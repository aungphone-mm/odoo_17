from odoo import api, fields, models


class AccountAsset(models.Model):

    _inherit = 'account.asset'

    asset_category = fields.Many2one('account.asset.category', string='Asset Category')

class AccountAssetCategory(models.Model):

    _name = 'account.asset.category'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
