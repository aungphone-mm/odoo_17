from odoo import fields, models, api




class ResPartner(models.Model):
    _inherit = 'res.partner'

    business_source_id = fields.Many2one(
        comodel_name='business.source',
        string='Business Source',
        required=False)
    electric_meter_ids = fields.One2many(string='Electric Meter', comodel_name='electric.meter', inverse_name='partner_id')