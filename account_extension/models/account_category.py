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


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     chart_of_account_id = fields.Many2one('account.account', string='Chart of Account',
#                                           domain=[('deprecated', '=', False)])
#
#     @api.onchange('chart_of_account_id')
#     def _onchange_chart_of_account_id(self):
#         if self.chart_of_account_id:
#             # Clear existing lines
#             self.line_ids = [(5, 0, 0)]
#             # Create a new line with the selected chart of account
#             self.line_ids = [(0, 0, {
#                 'account_id': self.chart_of_account_id.id,
#                 'name': self.chart_of_account_id.name,
#                 'debit': 0.0,
#                 'credit': 0.0,
#             })]
#
#     @api.onchange('line_ids', 'line_ids.debit', 'line_ids.credit')
#     def _onchange_line_ids(self):
#         if not self.chart_of_account_id or not self.line_ids:
#             return
#
#         # Exclude the first line (chart of account line) from calculations
#         other_lines = self.line_ids[1:]
#         total_debit = sum(line.debit for line in other_lines)
#         total_credit = sum(line.credit for line in other_lines)
#
#         # Update the first line (chart of account line)
#         first_line = self.line_ids[0]
#         if first_line.account_id == self.chart_of_account_id:
#             if total_debit > total_credit:
#                 first_line.credit = total_debit - total_credit
#                 first_line.debit = 0.0
#             elif total_credit > total_debit:
#                 first_line.debit = total_credit - total_debit
#                 first_line.credit = 0.0
#             else:
#                 first_line.debit = 0.0
#                 first_line.credit = 0.0
#
#     @api.model
#     def create(self, vals):
#         # Ensure the chart of account line is always the first line
#         if vals.get('line_ids'):
#             line_ids = vals['line_ids']
#             coa_id = vals.get('chart_of_account_id')
#             coa_line = next((line for line in line_ids if line[2].get('account_id') == coa_id), None)
#             if coa_line:
#                 line_ids.remove(coa_line)
#                 line_ids.insert(0, coa_line)
#                 vals['line_ids'] = line_ids
#         return super(AccountMove, self).create(vals)
#
#     def write(self, vals):
#         # Ensure the chart of account line is always the first line
#         if vals.get('line_ids'):
#             line_ids = self.resolve_2many_commands('line_ids', vals['line_ids'], ['account_id'])
#             coa_line = next((line for line in line_ids if line.get('account_id') == self.chart_of_account_id.id), None)
#             if coa_line:
#                 line_ids.remove(coa_line)
#                 line_ids.insert(0, coa_line)
#                 vals['line_ids'] = [(1, line.get('id'), line) if line.get('id') else (0, 0, line) for line in line_ids]
#         return super(AccountMove, self).write(vals)
