from odoo import api, models, fields


class JournalReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_journal'
    _description = 'Journal Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        This method prepares the data for the Journal report including all calculations.
        """
        if not data:
            return {}

        # Get the company record, not just the ID
        company = self.env['res.company'].browse(data['company_id'])

        # Get journal entries
        journal_entries = self.env['account.move'].search([
            ('journal_id', '=', data['journal_id']),
            ('date', '>=', data['start_date']),
            ('date', '<=', data['end_date']),
            ('company_id', '=', data['company_id']),
            # ('state', '=', 'posted')
        ], order='date')

        # Get all move lines
        move_lines = self.env['account.move.line'].search([
            ('move_id.journal_id', '=', data['journal_id']),
            ('move_id.date', '>=', data['start_date']),
            ('move_id.date', '<=', data['end_date']),
            ('move_id.company_id', '=', data['company_id']),
            # ('move_id.state', '=', 'posted')
        ])

        # Calculate totals
        total_debit = sum(move_lines.mapped('debit'))
        total_credit = sum(move_lines.mapped('credit'))
        balance = total_debit - total_credit

        # Process move lines for display with running balance
        processed_lines = []
        running_balance = 0

        for move in journal_entries:
            for line in move.line_ids:
                running_balance += line.debit - line.credit
                processed_lines.append({
                    'date': line.date,
                    'move_ref': line.move_id.reference_no or '',
                    'partner_name': line.partner_id.name if line.partner_id else '',
                    'description': line.name or '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                    'currency': line.company_currency_id,
                })

        return {
            'doc_ids': docids,
            'doc_model': 'journal.report.wizard',
            'data': data,
            'journal_entries': journal_entries,
            'processed_lines': processed_lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': balance,
            'company_currency': company.currency_id,
            'company': company,  # Important: Pass the company record, not just the ID
            'docs': self.env['journal.report.wizard'].browse(docids),
        }