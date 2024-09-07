from odoo import fields, models, api


class Airline(models.Model):
    _name = 'airline'
    _description = 'Airline Information'

    name = fields.Char('Code', required=True)
    description = fields.Text('Description', required=True)
    partner_id = fields.Many2one('res.partner', string='Company')
