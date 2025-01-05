from odoo import models, fields, api

class AccountMove(models.Model):

    _inherit = 'account.move'

    @api.model
    def write(self, vals):
        print('hello world')
        res = super(AccountMove, self).write(vals)
        return res

