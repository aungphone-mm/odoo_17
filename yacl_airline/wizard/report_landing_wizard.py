# wizard/report_selection_wizard_landing.py
from datetime import timedelta
from odoo import fields, models

class ReportLandingSelectionWizard(models.TransientModel):
    _name = 'report.landing.selection.wizard'
    _description = 'Landing Report Selection Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    def action_generate_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),
            'end_date': fields.Date.to_string(self.end_date),
            'ids': self.ids,
            'model': 'report.landing.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_landing_summary_report').report_action(self, data=data)