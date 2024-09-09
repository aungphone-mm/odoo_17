from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    business_source_id = fields.Many2one(
        comodel_name='business.source',
        string='Business Source',
        required=False)
    electric_meter_rate = fields.Many2one(related='business_source_id.rate_id', string='Electric Meter Rate')
    electric_meter_ids = fields.One2many(string='Electric Meter', comodel_name='electric.meter', inverse_name='partner_id')
    contact_name = fields.Char('Contact Person')
    contact_job_position = fields.Char('Job Position')