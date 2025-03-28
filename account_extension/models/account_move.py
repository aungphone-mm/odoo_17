from odoo import models, fields, api
from odoo import models, api
import xlsxwriter
import base64
from io import BytesIO

class AccountMove(models.Model):
    _inherit = 'account.move'

    custom_header = fields.Html(string='Custom Header')
    custom_note = fields.Html(string='Custom Note')

    account_receivable_id = fields.Many2one(
        'account.account',
        string='Account Receivable',
        domain="[('account_type', '=', 'asset_receivable')]",
        default=lambda self: self._get_default_account_receivable(),
        compute='_compute_account_receivable_id',
        store=True,
        readonly=False
    )
    custom_tax_amount = fields.Monetary(
        string="Custom Tax Amount",
        compute="_compute_custom_tax_amount",
        store=True
    )

    show_custom_tax = fields.Boolean(
        string="Show Custom Tax",
        compute="_compute_custom_tax_amount",
        store=True
    )

    @api.depends('amount_untaxed', 'invoice_line_ids.tax_ids')
    def _compute_custom_tax_amount(self):
        for move in self:
            # Only calculate custom tax if the invoice lines have taxes applied
            has_tax = any(line.tax_ids for line in move.invoice_line_ids)
            if has_tax:
                # 5% of untaxed amount
                move.custom_tax_amount = move.amount_untaxed * 0.05
                move.show_custom_tax = True
            else:
                move.custom_tax_amount = 0.0
                move.show_custom_tax = False

    def action_apply_old_account_code(self):
        """Apply partner's old account code to all journal items"""
        self.ensure_one()
        if self.partner_id and hasattr(self.partner_id, 'old_ac') and self.partner_id.old_ac:
            for line in self.line_ids:
                line.old_account_code = self.partner_id.old_ac
        return True


    # For AccountMove class
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update account receivable when partner changes"""
        if self.partner_id and self.move_type in ('out_invoice', 'out_refund'):
            self.account_receivable_id = self.partner_id.property_account_receivable_id

            # Update old_account_code on line items if they exist
            if hasattr(self.partner_id, 'old_ac') and self.partner_id.old_ac:
                for line in self.line_ids:
                    line.old_account_code = self.partner_id.old_ac

    # Add this method to the AccountMove class
    def _set_account_based_on_partner(self):
        """Set accounts based on partner for move lines"""
        if self.partner_id:
            for line in self.line_ids:
                # Set old account code if it exists on the partner
                if hasattr(self.partner_id, 'old_ac') and self.partner_id.old_ac:
                    line.old_account_code = self.partner_id.old_ac

                # Set appropriate account based on move type
                if self.move_type in (
                'out_invoice', 'out_refund') and not line.account_id.account_type == 'asset_receivable':
                    line.account_id = self.partner_id.property_account_receivable_id
                elif self.move_type in (
                'in_invoice', 'in_refund') and not line.account_id.account_type == 'liability_payable':
                    line.account_id = self.partner_id.property_account_payable_id

    # def write(self, vals):
    #     # First perform the original write operation
    #     res = super().write(vals)
    #
    #     # If payment reference was updated
    #     if 'payment_reference' in vals:
    #         for move in self:
    #             move.line_ids.write({
    #                 'ref': move.payment_reference
    #             })
    #     return res
    # @api.onchange('payment_reference')
    # def _onchange_payment_reference(self):
    #     for move in self:
    #         if move.payment_reference:
    #             # Update all journal items with the payment reference
    #             for line in move.line_ids:
    #                 line.ref = move.payment_reference
    @api.depends('line_ids', 'line_ids.account_id', 'partner_id')
    def _compute_account_receivable_id(self):
        """Compute account_receivable_id from existing move lines or partner"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # First try to get from existing receivable line
                receivable_line = move.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                )
                if receivable_line:
                    move.account_receivable_id = receivable_line[0].account_id
                # Fallback to partner's default receivable
                elif move.partner_id:
                    move.account_receivable_id = move.partner_id.property_account_receivable_id
                else:
                    move.account_receivable_id = False

    @api.model
    def _get_default_account_receivable(self):
        """Get default account receivable from partner or company"""
        if self.partner_id:
            return self.partner_id.property_account_receivable_id

        # Get default receivable from chart of accounts
        return self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('account_type', '=', 'asset_receivable'),
            ('deprecated', '=', False)
        ], limit=1)

    def _get_available_account_receivables(self):
        """Get available account receivables including those used in existing moves"""
        domain = [
            '|',
            ('account_type', '=', 'asset_receivable'),
            ('id', '=', self.account_receivable_id.id),  # Include current account even if deprecated
            ('company_id', '=', self.company_id.id),
        ]
        return self.env['account.account'].search(domain)

    @api.onchange('account_receivable_id')
    def _onchange_account_receivable(self):
        """Update journal items when account receivable changes"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                receivable_line = move.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                )
                if receivable_line and move.account_receivable_id:
                    receivable_line.account_id = move.account_receivable_id

    @api.onchange('partner_id')
    def _onchange_partner_account_receivable(self):
        """Update account receivable when partner changes"""
        if self.partner_id and self.move_type in ('out_invoice', 'out_refund'):
            self.account_receivable_id = self.partner_id.property_account_receivable_id

    def action_print_custom_invoice(self):
        """Print the custom invoice report"""
        self.ensure_one()
        return self.env.ref('account_extension.action_report_custom_invoice').report_action(self)

    depreciation_usd = fields.Float(
        string='Depreciation (USD)',
        compute='_compute_usd_amounts',
        store=True
    )
    cumulative_depreciation_usd = fields.Float(
        string='Cumulative Depreciation (USD)',
        compute='_compute_usd_amounts',
        store=True
    )
    depreciable_value_usd = fields.Float(
        string='Depreciable Value (USD)',
        compute='_compute_usd_amounts',
        store=True
    )

    @api.depends('amount_total', 'asset_id.exchange_rate', 'asset_id.asset_currency')
    def _compute_usd_amounts(self):
        for move in self:
            if move.asset_id.asset_currency == 'USD' and move.asset_id.exchange_rate:
                # Convert amount_total to USD
                move.depreciation_usd = move.amount_total / move.asset_id.exchange_rate

                # Calculate cumulative depreciation in USD
                previous_moves = self.env['account.move'].search([
                    ('asset_id', '=', move.asset_id.id),
                    ('date', '<=', move.date),
                    ('state', '!=', 'cancel')
                ], order='date')

                cumulative_mmk = sum(m.amount_total for m in previous_moves)
                move.cumulative_depreciation_usd = cumulative_mmk / move.asset_id.exchange_rate

                # Calculate depreciable value in USD
                if move.asset_id:
                    move.depreciable_value_usd = move.asset_id.book_value_usd
            else:
                move.depreciation_usd = 0.0
                move.cumulative_depreciation_usd = 0.0
                move.depreciable_value_usd = 0.0
    def action_journal_excel_download(self):
        """Export journal entries to Excel file"""
        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Journal Entries')

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
            'align': 'center',
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

        # Format for account codes - text format to preserve leading zeros
        account_code_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'border_color': '#C0C0C0',
            'num_format': '@'
        })

        amount_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'border_color': '#C0C0C0',
            'num_format': '#,##0.00'
        })

        date_format = workbook.add_format({
            'align': 'center',
            'border': 1,
            'border_color': '#C0C0C0',
            'num_format': 'dd/mm/yyyy'
        })

        # Set column widths
        sheet.set_column('A:A', 15)  # Entry Number
        sheet.set_column('B:B', 15)  # Reference
        sheet.set_column('C:C', 15)  # Date
        sheet.set_column('D:D', 20)  # Journal
        sheet.set_column('E:E', 15)  # Account Code
        sheet.set_column('F:F', 30)  # Account Name
        sheet.set_column('G:G', 40)  # Description
        sheet.set_column('H:H', 15)  # Old Account
        sheet.set_column('I:I', 30)  # Partner
        sheet.set_column('J:J', 20)  # Label
        sheet.set_column('K:K', 20)  # Analytic Account
        sheet.set_column('L:L', 15)  # Amount
        sheet.set_column('M:M', 15)  # Exchange Rate
        sheet.set_column('N:N', 15)  # Tax
        sheet.set_column('O:O', 15)  # Debit
        sheet.set_column('P:P', 15)  # Credit

        # Write title at the top center
        sheet.merge_range('A1:P1', 'Journal Entries Export', title_format)

        # Define headers
        headers = [
            'Entry Number',
            'Reference',
            'Date',
            'Journal',
            'Account Code',
            'Account Name',
            'Description',
            'Old Account',
            'Partner',
            'Label',
            'Analytic Account',
            'Amount',
            'Exchange Rate',
            'Tax',
            'Debit',
            'Credit'
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        # Process line data
        row = 2  # Start from row 2 (Excel row 3)

        # Calculate total amounts
        total_debit = sum(line.debit for line in self.line_ids)
        total_credit = sum(line.credit for line in self.line_ids)

        # Write data for each line
        for line in self.line_ids:
            # Entry Number - column A
            sheet.write(row, 0, self.name or '', cell_format)

            # Reference - column B
            sheet.write(row, 1, self.ref or '', cell_format)

            # Date - column C
            sheet.write(row, 2, self.date, date_format)

            # Journal - column D
            journal_name = self.journal_id.name if self.journal_id else ''
            sheet.write(row, 3, journal_name, cell_format)

            # Account Code - column E
            account_code = line.account_id.code if line.account_id else ''
            sheet.write(row, 4, account_code, account_code_format)

            # Account Name - column F
            account_name = line.account_id.name if line.account_id else ''
            sheet.write(row, 5, account_name, cell_format)

            # Description - column G
            sheet.write(row, 6, line.name or '', cell_format)

            # Old Account - column H
            old_account = ''
            if hasattr(line, 'old_account_id') and line.old_account_id:
                old_account = line.old_account_id.code
            sheet.write(row, 7, old_account, cell_format)

            # Partner - column I
            partner_name = line.partner_id.name if line.partner_id else ''
            sheet.write(row, 8, partner_name, cell_format)

            # Label - column J
            label = line.label if hasattr(line, 'label') else ''
            sheet.write(row, 9, label, cell_format)

            # Analytic Account - column K
            analytic_account = ''
            if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                analytic_accounts = []
                for account_id, percentage in line.analytic_distribution.items():
                    if ',' in str(account_id):
                        account_ids = [int(x) for x in account_id.split(',')]
                        accounts = self.env['account.analytic.account'].browse(account_ids)
                        analytic_accounts.extend(accounts)
                    else:
                        account = self.env['account.analytic.account'].browse(int(account_id))
                        analytic_accounts.append(account)

                # Get names
                if analytic_accounts:
                    analytic_names = [account.name for account in analytic_accounts if
                                      account.exists() and account.name]
                    analytic_account = ' / '.join(analytic_names) if analytic_names else ''

            sheet.write(row, 10, analytic_account, cell_format)

            # Amount - column L
            amount = line.balance
            sheet.write(row, 11, abs(amount), amount_format)

            # Exchange Rate - column M
            exchange = line.amount_currency if hasattr(line, 'amount_currency') else 0.0
            sheet.write(row, 12, exchange, amount_format)

            # Tax - column N
            tax = ''
            if hasattr(line, 'tax_line_id') and line.tax_line_id:
                tax = line.tax_line_id.name
            sheet.write(row, 13, tax, cell_format)

            # Debit - column O
            sheet.write(row, 14, line.debit, amount_format)

            # Credit - column P
            sheet.write(row, 15, line.credit, amount_format)

            row += 1

        # Add total row
        total_row = len(self.line_ids) + 2
        sheet.write(total_row, 14, total_debit, amount_format)
        sheet.write(total_row, 15, total_credit, amount_format)

        workbook.close()
        output.seek(0)

        # Generate attachment
        xlsx_data = output.getvalue()
        file_name = f'Journal_Entry_{self.name}.xlsx'

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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # The ref field already exists in account.move.line
    ref_no = fields.Char(string='Reference No', readonly=False)
    note = fields.Char(string='Note')
    received_date = fields.Char(string='Received Date')
    ref_name = fields.Char(string="Name")
    ref_desc = fields.Char(string="Description")
    old_account_code = fields.Char(string='Old Account Code', help='Legacy account code that will auto-fill partner')

    # Changed from Many2many to Many2one for dropdown behavior
    old_account_code_partner_id = fields.Many2one('res.partner', string='Select Partner',
                                                  help='Select a partner matching the old account code')

    # Keep this as a Many2many for displaying all options
    old_account_code_partner_options = fields.Many2many('res.partner', string='Matching Partners',
                                                        compute='_compute_matching_partners')

    @api.onchange('old_account_code')
    def _onchange_old_account_code(self):
        if self.old_account_code:
            # Search for partners with this old account code
            partners = self.env['res.partner'].search([('old_ac', '=', self.old_account_code)])

            # Update the many2many field to show matching partners
            self.old_account_code_partner_options = [(6, 0, partners.ids)]

            # Clear the dropdown selection
            self.old_account_code_partner_id = False

            if len(partners) == 1:
                # If only one partner, auto-select it in the dropdown
                self.old_account_code_partner_id = partners.id
                # Partner_id will be set by the onchange of old_account_code_partner_id
            elif len(partners) == 0:
                # No matching partners
                return {
                    'warning': {
                        'title': 'No Partners Found',
                        'message': f'No partners found with old account code: {self.old_account_code}'
                    }
                }
        else:
            # Clear fields when old_account_code is empty
            self.old_account_code_partner_options = [(5, 0, 0)]
            self.old_account_code_partner_id = False
            self.partner_id = False

    @api.depends('old_account_code')
    def _compute_matching_partners(self):
        for line in self:
            if line.old_account_code:
                partners = self.env['res.partner'].search([('old_ac', '=', line.old_account_code)])
                line.old_account_code_partner_options = [(6, 0, partners.ids)]
            else:
                line.old_account_code_partner_options = [(6, 0, [])]

    @api.onchange('old_account_code_partner_id')
    def _onchange_old_account_code_partner_id(self):
        # When a partner is selected from the dropdown, update the partner_id
        if self.old_account_code_partner_id:
            self.partner_id = self.old_account_code_partner_id
            self._set_account_based_on_partner()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self._set_account_based_on_partner()

    def _set_account_based_on_partner(self):
        # Set account based on selected partner
        if self.partner_id:
            if self.move_id.move_type in ('out_invoice', 'out_refund'):
                self.account_id = self.partner_id.property_account_receivable_id.id
            elif self.move_id.move_type in ('in_invoice', 'in_refund'):
                self.account_id = self.partner_id.property_account_payable_id.id

    # @api.onchange('old_account_code')
    # def _onchange_old_account_code(self):
    #     if self.old_account_code:
    #         # Search for partner with this old account code
    #         partner = self.env['res.partner'].search([('old_ac', '=', self.old_account_code)], limit=1)
    #         if partner:
    #             self.partner_id = partner.id
    #             # You may also want to set account based on partner if needed
    #             if self.move_id.move_type in ('out_invoice', 'out_refund'):
    #                 self.account_id = partner.property_account_receivable_id.id
    #             elif self.move_id.move_type in ('in_invoice', 'in_refund'):
    #                 self.account_id = partner.property_account_payable_id.id

