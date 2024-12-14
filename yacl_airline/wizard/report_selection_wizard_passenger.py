# wizard/report_selection_wizard.py
from odoo import fields, models

class ReportSelectionWizard(models.TransientModel):
    _name = 'report.passenger.selection.wizard'
    _description = 'Passenger Report Selection Wizard'

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    def action_generate_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),  # Convert to string
            'end_date': fields.Date.to_string(self.end_date),
            'ids': self.ids,
            'model': 'report.passenger.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_passenger_summary_report').report_action(self, data=data)