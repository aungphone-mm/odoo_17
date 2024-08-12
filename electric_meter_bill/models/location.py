from odoo import fields, models, api


class Location(models.Model):
    _name = 'location'
    _description = 'Location'

    name = fields.Char()
    code = fields.Char(string="Code")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
