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

        # Set column widths
        worksheet.set_column('A:A', 15)  # Date
        worksheet.set_column('B:B', 20)  # Move Name
        worksheet.set_column('C:C', 30)  # Account
        worksheet.set_column('D:D', 30)  # Description
        worksheet.set_column('E:E', 15)  # Partner
        worksheet.set_column('F:F', 15)  # Debit
        worksheet.set_column('G:G', 15)  # Credit

        # Write headers
        headers = ['Date', 'Move Name', 'Account', 'Description', 'Partner', 'Debit', 'Credit']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Get all move lines from the journal entries
        move_lines = self.env['account.move.line'].search([
            ('move_id.journal_id', '=', self.journal_id.id),
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

            if key not in grouped_data:
                grouped_data[key] = {
                    'date': line.date,
                    'move_name': move_name,
                    'account': line.account_id.name,
                    'description': line.name or '',
                    'partner': line.partner_id.name if line.partner_id else '',
                    'debit': 0.0,
                    'credit': 0.0,
                }

            # Sum debits and credits
            grouped_data[key]['debit'] += line.debit
            grouped_data[key]['credit'] += line.credit

        # Sort by move name and write to Excel
        row = 1
        for key in sorted(grouped_data.keys()):
            data = grouped_data[key]
            worksheet.write(row, 0, data['date'], date_format)
            worksheet.write(row, 1, data['move_name'])
            worksheet.write(row, 2, data['account'])
            worksheet.write(row, 3, data['description'])
            worksheet.write(row, 4, data['partner'])
            worksheet.write(row, 5, data['debit'], number_format)
            worksheet.write(row, 6, data['credit'], number_format)
            row += 1

        # Add totals row
        worksheet.write(row, 4, 'Total', header_format)
        worksheet.write_formula(row, 5, f'=SUM(F2:F{row})', number_format)
        worksheet.write_formula(row, 6, f'=SUM(G2:G{row})', number_format)

        # Close workbook
        workbook.close()

        # Set binary data to download
        out = base64.encodebytes(output.getvalue())
        file_name = f'Journal_Report_{self.journal_id.name}_{self.start_date}_{self.end_date}.xlsx'

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