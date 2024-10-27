from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PassengerBoardingBridgeChargesLine(models.Model):
    _name = 'passenger.boarding.bridge.charges.line'
    _description = 'Passenger Boarding Bridge Charges Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    passenger_boarding_bridge_charges_id = fields.Many2one('passenger.boarding.bridge.charges', string='Passenger Boarding Bridge Charges', tracking=True, track_visibility='always')
    flightno_id = fields.Many2one('flights',string='Flight No.')
    flight_registration_no = fields.Char(string='Registration No.', related='flightno_id.register_no', store=True)
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, track_visibility='always')
    end_time = fields.Datetime(string='End Date & Time', tracking=True, track_visibility='always')
    total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
    bridge_rate_id = fields.Many2one('passenger.boarding.bridge.charges.rate', string='Rate',
                                       compute='_compute_bridge_rate',
                                       inverse='_inverse_bridge_rate',
                                       store=True, tracking=True)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)

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
                        raise ValidationError(f"No rates defined for bridge rate {record.bridge_rate_id.name}")
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

    @api.constrains('flightno_id')
    def _check_airline(self):
        for record in self:
            if not record.flightno_id:
                raise ValidationError(_("Flight No. must be set for each bridge service line."))


