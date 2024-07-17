from odoo import api, models, fields


class AccountCategory(models.Model):
    _name = 'account.category'
    _description = 'Chart of accounts category'
    _rec_name = 'name'
    name = fields.Char(required=True, string='Category Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class AccountAccount(models.Model):
    _inherit = 'account.account'
    category_id = fields.Many2one('account.category', string='Category')
    old_account_id = fields.Many2one('old.account', string='Old Account')

class AccountGroup(models.Model):
    _inherit = 'account.group'
    code = fields.Char(required=True, string='Code')
    category = fields.Many2one('account.group.category', string='Category')

class AccountGroupCategory(models.Model):
    _name = 'account.group.category'
    name = fields.Char(required=True, string='name')

class OldAccount(models.Model):
    _name = 'old.account'
    _rec_name = 'name'
    name = fields.Char(required=True, string='Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


