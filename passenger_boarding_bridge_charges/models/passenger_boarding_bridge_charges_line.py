from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PassengerBoardingBridgeChargesLine(models.Model):
    _name = 'passenger.boarding.bridge.charges.line'
    _description = 'Passenger Boarding Bridge Charges Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    passenger_boarding_bridge_charges_id = fields.Many2one('passenger.boarding.bridge.charges', string='Passenger Boarding Bridge Charges', tracking=True, )
    flightno_id = fields.Char(string='Flight No.')
    flight_registration_no = fields.Char(string='Registration No.')
    flight_aircraft = fields.Char(string='Aircraft Type')
    start_time = fields.Datetime(string='Start Date & Time', default=fields.Datetime.now, tracking=True, )
    end_time = fields.Datetime(string='End Date & Time', tracking=True)
    total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
    bridge_rate_id = fields.Many2one('passenger.boarding.bridge.charges.rate', string='Rate',
                                       compute='_compute_bridge_rate',
                                       inverse='_inverse_bridge_rate',
                                       store=True, tracking=True)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)
    seat_capacity = fields.Integer(string='Seat Capacity',related='bridge_rate_id.seat_capacity')

    @api.constrains('flightno_id')
    def _check_airline(self):
        for record in self:
            if not record.flightno_id:
                raise ValidationError(_("Flight No. must be set for each bridge service line."))
    @api.onchange('flight_aircraft')
    def _onchange_flight(self):
        if self.flightno_id:
            if not self.seat_capacity or self.seat_capacity <= 0:
                return {
                    'warning': {
                        'title': 'Error',
                        'message': _(
                            "Please define seat capacity for flight %s before proceeding.") % self.flightno_id
                    }
                }

            rate = self.env['passenger.boarding.bridge.charges.rate'].search([
                ('seat_capacity', '=', self.seat_capacity),
                ('active', '=', True)
            ], limit=1)

            if not rate:
                return {
                    'warning': {
                        'title': 'Missing Bridge Rate',
                        'message': f"{self.flightno_id} is {self.seat_capacity} seats. No bridge rate found for aircraft with {self.seat_capacity} seats"
                    }
                }
    @api.depends('flightno_id')
    def _compute_bridge_rate(self):
        for line in self:
            if line.flightno_id and line.seat_capacity:
                rate = self.env['passenger.boarding.bridge.charges.rate'].search([
                    ('seat_capacity', '=', line.seat_capacity),
                    ('active', '=', True)
                ], limit=1)
                if not rate:
                    line.bridge_rate_id = False
                    # Instead of raising ValidationError, we'll handle this in onchange
                else:
                    line.bridge_rate_id = rate.id
            else:
                line.bridge_rate_id = False

    @api.depends('passenger_boarding_bridge_charges_id.bridge_rate_id')
    def _compute_bridge_rate(self):
        for line in self:
            line.bridge_rate_id = line.passenger_boarding_bridge_charges_id.bridge_rate_id

    def _inverse_bridge_rate(self):
        for line in self:
            if line.bridge_rate_id != line.passenger_boarding_bridge_charges_id.bridge_rate_id:
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

    @api.depends('total_minutes', 'bridge_rate_id')
    def _compute_amount(self):
        for record in self:
            amount = 0
            if record.bridge_rate_id and record.total_minutes:
                rate_lines = record.bridge_rate_id.bridge_rate_line_ids.sorted(key=lambda r: r.from_unit)
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
                        raise ValidationError(f"{record.bridge_rate_id.name} rate has no rate lines. Please add rate lines in Bridge Rate!")
            record.amount = amount

    @api.onchange('total_minutes', 'bridge_rate_id')
    def _onchange_rate_details(self):
        self._compute_amount()
        if self.bridge_rate_id and self.total_minutes:
            rate_lines = self.bridge_rate_id.bridge_rate_line_ids.sorted(key=lambda r: r.from_unit)
            max_rate_line = rate_lines[-1] if rate_lines else None
            if max_rate_line and self.total_minutes > max_rate_line.to_unit:
                return {
                    'warning': {
                        'title': "Maximum Rate Used",
                        'message': f"Using maximum rate {self.amount} for {self.total_minutes} minutes"
                    }
                }

    @api.model
    def create(self, vals):
        passenger_lines = super(PassengerBoardingBridgeChargesLine, self).create(vals)
        for passenger_line in passenger_lines:
            passenger_line._log_bridge_tracking(vals)
            return passenger_lines

    def _log_bridge_tracking(self, vals):
        template_id = self.env.ref('passenger_boarding_bridge_charges.airline_passenger_bridge_line_template')
        changes = []

        # if 'flightno_id' in vals:
        #     flight = self.env['flights'].browse(vals['flightno_id'])
        #     changes.append(f"Flight Number: → {flight.name}")
        #     changes.append(f"Flight Registration No: → {flight.name or 'N/A'}")

        if 'start_time' in vals:
            new_value = vals.get('start_time', 'N/A')
            changes.append(f"Start Time:  → {new_value}")

        if 'end_time' in vals:
            new_value = vals.get('end_time', 'N/A')
            changes.append(f"End Time:  → {new_value}")

        if 'start_time' in vals or 'end_time' in vals:
            self._compute_total_minutes()
            changes.append(f"Total Minutes: → {self.total_minutes}")

        if 'bridge_rate_id' in vals:
            bridge_rate = self.env['passenger.boarding.bridge.charges.rate'].browse(vals['bridge_rate_id'])
            new_value = bridge_rate.name  # or whatever field contains the rate name
            changes.append(f"Bridge Rate: → {new_value}")

        if changes:
            rendered_message = self.env['ir.qweb']._render(
                template_id.id, {'changes': changes}
            )

            self.passenger_boarding_bridge_charges_id.message_post(
                body=rendered_message,
                message_type='notification',
                subtype_xmlid="mail.mt_note"
            )