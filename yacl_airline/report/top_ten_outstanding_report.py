from odoo import api, models, fields
import datetime


class TopTenOutstandingReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_top_ten_outstanding'
    _description = 'Top Ten Outstanding Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        This method prepares the data for the Top Ten Outstanding report.
        It fetches the top 10 invoices with the highest outstanding amounts.
        """
        # Get the current date for the report
        current_date = fields.Date.today()

        # Find the top 10 outstanding invoices
        outstanding_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', current_date)
        ], order='amount_residual desc', limit=10)

        # Calculate total outstanding amount
        total_outstanding = sum(outstanding_invoices.mapped('amount_residual'))

        # Get company currency for formatting
        company_currency = self.env.company.currency_id

        # Prepare data for the report
        return {
            'doc_ids': [],  # We don't need specific doc_ids
            'doc_model': 'top.ten.outstanding.wizard',  # Using our wizard model instead
            'outstanding_invoices': outstanding_invoices,  # Changed from 'docs' to 'outstanding_invoices'
            'current_date': current_date,
            'total_outstanding': total_outstanding,
            'company_currency': company_currency,
            'get_days_overdue': self._get_days_overdue,
        }

    def _get_days_overdue(self, invoice):
        """Calculate how many days an invoice is overdue"""
        today = fields.Date.today()
        due_date = invoice.invoice_date_due
        if due_date and today > due_date:
            return (today - due_date).days
        return 0