from odoo import fields, models, api, _

class PassengerLandingRateLine(models.Model):
    _name = 'passenger.landing.rate.line'
    _description = 'Passenger Landing Rate Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Registration No', required=True)
    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate', string='Passenger Landing Rate')
    rate_id = fields.Many2one('passenger.landing.rate', string='Passenger Landing Rate', required=True)
    aircraft_type = fields.Char(string='Aircraft Type', required=True)
    unit_price = fields.Float(string='Unit Price', required=True)

    # @api.model
    # def create(self, vals):
    #     # Create or update flight record when creating rate line
    #     flight = self.env['flights'].search([
    #         ('aircraft_type', '=', vals.get('aircraft_type')),
    #         ('name', '=', vals.get('registration_no'))
    #     ], limit=1)
    #
    #     if not flight:
    #         flight = self.env['flights'].create({
    #             'aircraft_type': vals.get('aircraft_type'),
    #             'name': vals.get('registration_no')
    #         })
    #
    #     return super(PassengerLandingRateLine, self).create(vals)
    #
    # @api.onchange('aircraft_type', 'registration_no')
    # def _onchange_flight_details(self):
    #     # Auto-suggest existing values
    #     if self.registration_no:
    #         existing_flights = self.env['flights'].search([
    #             ('name', '=', self.registration_no)
    #         ], limit=1)
    #         if existing_flights:
    #             self.registration_no = existing_flights.name
    #             self.aircraft_type = existing_flights.aircraft_type
    #
