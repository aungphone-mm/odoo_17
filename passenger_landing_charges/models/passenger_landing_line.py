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
    # start_time = fields.Datetime(string='Start Date & Time', tracking=True)
    # end_time = fields.Datetime(string='End Date & Time', tracking=True)
    # total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
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

    @api.depends('flightno_id', 'passenger_landing_rate_id')
    def _compute_amount(self):
        for record in self:
            amount = 0
            if record.passenger_landing_rate_id and record.flight_registration_no and record.flightno_id:
                rate_line = record.passenger_landing_rate_id.passenger_landing_rate_line_ids.filtered(
                    lambda r: (r.registration_no == record.flight_registration_no and
                               r.flight_no == record.flightno_id.name)
                )
                if rate_line:
                    amount = rate_line[0].rate
                else:
                    # If no matching rate is found, set amount to 0
                    record.amount = 0
            record.amount = amount

