from odoo import models, fields, api

class AccountMove(models.Model):

    _inherit = 'account.move'

    custom_header = fields.Html(string='Custom Header')
    custom_note = fields.Html(string='Custom Note')

    def action_print_custom_invoice(self):
        """Print the custom invoice report"""
        self.ensure_one()
        return self.env.ref('account_extension.action_report_custom_invoice').report_action(self)

    @api.model
    def write(self, vals):
        print('hello world')
        res = super(AccountMove, self).write(vals)
        return res