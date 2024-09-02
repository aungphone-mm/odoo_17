from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError, UserError

class AccountCashbook(models.Model):
    _name = 'account.cashbook'
    _description = 'Cashbook Payment/Receive for Accounting'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    date = fields.Date(string='Date', required=True, tracking=True)
    type = fields.Selection(string='Type', selection=[('payment', 'Payment'), ('receive', 'Receive'), ],
                            required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True, tracking=True)
    main_account_id = fields.Many2one(comodel_name='account.account', string='Main Account Name',
                                      domain='[("account_type", "=", "asset_cash")]', related='journal_id.default_account_id', required=True, tracking=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True, tracking=True)
    description = fields.Html(string='Description', required=False, tracking=True)
    line_ids = fields.One2many(comodel_name='account.cashbook.line', inverse_name='cashbook_id', string='Cashbook Line',
                               required=False, tracking=True)
    state = fields.Selection(string='State', selection=[('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel') ], required=True,
                             default='draft', tracking=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', readonly=True, copy=False)
    move_line_ids = fields.One2many(related='move_id.line_ids', string='Journal Items', readonly=True)

    def create(self, vals):
        if 'date' not in vals:
            raise ValidationError("Date is required.")
        cashbook_date = fields.Date.from_string(vals['date'])
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'account.cashbook')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Account Cashbook Sequence',
                'code': 'account.cashbook',
                'prefix': 'ACC-CBR/%(year)s/%(month)s/',
                'padding': 5,
                'number_next': 1,  # Explicitly set the starting number
                'number_increment': 1,
            })
        name = seq.with_context(ir_sequence_date=cashbook_date).next_by_id()
        vals['name'] = name
        return super(AccountCashbook, self).create(vals)

    def action_done(self):
        self.create_journal_entries()
        self.write({'state': 'done'})

    def action_cancel(self):
        self.cancel_journal_entries()
        self.write({'state': 'cancel'})

    def cancel_journal_entries(self):
        for record in self:
            if record.move_id:
                # Check if the move is posted
                if not record.move_id.state == 'posted':
                    record.move_id.button_cancel()  # Cancel the journal entry
                    record.move_id.unlink()  # Unlink the journal entry
                else:
                    raise UserError("Cannot Delete posted journal entries.")
            record.write({'move_id': False})

    def create_journal_entries(self):
        for record in self:
            if record.move_id:
                raise UserError('Journal entry already exists for this cashbook.')
            line_vals = []
            total_amount = sum(line.amount for line in record.line_ids)
            # Add lines for each cashbook line
            for line in record.line_ids:
                line_vals.append((0, 0, {
                    'account_id': line.account_id.id,
                    'name': line.name or record.name,
                    'debit': line.amount if record.type == 'payment' else 0.0,
                    'credit': line.amount if record.type == 'receive' else 0.0,
                }))
            # Add the main account line at the end
            line_vals.append((0, 0, {
                'account_id': record.main_account_id.id,
                'name': record.description or record.name,
                'debit': total_amount if record.type == 'receive' else 0.0,
                'credit': total_amount if record.type == 'payment' else 0.0,
            }))
            move_vals = {
                'date': record.date,
                'ref': record.name,
                'journal_id': record.journal_id.id,
                'line_ids': line_vals,
            }
            move = self.env['account.move'].create(move_vals)
            record.write({'move_id': move.id})

class AccountCashbookLine(models.Model):
    _name = 'account.cashbook.line'
    _description = 'Cashbook Payment/Receive Line for Accounting'

    name = fields.Char(string='Description', required=False, tracking=True)
    account_id = fields.Many2one(comodel_name='account.account', string='Account Name', required=True, tracking=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True, tracking=True, related='cashbook_id.currency_id')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, tracking=True)
    cashbook_id = fields.Many2one(comodel_name='account.cashbook', string='Cashbook', required=True, tracking=True)
