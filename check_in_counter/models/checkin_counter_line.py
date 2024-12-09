from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class CheckinCounterLine(models.Model):
    _name = 'checkin.counter.line'
    _description = 'check in counter Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    checkin_counter_id = fields.Many2one('checkin.counter', string='Check in Counter', tracking=True)
    flightno_id = fields.Char(string='Flight No.')
    flight_registration_no = fields.Char(string='Registration No.', store=True)
    flight_aircraft = fields.Char(string='Aircraft Type',store=True)
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Date & Time', tracking=True, default=fields.Datetime.now)
    total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
    checkin_counter_rate_id = fields.Many2one('checkin.counter.rate', string='Rate',
                                       compute='_compute_checkin_counter_rate',
                                       inverse='_inverse_checkin_counter_rate',
                                       store=True, tracking=True)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)

    @api.depends('checkin_counter_id.checkin_counter_rate_id')
    def _compute_checkin_counter_rate(self):
        for line in self:
            line.checkin_counter_rate_id = line.checkin_counter_id.checkin_counter_rate_id

    def _inverse_checkin_counter_rate(self):
        for line in self:
            if line.checkin_counter_rate_id != line.checkin_counter_id.checkin_counter_rate_id:
                # You can add any necessary logic here when the rate changes
                pass
    #aungphone
    @api.depends('start_time', 'end_time')
    def _compute_total_minutes(self):
        for record in self:
            if record.start_time and record.end_time:
                duration = record.end_time - record.start_time
                record.total_minutes = int(duration.total_seconds() / 60)
            else:
                record.total_minutes = 0

    @api.depends('total_minutes', 'checkin_counter_rate_id')
    def _compute_amount(self):
        for record in self:
            amount = 0
            if record.checkin_counter_rate_id and record.total_minutes:
                rate_lines = record.checkin_counter_rate_id.checkin_counter_rate_line_ids.sorted(key=lambda r: r.from_unit)
                max_rate_line = rate_lines[-1] if rate_lines else None
                for rate_line in rate_lines:
                    if not rate_line.to_unit or record.total_minutes <= rate_line.to_unit:
                        amount = rate_line.unit_price
                        break
                else:
                    # If no suitable range is found, use the maximum unit price
                    if max_rate_line:
                        amount = max_rate_line.unit_price
                    else:
                        raise ValidationError(f"No rates defined for checkin rate {record.checkin_counter_rate_id.name}")
            record.amount = amount

    @api.onchange('total_minutes', 'checkin_counter_rate_id')
    def _onchange_rate_details(self):
        self._compute_amount()
        if self.checkin_counter_rate_id and self.total_minutes:
            rate_lines = self.checkin_counter_rate_id.checkin_counter_rate_line_ids.sorted(key=lambda r: r.from_unit)
            max_rate_line = rate_lines[-1] if rate_lines else None
            if max_rate_line and self.total_minutes > max_rate_line.to_unit:
                return {
                    'warning': {
                        'title': "Maximum Rate Used",
                        'message': f"Using maximum rate {self.amount} for {self.total_minutes} minutes"
                    }
                }

    @api.constrains('flightno_id')
    def _check_airline(self):
        for record in self:
            if not record.flightno_id:
                raise ValidationError(_("Flight No. must be set for each checkin line."))

    @api.model
    def create(self, vals):
        passenger_lines = super(CheckinCounterLine, self).create(vals)
        for passenger_line in passenger_lines:
            passenger_line._log_tracking(vals)
            return passenger_lines

    def _log_tracking(self, vals):
        template_id = self.env.ref('check_in_counter.airline_passenger_checkin_line_template')
        changes = []

        if 'flightno_id' in vals:
            # flight = self.env['flights'].browse(vals['flightno_id'])
            new_value = vals.get('flightno_id', 'N/A')
            new_value1 = vals.get('flight_registration_no', 'N/A')
            changes.append(f"Flight Number: → {new_value}")
            changes.append(f"Flight Registration No: → {new_value1 or 'N/A'}")

        if 'start_time' in vals:
            new_value = vals.get('start_time', 'N/A')
            changes.append(f"Start Time:  → {new_value}")

        if 'end_time' in vals:
            new_value = vals.get('end_time', 'N/A')
            changes.append(f"End Time:  → {new_value}")

        if 'start_time' in vals or 'end_time' in vals:
            self._compute_total_minutes()
            changes.append(f"Total Minutes: → {self.total_minutes}")

        if 'checkin_counter_rate_id' in vals:
            bridge_rate = self.env['checkin.counter.rate'].browse(vals['checkin_counter_rate_id'])
            new_value = bridge_rate.name  # or whatever field contains the rate name
            changes.append(f"Bridge Rate: → {new_value}")

        if changes:
            rendered_message = self.env['ir.qweb']._render(
                template_id.id, {'changes': changes}
            )

            self.checkin_counter_id.message_post(
                body=rendered_message,
                message_type='notification',
                subtype_xmlid="mail.mt_note"
            )