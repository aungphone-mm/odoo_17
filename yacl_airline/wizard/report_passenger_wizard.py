# wizard/report_selection_wizard.py
from datetime import timedelta
from odoo import fields, models

class ReportPassengerSelectionWizard(models.TransientModel):
    _name = 'report.passenger.selection.wizard'
    _transient_max_count = 100
    _description = 'Passenger Report Selection Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    flight_type = fields.Selection([
        ('all', 'All'),
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], string='Flight Type', required=True, default='all')

    def action_generate_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),
            'end_date': fields.Date.to_string(self.end_date),
            'flight_type': self.flight_type,
            'ids': self.ids,
            'model': 'report.passenger.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_passenger_summary_report').report_action(self, data=data)