from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PassengerLandingLine(models.Model):
    _name = 'passenger.landing.line'
    _description = 'Passenger Landing Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    passenger_landing_id = fields.Many2one('passenger.landing', string='Passenger Landing', tracking=True)
    flightno_id = fields.Many2one('flights',string='Flight No.')
    flight_registration_no = fields.Char(string='Registration No.', related='flightno_id.register_no', store=True)
    flight_aircraft = fields.Char(string='Aircraft Type', related='flightno_id.aircraft_type', store=True)
    start_time = fields.Datetime(string='Start Date & Time', tracking=True)
    end_time = fields.Datetime(string='End Date & Time', tracking=True)
    total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate', string='Rate',
                                       compute='_compute_passenger_landing_rate',
                                       inverse='_inverse_passenger_landing_rate',
                                       store=True, tracking=True)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)

    @api.depends('passenger_landing_id.passenger_landing_rate_id')
    def _compute_passenger_landing_rate(self):
        for line in self:
            line.passenger_landing_rate_id = line.passenger_landing_id.passenger_landing_rate_id

    def _inverse_passenger_landing_rate(self):
        for line in self:
            if line.passenger_landing_rate_id != line.passenger_landing_id.passenger_landing_rate_id:
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

    @api.depends('total_minutes', 'passenger_landing_rate_id')
    def _compute_amount(self):
        for record in self:
            amount = 0
            if record.passenger_landing_rate_id and record.total_minutes:
                rate_lines = record.passenger_landing_rate_id.passenger_landing_rate_line_ids.sorted(key=lambda r: r.from_unit)
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
                        raise ValidationError(f"No rates defined for PassengerLanding rate {record.passenger_landing_rate_id.name}")
            record.amount = amount

    @api.onchange('total_minutes', 'passenger_landing_rate_id')
    def _onchange_rate_details(self):
        self._compute_amount()
        if self.passenger_landing_rate_id and self.total_minutes:
            rate_lines = self.passenger_landing_rate_id.passenger_landing_rate_line_ids.sorted(key=lambda r: r.from_unit)
            max_rate_line = rate_lines[-1] if rate_lines else None
            if max_rate_line and self.total_minutes > max_rate_line.to_unit:
                return {
                    'warning': {
                        'title': "Maximum Rate Used",
                        'message': f"Using maximum rate {self.amount} for {self.total_minutes} minutes"
                    }
                }

    @api.constrains('flightno_id')
    def _passenger_landing_service(self):
        for record in self:
            if not record.flightno_id:
                raise ValidationError(_("Flight No. must be set for each PassengerLanding line."))

    @api.model
    def create(self, vals):
        passenger_lines = super(PassengerLandingLine, self).create(vals)
        for passenger_line in passenger_lines:
            passenger_line._log_tracking(vals)
            return passenger_lines

    def _log_tracking(self, vals):
        template_id = self.env.ref('passenger_landing_charges.airline_passenger_landing_line_template')
        changes = []

        if 'flightno_id' in vals:
            flight = self.env['flights'].browse(vals['flightno_id'])
            changes.append(f"Flight Number: → {flight.name}")
            changes.append(f"Flight Registration No: → {flight.register_no or 'N/A'}")

        if 'start_time' in vals:
            new_value = vals.get('start_time', 'N/A')
            changes.append(f"Start Time:  → {new_value}")

        if 'end_time' in vals:
            new_value = vals.get('end_time', 'N/A')
            changes.append(f"End Time:  → {new_value}")

        if 'start_time' in vals or 'end_time' in vals:
            self._compute_total_minutes()
            changes.append(f"Total Minutes: → {self.total_minutes}")

        if 'passenger_landing_rate_id' in vals:
            bridge_rate = self.env['passenger.landing.rate'].browse(vals['passenger_landing_rate_id'])
            new_value = bridge_rate.name  # or whatever field contains the rate name
            changes.append(f"Landing Rate: → {new_value}")

        if changes:
            rendered_message = self.env['ir.qweb']._render(
                template_id.id, {'changes': changes}
            )

            self.passenger_landing_id.message_post(
                body=rendered_message,
                message_type='notification',
                subtype_xmlid="mail.mt_note"
            )