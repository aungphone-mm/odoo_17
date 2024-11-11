from odoo import fields, models, api

class Airline(models.Model):
    _name = 'airline'
    _description = 'Airline Information'

    name = fields.Char('Airline', required=True)
    description = fields.Text('Code', required=True)
    partner_id = fields.Many2one('res.partner', string='Company')
    flight_ids = fields.One2many('flights', 'airline_id', string='Flights')