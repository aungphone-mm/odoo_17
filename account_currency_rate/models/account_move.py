from odoo import models, fields, api


class AccountMove(models.Model):

    _inherit = 'account.move'

    currency_rate = fields.Float(string="Currency Rate", store=True)
    show_currency_rate = fields.Boolean(
        compute='_compute_show_currency_rate',
        store=False,
    )

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_show_currency_rate(self):
        for record in self:
            record.show_currency_rate = record.currency_id != record.company_id.currency_id