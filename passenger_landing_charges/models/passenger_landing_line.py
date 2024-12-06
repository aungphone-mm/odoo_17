from odoo import fields, models, api, _

class PassengerLandingLine(models.Model):
    _name = 'passenger.landing.line'
    _description = 'Passenger Landing Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    passenger_landing_id = fields.Many2one('passenger.landing', string='Aircraft Landing',
                                         tracking=True, index=True)
    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate',string='Aircraft Rate')
    flight_no = fields.Char(string='Flight No', required=True)
    flight_registration_no = fields.Many2one('passenger.landing.rate.line',
                                           string='Registration No.',
                                           domain="[('rate_id', '=', parent.passenger_landing_rate_id)]")
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, default=fields.Datetime.now)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)
    flight_aircraft = fields.Many2one('passenger.landing.rate.line',
                                      string='Aircraft Type',
                                      domain="[('id', '=', flight_registration_no.id)]")
    aircraft_type_display = fields.Char(related='flight_aircraft.aircraft_type', string='Aircraft Type')

    @api.onchange('flight_registration_no')
    def _onchange_flight_registration_no(self):
        for record in self:
            record.flight_aircraft = record.flight_registration_no

    @api.depends('flight_aircraft', 'start_time')
    def _compute_amount(self):
        for record in self:
            if record.flight_aircraft:
                record.amount = record.flight_aircraft.unit_price
            else:
                record.amount = 0.0