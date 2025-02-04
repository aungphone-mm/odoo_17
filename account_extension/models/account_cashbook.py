import math
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError, UserError
from io import BytesIO
import xlsxwriter
import base64


class AccountCashbook(models.Model):
    _name = 'account.cashbook'
    _description = 'Cashbook Payment/Receive for Accounting'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    type = fields.Selection(string='Type', selection=[('payment', 'Payment'), ('receive', 'Receive'), ],
                            required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', tracking=True)
    main_account_id = fields.Many2one(comodel_name='account.account', string='Main Account Name',
                                      domain='[("account_type", "=", "asset_cash")]', related='journal_id.default_account_id', readonly=False)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id.id, tracking=True)
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
    # total_credit = fields.Float(string='Total Credit', compute='_compute_total_credit', store=True)
    # total_debit = fields.Float(string='Total Debit', compute='_compute_total_debit', store=True)
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

    @api.depends('currency_id')
    def _compute_currency_id(self):
        for record in self:
            if record.company_id:
                record.currency_id = record.company__id.currency_id

    def action_excel_download(self):
        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Cashbook Lines')

        # Add formats
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
            'border': 0,
            'bg_color': '#e6fcf2'
        })

        header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#C0C0C0',
            'bg_color': '#e6fcf2'
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'border_color': '#C0C0C0'
        })

        amount_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'border_color': '#C0C0C0',
            'num_format': '#,##0.00" K"'  # Format to show numbers with 2 decimals and K suffix
        })

        analytic_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'border_color': '#C0C0C0',
            # 'bg_color': '#FFB6C1'  # Light pink background for analytic codes
        })
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Set column widths
        sheet.set_column('A:A', 10)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 10)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)
        sheet.set_column('N:N', 20)
        sheet.set_column('O:O', 20)
        sheet.set_column('P:P', 20)

        # Write title at the top center
        if self.type == 'receive':
            title = 'Cashbook Receive'
        elif self.type == 'payment':
            title = 'Cashbook Payment'
        else:
            title = 'Cashbook'

        sheet.merge_range('A1:P1', title, title_format)
        headers = [
            'Date',
            'Source Code',
            'Reference',
            'Cheque',
            'DN/CN No.',
            'Description',
            'Account Name',
            'Partner',
            'Particular',
            'Label',
            'Analytic Distribution',
            'Currency',
            'Amount',
            'Main Account',
            'Sub Account',
            'Note'
        ]

        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        # Write data starting from row 2 (row index 2 in code corresponds to Excel row 3)
        for row, line in enumerate(self.line_ids, 2):
            sheet.write(row, 0, line.cashbook_id.date.strftime('%Y-%m-%d') if line.cashbook_id.date else '', date_format)
            # Account Name
            account_name = f"{line.account_id.code} {line.account_id.name}"
            sheet.write(row, 6, account_name, cell_format)

            # Partner
            sheet.write(row, 7, line.partner_id.name if line.partner_id else '', cell_format)

            # Label
            sheet.write(row, 9, line.name or '', cell_format)

            # Analytic Distribution
            sheet.write(row, 10, line.analytic_code or '', analytic_format)

            # Currency
            sheet.write(row, 11, line.currency_id.name, cell_format)

            # Amount - write the amount directly (it's already in K)
            sheet.write(row, 12, line.amount, amount_format)

            analytic_value = ''
            if line.analytic_distribution:
                # Get account info for each entry in the distribution
                analytic_accounts = []
                for account_id, percentage in line.analytic_distribution.items():
                    if ',' in account_id:  # Handle compound keys
                        account_ids = [int(x) for x in account_id.split(',')]
                        accounts = self.env['account.analytic.account'].browse(account_ids)
                        analytic_accounts.extend(accounts)
                    else:
                        account = self.env['account.analytic.account'].browse(int(account_id))
                        analytic_accounts.append(account)

                # Create the display string using code field
                analytic_value = ' / '.join(account.code for account in analytic_accounts if account.exists())

            # Write to Excel
            sheet.write(row, 10, analytic_value, analytic_format)

        # Add total row
        total_row = len(self.line_ids) + 2
        total_formula = f'=SUM(M3:M{total_row})'
        sheet.write(total_row, 12, total_formula, amount_format)

        workbook.close()
        output.seek(0)

        # Generate attachment
        xlsx_data = output.getvalue()
        file_name = f'Cashbook_{self.name}_Lines.xlsx'

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'store_fname': file_name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

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

        # If type not in vals, get it from context
        cashbook_type = vals.get('type') or self._context.get('default_type')

        # Choose sequence based on type
        sequence_code = f'account.cashbook.{cashbook_type}'

        seq = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)
        if not seq:
            # Create sequence if it doesn't exist
            prefix = 'REC/' if cashbook_type == 'receive' else 'PAY/'
            seq = self.env['ir.sequence'].sudo().create({
                'name': f'Account Cashbook {cashbook_type.title()} Sequence',
                'code': sequence_code,
                'prefix': f'{prefix}%(year)s/%(month)s/',
                'padding': 5,
                'number_next': 1,
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
        # Compute analytic values for lines
        for record in self:
            for line in record.line_ids:
                analytic_accounts = []
                if line.analytic_distribution:
                    for account_id, percentage in line.analytic_distribution.items():
                        if ',' in account_id:  # Handle compound keys
                            account_ids = [int(x) for x in account_id.split(',')]
                            accounts = self.env['account.analytic.account'].browse(account_ids)
                            analytic_accounts.extend(accounts)
                        else:
                            account = self.env['account.analytic.account'].browse(int(account_id))
                            analytic_accounts.append(account)
                # Join analytic codes with '/'
                line.analytic_code = ' / '.join(account.code for account in analytic_accounts if account.exists())
        return self.env.ref('account_extension.action_report_cashbook_invoice').report_action(self)

    def action_print_payable_invoice(self):
        # Cashbook Invoice Print
        return self.env.ref('account_extension.action_report_payable_invoice').report_action(self)

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

            # Add lines for each cashbook line
            for line in record.line_ids:
                # Determine the amount based on currency comparison
                if record.currency_id == record.company_id.currency_id:
                    amount = line.amount
                else:
                    amount = line.amount * record.currency_rate

                # Set debit to cashbook line amount if type is 'payment', otherwise set to zero
                debit = amount if record.type == 'payment' else 0.0
                credit = amount if record.type == 'receive' else 0.0

                line_vals.append((0, 0, {
                    'account_id': line.account_id.id,
                    'name': line.name or record.name,
                    'partner_id': line.partner_id.id or record.partner_id.id,
                    'debit': debit,
                    'credit': credit,
                    'analytic_distribution': line.analytic_distribution,
                    'currency_id': record.currency_id.id,
                }))

            # Add the main account line at the end
            total_amount = sum(line.amount for line in record.line_ids)
            if record.currency_id != record.company_id.currency_id:
                total_amount *= record.currency_rate

            main_debit = total_amount if record.type == 'receive' else 0.0
            main_credit = total_amount if record.type == 'payment' else 0.0

            line_vals.append((0, 0, {
                'account_id': record.main_account_id.id,
                'name': record.description or record.name,
                'partner_id': record.partner_id.id,
                'debit': main_debit,
                'credit': main_credit,
                'currency_id': record.currency_id.id,
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
    analytic_code = fields.Char(string='Analytic Code', store=True)
    analytic_distribution = fields.Json(string='Analytic Distribution')
    partner_id = fields.Many2one('res.partner', string='Partner',
                                              compute='_compute_partner',
                                              inverse='_inverse_partner',
                                              store=True)

    @api.depends('cashbook_id.partner_id')
    def _compute_partner(self):
        for line in self:
            line.partner_id = line.cashbook_id.partner_id

    def _inverse_partner(self):
        for line in self:
            if line.partner_id != line.cashbook_id.partner_id:
                pass

    @api.onchange('analytic_distribution')
    def compute_analytic_distribution_account_code(self):
        for line in self:
            if line.analytic_distribution:
                account_ids = []
                for key in line.analytic_distribution.keys():
                    if ',' in key:
                        ids = [int(x) for x in key.split(',')]
                        account_ids.extend(ids)
                    else:
                        account_ids.append(int(key))
                accounts = self.env['account.analytic.account'].browse(account_ids)
                line.analytic_code = ', '.join(accounts.mapped('code'))
                print(line.analytic_code)

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

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    per_depreciation_amount = fields.Float(string='Per Depreciation Amount')
    # per_depreciation_date = fields.Date(string='Per Depreciation Date')
    dep_ref = fields.Char(string='Reference')
    dep_rate = fields.Char(string='Depreciation Rate')
    remark = fields.Char(string='Remark')

    def compute_depreciation_board(self):
        self.ensure_one()

        if self.per_depreciation_amount > 0 and self.prorata_date:
            # Clear existing unposted depreciation lines
            self.depreciation_move_ids.filtered(lambda x: x.state == 'draft').unlink()

            # Calculate remaining value and number of periods
            remaining_value = self.book_value
            depreciation_amount = self.per_depreciation_amount

            # Calculate exact number of periods needed
            number_of_periods = math.ceil(remaining_value / depreciation_amount)

            # Generate depreciation moves
            commands = []
            # Adjust base date to the last day of the initial month
            base_date = self.prorata_date + relativedelta(day=31)
            for i in range(number_of_periods):
                # For each period, add 'i' months and force the day to 31
                depreciation_date = base_date + relativedelta(months=i, day=31)  # KEY CHANGE

                # Calculate current period's depreciation
                if i == number_of_periods - 1:
                    current_depreciation = remaining_value  # Last period uses remaining value
                else:
                    current_depreciation = min(depreciation_amount, remaining_value)

                # Create the move (unchanged)
                vals = {
                    'asset_id': self.id,
                    'amount_total': current_depreciation,
                    'date': depreciation_date,
                    'ref': f'{self.name}: Depreciation',
                    'move_type': 'entry',
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': [
                        (0, 0, {
                            'name': f'{self.name}: Depreciation',
                            'debit': current_depreciation,
                            'account_id': self.account_depreciation_expense_id.id,
                        }),
                        (0, 0, {
                            'name': f'{self.name}: Depreciation',
                            'credit': current_depreciation,
                            'account_id': self.account_depreciation_id.id,
                        })
                    ]
                }
                move = self.env['account.move'].create(vals)
                move.write({'auto_post': 'at_date'})
                commands.append((4, move.id))

                remaining_value -= current_depreciation
                if remaining_value <= 0:
                    break

            self.write({'depreciation_move_ids': commands})
            return True

        return super(AccountAsset, self).compute_depreciation_board()