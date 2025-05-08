from odoo import fields, models

class CashbookReportWizard(models.TransientModel):
    _name = 'cashbook.report.wizard'
    _description = 'Cashbook Report Wizard'
    _transient_max_count = 100

    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )

    def action_print_report(self):
        """Generate the cashbook report"""
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('yacl_airline.action_cashbook_report').report_action(self, data=data)