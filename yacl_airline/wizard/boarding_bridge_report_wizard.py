from datetime import timedelta
from odoo import fields, models

class BoardingBridgeReportWizard(models.TransientModel):
    _name = 'boarding.bridge.report.wizard'
    _description = 'Boarding Bridge Report Wizard'
    _transient_max_count = 100

    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    def action_print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('yacl_airline.action_boarding_bridge_report').report_action(self, data=data)