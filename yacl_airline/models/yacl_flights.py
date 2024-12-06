from odoo import fields, models, api


class FlightInfo(models.Model):
    _name = 'flights'
    _description = 'Flight No'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char("Registration No.", tracking=True)
    airline_id = fields.Many2one('airline',string='Airline', tracking=True)
    aircraft_type = fields.Char('Aircraft Type', tracking=True)
    # name = fields.Char("Registration No.")
    seat_capacity = fields.Integer(string='Seat Capacity', tracking=True)

    @api.depends('aircraft_type')
    def name_get(self):
        result = []
        for record in self:
            name = record.aircraft_type
            result.append((record.id, name))
        return result