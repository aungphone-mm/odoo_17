from odoo import fields, models, api


class BusinessSource(models.Model):
    _name = 'business.source'
    _description = 'Business Source'

    name = fields.Char(string="Code")
    description = fields.Char(string="Description")
    partner_ids = fields.One2many(
        comodel_name='res.partner',
        inverse_name='business_source_id',
        string='Customer',
        required=False)
    rate_id = fields.Many2one(
        comodel_name='electric.rate',
        string='Rate',
        required=False)

