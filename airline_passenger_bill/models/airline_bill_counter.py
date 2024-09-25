from odoo import fields, models, api, _


class AirlineBillCounter(models.Model):
    _name = 'airline.bill.counter'
    _description = 'Airline Bill Counter'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')