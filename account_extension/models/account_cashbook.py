from wheel.metadata import _
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError

class AccountCashbook(models.Model):
    _name = 'account.cashbook'
    _description = 'Cashbook Payment/Receive for Accounting'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    date = fields.Date(string='Date', required=True)
    type = fields.Selection(string='Type', selection=[('payment', 'Payment'), ('receive', 'Receive'), ],
                            required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True)
    main_account_id = fields.Many2one(comodel_name='account.account', string='Main Account Name',
                                      domain='[("account_type", "=", "asset_cash")]', related='journal_id.default_account_id', readonly=False)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True)
    description = fields.Html(string='Description', required=False)
    line_ids = fields.One2many(comodel_name='account.cashbook.line', inverse_name='cashbook_id', string='Cashbook Line',
                               required=False)
    state = fields.Selection(
        string='State',
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('done', 'Done'),
            ('cancel', 'Cancel')
        ],
        required=True,
        default='draft')
    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', readonly=True, copy=False)
    move_line_ids = fields.One2many(related='move_id.line_ids', string='Journal Items', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_rate = fields.Float(string='Currency Rate', default=1.0, digits=(12, 6))
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    show_currency_rate = fields.Boolean(
        compute='_compute_show_currency_rate',
        store=False,
    )

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_show_currency_rate(self):
        for record in self:
            record.show_currency_rate = record.currency_id != record.company_id.currency_id

    @api.onchange('currency_rate')
    def _onchange_currency_rate(self):
        if self.currency_id != self.company_id.currency_id:
            # Update the rate in the context
            self = self.with_context(currency_rate=self.currency_rate)

    @api.onchange('currency_id')
    def _onchange_currency(self):
        if self.currency_id:
            if self.currency_id != self.company_id.currency_id:
                rate = self.env['res.currency']._get_conversion_rate(
                    self.company_id.currency_id,
                    self.currency_id,
                    self.company_id,
                    self.date or fields.Date.today()
                )
                # Store the direct rate (MMK per USD) instead of the inverse
                self.currency_rate = 1 / rate if rate else 0.0
            else:
                self.currency_rate = 1.0

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

    def action_confirm(self):
        self.create_journal_entries()
        self.write({'state': 'confirm'})

    def action_done(self):
        self.env['account.move'].browse(self.move_id.id).action_post()
        self.write({'state': 'done'})

    def action_cancel(self):
        self.cancel_journal_entries()
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.update({'state': 'draft'})

    def action_print_invoice(self):
        # Cashbook Invoice Print ထုတ်ရန်အတွက် (ဖိုးလပြည့်)
        return self.env.ref('account_extension.action_report_cashbook_invoice').report_action(self)

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

            # Convert amounts to company currency if needed
            def convert_amount(amount):
                if record.currency_id != record.company_id.currency_id:
                    return amount * record.currency_rate
                return amount

            total_amount = sum(convert_amount(line.amount) for line in record.line_ids)

            # Add lines for each cashbook line
            for line in record.line_ids:
                converted_amount = convert_amount(line.amount)
                is_payment = record.type == 'payment'

                # Set the correct signs for amount_currency based on debit/credit
                amount_currency = 0.0
                if record.currency_id != record.company_id.currency_id:
                    amount_currency = line.amount if is_payment else -line.amount

                line_vals.append((0, 0, {
                    'account_id': line.account_id.id,
                    'name': line.name or record.name,
                    'partner_id': line.partner_id.id or record.partner_id.id,
                    'debit': converted_amount if is_payment else 0.0,
                    'credit': converted_amount if not is_payment else 0.0,
                    'analytic_distribution': line.analytic_distribution,
                    'amount_currency': amount_currency,
                    'currency_id': record.currency_id.id if record.currency_id != record.company_id.currency_id else False,
                }))

            # Add the main account line at the end
            is_payment = record.type == 'payment'
            amount_currency = 0.0
            if record.currency_id != record.company_id.currency_id:
                amount_currency = sum(line.amount for line in record.line_ids)
                amount_currency = -amount_currency if is_payment else amount_currency

            line_vals.append((0, 0, {
                'account_id': record.main_account_id.id,
                'name': record.description or record.name,
                'partner_id': record.partner_id.id,
                'debit': total_amount if not is_payment else 0.0,
                'credit': total_amount if is_payment else 0.0,
                'amount_currency': amount_currency,
                'currency_id': record.currency_id.id if record.currency_id != record.company_id.currency_id else False,
            }))

            move_vals = {
                'date': record.date,
                'ref': record.name,
                'journal_id': record.journal_id.id,
                'partner_id': record.partner_id.id,
                'line_ids': line_vals,
            }
            move = self.env['account.move'].create(move_vals)
            record.write({'move_id': move.id})

class AccountCashbookLine(models.Model):
    _name = 'account.cashbook.line'
    _description = 'Cashbook Payment/Receive Line for Accounting'

    name = fields.Char(string='Label')
    account_id = fields.Many2one(comodel_name='account.account', string='Account Name', required=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True, related='cashbook_id.currency_id')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True)
    cashbook_id = fields.Many2one(comodel_name='account.cashbook', string='Cashbook', required=True)
    analytic_precision = fields.Integer(
        string='Analytic',
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    analytic_distribution = fields.Json(string='Analytic Distribution')
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        for line in self:
            if line.analytic_distribution:
                # Split compound keys that may contain multiple IDs
                account_ids = []
                for key in line.analytic_distribution.keys():
                    # Handle both single IDs and compound IDs
                    if ',' in key:
                        ids = [int(x) for x in key.split(',')]
                        account_ids.extend(ids)
                    else:
                        account_ids.append(int(key))

                accounts = self.env['account.analytic.account'].browse(account_ids)
                for account in accounts:
                    if not account.exists():
                        raise ValidationError(_('Some analytic accounts in distribution are not found!'))

    def _prepare_analytic_lines(self):
        """Prepare analytic lines from cashbook line"""
        result = []
        for move_line in self:
            if move_line.analytic_distribution:
                for account_id, percentage in move_line.analytic_distribution.items():
                    amount = move_line.amount * (percentage / 100)
                    result.append({
                        'name': move_line.name or '',
                        'amount': amount,
                        'account_id': int(account_id),
                        'ref': move_line.cashbook_id.name,
                        'cashbook_line_id': move_line.id,
                        'date': move_line.cashbook_id.date,
                        'partner_id': move_line.partner_id.id,
                        'unit_amount': 1.0,
                        'product_id': False,
                        'currency_id': move_line.currency_id.id,
                    })
        return result

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_('Amount must be positive.'))