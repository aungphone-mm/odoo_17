from odoo import models, fields, api
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
        for line in self.line_ids:
            # Check if partner_id exists in the line
            if line.partner_id and hasattr(line.partner_id, 'old_ac') and line.partner_id.old_ac:
                # Get old code from the line's partner
                line.old_account_code = line.partner_id.old_ac
            # Fallback to move's partner if needed
            elif self.partner_id and hasattr(self.partner_id, 'old_ac') and self.partner_id.old_ac:
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

        for line in self.line_ids:
            # Check if partner_id exists in the line
            if line.partner_id and hasattr(line.partner_id, 'old_ac') and line.partner_id.old_ac:
                # Get old code from the line's partner
                line.old_account_code = line.partner_id.old_ac
            # Fallback to move's partner if needed
            elif self.partner_id and hasattr(self.partner_id, 'old_ac') and self.partner_id.old_ac:
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

    # In AccountMove class
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

                # Calculate depreciable value in USD (remaining value)
                if move.asset_id:
                    # Get the initial book value
                    initial_value = move.asset_id.book_value_usd
                    # print(move.asset_id.original_value_usd,"originasdf vailer asu usd")
                    # Subtract cumulative depreciation to get remaining value
                    move.depreciable_value_usd = initial_value - move.cumulative_depreciation_usd
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
        sheet.set_column('A:A', 15)  # Date
        sheet.set_column('B:B', 15)  # Source Code
        sheet.set_column('C:C', 15)  # Reference
        sheet.set_column('D:D', 15)  # Cheque
        sheet.set_column('E:E', 15)  # DN/CN No.
        sheet.set_column('F:F', 40)  # Description
        sheet.set_column('G:G', 30)  # Name
        sheet.set_column('H:H', 20)  # Particular
        sheet.set_column('I:I', 15)  # USD(AMT)
        sheet.set_column('J:J', 15)  # Currency
        sheet.set_column('K:K', 15)  # Price
        sheet.set_column('L:L', 15)  # Amount
        sheet.set_column('M:M', 15)  # Main Account
        sheet.set_column('N:N', 25)  # Main Dept
        sheet.set_column('O:O', 15)  # Sub Account
        sheet.set_column('P:P', 30)  # Sub Dept
        sheet.set_column('Q:Q', 30)  # Note

        # Write title at the top center
        sheet.merge_range('A1:Q1', 'Journal Entries Export', title_format)

        # Define headers
        headers = [
            'Date',
            'Source Code',
            'Reference',
            'Cheque',
            'DN/CN No.',
            'Description',
            'Name',
            'Particular',
            'USD(AMT)',
            'Currency',
            'Price',
            'Amount',
            'Main Account',
            'Main Dept',
            'Sub Account',
            'Sub Dept',
            'Note'
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        # Process line data
        row = 2  # Start from row 2 (Excel row 3)

        # Write data for each line
        for line in self.line_ids:
            # Date - column A
            sheet.write(row, 0, self.date, date_format)

            # Source Code - column B
            source_code = self.journal_id.code if self.journal_id else ''
            sheet.write(row, 1, source_code, cell_format)

            # Reference - column C
            sheet.write(row, 2, self.ref or '', cell_format)

            # Cheque - column D (leaving empty as not specified)
            sheet.write(row, 3, '', cell_format)

            # DN/CN No. - column E (leaving empty as not specified)
            sheet.write(row, 4, '', cell_format)

            # Description - column F
            sheet.write(row, 5, line.name or '', cell_format)

            # Name - column G (partner name)
            partner_name = line.partner_id.name if line.partner_id else ''
            sheet.write(row, 6, partner_name, cell_format)

            # Particular - column H (label)
            label = line.label if hasattr(line, 'label') else ''
            sheet.write(row, 7, label, cell_format)

            # USD(AMT) - column I (amount_currency)
            # amount_currency = line.amount_currency if hasattr(line, 'amount_currency') else 0.0
            # sheet.write(row, 8, amount_currency, amount_format)

            # USD(AMT) - column I (amount_currency)
            amount_currency = line.amount_currency if hasattr(line, 'amount_currency') else 0.0
            # Get currency name for checking
            currency_name = line.currency_id.name if hasattr(line, 'currency_id') and line.currency_id else ''
            # Only write amount_currency if it's not USD
            if currency_name == 'USD':
                sheet.write(row, 8, amount_currency, amount_format)
            else:
                sheet.write(row, 8, '', cell_format)  # Empty string for mmk currency

            # Currency - column J
            sheet.write(row, 9, currency_name, cell_format)

            # Currency - column J
            currency_name = line.currency_id.name if hasattr(line, 'currency_id') and line.currency_id else ''
            sheet.write(row, 9, currency_name, cell_format)

            # Price - column K (currency_rate_display)
            rate = line.currency_rate_display if hasattr(line, 'currency_rate_display') else 0.0
            sheet.write(row, 10, rate, amount_format)

            # Amount - column L (debit)
            # sheet.write(row, 11, line.debit, amount_format)
            amount_currency = line.amount_currency if hasattr(line, 'amount_currency') else 0.0
            sheet.write(row, 11, amount_currency, amount_format)

            # Get account code and name
            account_code = line.account_id.code if line.account_id else ''
            account_name = line.account_id.name if line.account_id else ''

            # Main Account & Main Dept (Analytic) and Sub Account & Sub Dept (Account)
            analytic_code = ''
            analytic_name = ''

            # If account code doesn't start with '9', show in Main Account/Dept (analytic) columns
            if account_code and not account_code.startswith('9'):
                # Show in Main Account (analytic) columns
                analytic_code = account_code
                analytic_name = account_name

                # Sub Account (account) columns remain empty
                sheet.write(row, 14, '', cell_format)  # Sub Account
                sheet.write(row, 15, '', cell_format)  # Sub Dept
            else:
                # Show in Sub Account (account) columns
                sheet.write(row, 14, account_code, account_code_format)  # Sub Account
                sheet.write(row, 15, account_name, cell_format)  # Sub Dept

                # Get analytic information from analytic_distribution
                if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                    analytic_codes = []
                    analytic_names = []

                    for account_id, percentage in line.analytic_distribution.items():
                        if ',' in str(account_id):
                            account_ids = [int(x) for x in account_id.split(',')]
                            accounts = self.env['account.analytic.account'].browse(account_ids)
                            for account in accounts:
                                if account.exists():
                                    analytic_codes.append(account.code or '')
                                    analytic_names.append(account.name or '')
                        else:
                            account = self.env['account.analytic.account'].browse(int(account_id))
                            if account.exists():
                                analytic_codes.append(account.code or '')
                                analytic_names.append(account.name or '')

                    analytic_code = ' / '.join(analytic_codes) if analytic_codes else ''
                    analytic_name = ' / '.join(analytic_names) if analytic_names else ''

            # Write Main Account and Main Dept (Analytic)
            sheet.write(row, 12, analytic_code, cell_format)  # Main Account
            sheet.write(row, 13, analytic_name, cell_format)  # Main Dept

            # Note - column Q (leaving empty as not specified)
            sheet.write(row, 16, '', cell_format)

            row += 1

        # Calculate total amount (debit)
        total_debit = sum(line.debit for line in self.line_ids)

        # Add total row
        # total_row = len(self.line_ids) + 2
        # sheet.write(total_row, 11, total_debit, amount_format)  # Total Amount (debit)

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
    partner_id = fields.Many2one('res.partner', string='Partner',
                                              compute='_compute_partner',
                                              inverse='_inverse_partner',
                                              store=True)

    @api.depends('move_id.partner_id')
    def _compute_partner(self):
        for line in self:
            line.partner_id = line.move_id.partner_id

    def _inverse_partner(self):
        for line in self:
            if line.partner_id != line.move_id.partner_id:
                pass

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

