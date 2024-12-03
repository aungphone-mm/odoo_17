from odoo import fields, models, _

class PassengerLandingRateLine(models.Model):
    _name = 'passenger.landing.rate.line'
    _description = 'Passenger Landing Rate Line'

    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate', string='Passenger Landing Rate')
    rate = fields.Float(string='Rate', required=True)
    rate_id = fields.Many2one('passenger.landing.rate', string='Passenger Landing Rate', required=True)
    flight_id = fields.Many2one('flights', string='Flight', required=True)
    registration_no = fields.Char(related='flight_id.register_no', string='Registration No', store=True, readonly=True)