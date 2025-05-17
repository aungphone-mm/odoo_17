# journal_report_wizard.py
from datetime import timedelta
import io
import base64
import xlsxwriter
from odoo import fields, models, api


class JournalReportWizard(models.TransientModel):
    _name = 'journal.report.wizard'
    _transient_max_count = 100
    _description = 'Journal Report Wizard'

    # Basic fields for the report
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Excel export fields
    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('File Name')

    # Computed fields
    move_ids = fields.Many2many(
        'account.move',
        string='Journal Entries',
        compute='_compute_journal_entries'
    )

    total_debit = fields.Monetary(string='Total Debit', compute='_compute_totals', currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Credit', compute='_compute_totals', currency_field='currency_id')
    balance = fields.Monetary(string='Balance', compute='_compute_totals', currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')

    @api.depends('journal_id', 'start_date', 'end_date', 'company_id')
    def _compute_journal_entries(self):
        for wizard in self:
            domain = [
                ('journal_id', '=', wizard.journal_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date),
                ('company_id', '=', wizard.company_id.id),
                # ('state', '=', 'posted')
            ]
            wizard.move_ids = self.env['account.move'].search(domain)

    @api.depends('move_ids')
    def _compute_totals(self):
        for wizard in self:
            move_lines = self.env['account.move.line'].search([
                ('move_id', 'in', wizard.move_ids.ids)
            ])
            wizard.total_debit = sum(move_lines.mapped('debit'))
            wizard.total_credit = sum(move_lines.mapped('credit'))
            wizard.balance = wizard.total_debit - wizard.total_credit

    def action_generate_report(self):
        data = {
            'journal_id': self.journal_id.id,
            'journal_name': self.journal_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'ids': self.ids,
            'model': 'journal.report.wizard',
        }
        return self.env.ref('yacl_airline.action_journal_report').report_action(self, data=data)

    def action_export_excel(self):
        """Export journal entries to Excel with account_id grouping by move name"""
        # Create workbook and add worksheet
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Journal Entries')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D3D3D3',
            'border': 1
        })

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})

        # Set column widths for new structure - fixed duplicate column assignments
        # Set column widths based on the new headers
        worksheet.set_column('A:A', 15)  # REFERENCE
        worksheet.set_column('B:B', 15)  # CHEQUE (new column)
        worksheet.set_column('C:C', 15)  # DCNOTENO
        worksheet.set_column('D:D', 20)  # ACCOUNT GROUP (new column)
        worksheet.set_column('E:E', 15)  # ACCOUNT RECEIVABLE
        worksheet.set_column('F:F', 15)  # DATE
        worksheet.set_column('G:G', 20)  # NAME (renamed from 'partner')
        worksheet.set_column('H:H', 30)  # DESCRIPTION (renamed from 'label')
        worksheet.set_column('I:I', 30)  # PARTICULAR (new column)
        worksheet.set_column('J:J', 15)  # AMOUNT
        worksheet.set_column('K:K', 15)  # MAIN A/C
        worksheet.set_column('L:L', 15)  # SUB A/C
        worksheet.set_column('M:M', 15)  # JOURNAL
        worksheet.set_column('N:N', 15)  # Currency
        worksheet.set_column('O:O', 15)  # Amount in Currency
        worksheet.set_column('P:P', 15)  # Exchange Rate
        worksheet.set_column('Q:Q', 15)  # MAIN DEPT
        worksheet.set_column('R:R', 15)  # SUB DEPT
        worksheet.set_column('S:S', 10)  # QTY
        worksheet.set_column('T:T', 10)  # UNIT
        worksheet.set_column('U:U', 15)  # PRICE
        worksheet.set_column('V:V', 20)  # NOTE
        worksheet.set_column('W:W', 15)  # BATCHNO
        worksheet.set_column('X:X', 15)  # ENTRYNO
        worksheet.set_column('Y:Y', 10)  # LINE
        worksheet.set_column('Z:Z', 15)  # SOURCE CODE
        worksheet.set_column('AA:AA', 10)  # State (moved to new position)

        # Write headers - removed header column
        headers = ['REFERENCE', 'CHEQUE', 'DCNOTENO', 'ACCOUNT GROUP',
                   'DATE', 'NAME','DESCRIPTION', 'PARTICULAR', 'AMOUNT', 'MAIN A/C', 'SUB A/C','JOURNAL',
                   'Currency', 'Amount in Currency', 'Exchange Rate',
                   'MAIN DEPT', 'SUB DEPT', 'QTY', 'UNIT', 'PRICE', 'NOTE',
                   'BATCHNO', 'ENTRYNO', 'LINE', 'SOURCE CODE','State']

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Get all move lines from the journal entries
        move_lines = self.env['account.move.line'].search([
            # ('move_id.journal_id', '=', self.journal_id.id),
            ('move_id.date', '>=', self.start_date),
            ('move_id.date', '<=', self.end_date),
            ('move_id.company_id', '=', self.company_id.id),
        ])

        # Group data by move and account
        grouped_data = {}
        for line in move_lines:
            move_name = line.move_id.name or 'Unnamed'
            account_id = line.account_id.id
            key = (move_name, account_id)

            # Improved analytic code extraction
            analytic_code = ''
            # Try different ways to access analytic account in Odoo 17
            if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                # For Odoo 17's new analytic distribution dict format
                # Get the first analytic account code if available
                analytic_ids = list(line.analytic_distribution.keys())
                if analytic_ids:
                    analytic_account = self.env['account.analytic.account'].browse(int(analytic_ids[0]))
                    analytic_code = analytic_account.code or analytic_account.name or ''
            elif hasattr(line, 'analytic_account_id') and line.analytic_account_id:
                # Traditional way
                analytic_code = line.analytic_account_id.code or line.analytic_account_id.name or ''
            elif hasattr(line, 'analytic_tag_ids') and line.analytic_tag_ids:
                # Via tags
                analytic_code = ', '.join(line.analytic_tag_ids.mapped('name'))

            currency_name = line.move_id.currency_id.name if line.move_id.currency_id else ''
            narration = line.move_id.inv_desc if hasattr(line.move_id, 'inv_desc') else ''

            # Determine main_ac based on the account type
            main_ac = ''
            if line.account_id:
                account_name = line.account_id.name if hasattr(line.account_id, 'name') else ''
                # Check if account is a Debtors account
                if 'Debtor' in account_name:
                    # First try using partner's old_ac from the line
                    if line.partner_id and hasattr(line.partner_id, 'old_ac') and line.partner_id.old_ac:
                        main_ac = line.partner_id.old_ac
                    # Fallback to move's partner if needed
                    elif line.move_id.partner_id and hasattr(line.move_id.partner_id,
                                                             'old_ac') and line.move_id.partner_id.old_ac:
                        main_ac = line.move_id.partner_id.old_ac
                    # If still no value, use account name as fallback
                    else:
                        main_ac = account_name
                else:
                    # For non-Debtor accounts, use account name as before
                    main_ac = line.account_id.code

            if key not in grouped_data:
                grouped_data[key] = {
                    'reference': line.ref_no or '',
                    'analytic_code': analytic_code,
                    'dcnoteno': line.move_id.name or '',
                    'account_receivable_id': line.move_id.account_receivable_id.name or '',
                    'date': line.date,
                    'partner': line.partner_id.name if line.partner_id else '',
                    'account_group': line.ref_name or '',
                    'ref_desc': line.ref_desc or '',
                    'label': line.name or '',
                    'amount': 0.0,
                    'main_ac': main_ac,
                    # 'main_ac': line.account_id.code.split('/')[
                    #     0] if line.account_id.code and '/' in line.account_id.code else (line.account_id.code or ''),
                    'sub_ac': line.account_id.code.split('/')[
                        1] if line.account_id.code and '/' in line.account_id.code else '',
                    'journal': line.move_id.journal_id.name or '',  # Added journal name
                    'main_dept': '',
                    'sub_dept': '',
                    'qty': line.quantity if hasattr(line, 'quantity') else 0,
                    'unit': line.product_uom_id.name if hasattr(line, 'product_uom_id') and line.product_uom_id else '',
                    'price': line.price_unit if hasattr(line, 'price_unit') else 0.0,
                    'note': narration,
                    'batchno': '',
                    # 'entryno': line.id,
                    # 'line': line.sequence if hasattr(line, 'sequence') else 0,
                    'entryno': '',
                    'line': '',
                    'source_code': line.move_id.journal_id.code or '',
                    'debit': 0.0,
                    'credit': 0.0,
                    'currency': currency_name,
                    'amount_currency': 0.0,
                    'exchange_rate': line.currency_rate_display if hasattr(line, 'currency_rate_display') else '',
                    'state': line.move_id.state,
                }

            # Sum debits and credits
            grouped_data[key]['debit'] += line.debit
            grouped_data[key]['credit'] += line.credit
            # Calculate amount as debit - credit
            grouped_data[key]['amount'] = grouped_data[key]['debit'] - grouped_data[key]['credit']
            # Add amount_currency
            grouped_data[key]['amount_currency'] += line.amount_currency if hasattr(line, 'amount_currency') else 0.0

        # Sort by move name and write to Excel
        row = 1
        for key in sorted(grouped_data.keys()):
            data = grouped_data[key]

            # Write data to worksheet - fixed column indices
            worksheet.write(row, 0, data['reference'])
            worksheet.write(row, 1, data['analytic_code'])
            worksheet.write(row, 2, data['dcnoteno'])
            worksheet.write(row, 5, data['account_group'])
            worksheet.write(row, 3, data['account_receivable_id']) #ACCOUNT RECEIVABLE
            worksheet.write(row, 4, data['date'], date_format)
            worksheet.write(row, 5, data['partner'])
            worksheet.write(row, 6, data['ref_desc'])#Particular
            worksheet.write(row, 7, data['label'])
            worksheet.write(row, 8, data['amount'], number_format)
            worksheet.write(row, 9, data['main_ac'])
            worksheet.write(row, 10, data['sub_ac'])
            worksheet.write(row, 11, data['journal'])
            worksheet.write(row, 12, data['currency'])
            worksheet.write(row, 13, data['amount_currency'], number_format)
            worksheet.write(row, 14, data['exchange_rate'])
            worksheet.write(row, 15, data['main_dept'])
            worksheet.write(row, 16, data['sub_dept'])
            worksheet.write(row, 17, data['qty'])
            worksheet.write(row, 18, data['unit'])
            worksheet.write(row, 19, data['price'], number_format)
            worksheet.write(row, 20, data['note'])
            worksheet.write(row, 21, data['batchno'])
            worksheet.write(row, 22, data['entryno'])
            worksheet.write(row, 23, data['line'])
            worksheet.write(row, 24, data['source_code'])
            worksheet.write(row, 25, data['state'])

            row += 1

        # Add totals row - updated formula to match AMOUNT column
        worksheet.write(row, 6, 'Total', header_format)
        worksheet.write_formula(row, 7, f'=SUM(H2:H{row})', number_format)

        # Close workbook
        workbook.close()

        # Set binary data to download
        out = base64.encodebytes(output.getvalue())
        file_name = f'Journal_Report_{self.start_date}_{self.end_date}.xlsx'

        # Save the file
        self.write({
            'excel_file': out,
            'file_name': file_name,
        })

        # Return the action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=excel_file&download=true&filename={file_name}',
            'target': 'self',
        }