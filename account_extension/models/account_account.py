from odoo import api, models, fields
import num2words
class AccountAccount(models.Model):
    _inherit = 'account.account'
    main_code = fields.Char(string='Main Code', required=True)
    sub_code = fields.Char(string='Sub Code', required=True)
    group_code = fields.Char(string='Group Code', required=True)
    old_code = fields.Char(string='Old Code', required=True)








