from odoo import api, models
from datetime import datetime, timedelta


class LandingSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_landing_summary'
    _description = 'Landing Summary Report'

    def _get_report_values(self, docids, data=None):
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        # Adjust the end_date to include the full day
        end_date = end_date.replace(hour=23, minute=59, second=59)
        # Apply the 6:30 hour adjustment for Myanmar timezone if needed
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)

        # Search account move lines with the specified journal
        move_lines = self.env['account.move.line'].search([
            ('move_id.date', '>=', adjusted_start_date.date()),
            ('move_id.date', '<=', adjusted_end_date.date()),
            ('move_id.journal_id.name', '=', 'Landing Charges (International)'),
            ('move_id.move_type', '=', 'out_invoice'),  # Only customer invoices
        ])

        # Group by airline
        summary = {}

        for line in move_lines:
            # You'll need to determine how airlines are linked to accounting entries
            # This assumes there's a partner_id that represents the airline
            # You may need to adjust this based on your specific data model
            partner = line.partner_id.name

            if partner not in summary:
                summary[partner] = {
                    'airline': partner,
                    'frequency': 0,
                    'amount': 0,
                    'tax_5': 0,
                    'total': 0,
                    'remark': ''
                }

            # Increment frequency - you may need logic to count unique flights
            summary[partner]['frequency'] += 1
            # Use the debit amount for revenue entries
            line_amount = line.credit if line.credit > 0 else 0
            summary[partner]['amount'] += line_amount
            summary[partner]['tax_5'] += line_amount * 0.05
            summary[partner]['total'] += line_amount * 1.05

        report_data = list(summary.values())

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }