from odoo import fields,api, models

class FlightInfo(models.Model):
    _name = 'flights'
    _description = 'Flight No'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char("Flight No", tracking=True)
    airline_id = fields.Many2one('airline',string='Airline', tracking=True)
    aircraft_type = fields.Char('Aircraft Type')
    register_no = fields.Char("Registration No.")
    seat_capacity = fields.Integer(string='Seat Capacity', required=True, tracking=True)