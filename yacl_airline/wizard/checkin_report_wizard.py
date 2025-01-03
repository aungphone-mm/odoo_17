from odoo import fields, models
from datetime import timedelta

class ReportCheckinSelectionWizard(models.TransientModel):
    _name = 'report.checkin.selection.wizard'
    _description = 'Check-in Counter Report Selection Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=14)
    )
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    def action_generate_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),
            'end_date': fields.Date.to_string(self.end_date),
            'ids': self.ids,
            'model': 'report.checkin.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_checkin_summary_report').report_action(self, data=data)

    def action_generate_excel_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),
            'end_date': fields.Date.to_string(self.end_date),
            'ids': self.ids,
            'model': 'report.checkin.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_checkin_counter_xlsx').report_action(self, data=data)