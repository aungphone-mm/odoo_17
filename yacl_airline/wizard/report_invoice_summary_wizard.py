from odoo import fields, models, api
from datetime import datetime, timedelta

class ReportSelectionWizard(models.TransientModel):
    _name = 'report.selection.wizard'
    _transient_max_count = 100
    _description = 'Invoice Report Selection Wizard'

    airline_id = fields.Many2one('airline', string='Airline', required=True)
    module = fields.Selection([
        ('security', 'Security Service'),
        ('bridge', 'Boarding Bridge'),
        ('landing', 'Aircraft Landing'),
        ('checkin', 'Check-in Counter'),
        ('passenger', 'Passenger Service'),
    ], string='Module', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    adjusted_start_date = fields.Datetime(compute='_compute_adjusted_dates', store=True)
    adjusted_end_date = fields.Datetime(compute='_compute_adjusted_dates', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_adjusted_dates(self):
        for record in self:
            if record.start_date:
                start_datetime = datetime.combine(record.start_date, datetime.min.time())
                record.adjusted_start_date = start_datetime - timedelta(hours=6, minutes=30)
            else:
                record.adjusted_start_date = False

            if record.end_date:
                end_datetime = datetime.combine(record.end_date, datetime.min.time())
                record.adjusted_end_date = end_datetime - timedelta(hours=6, minutes=30)
            else:
                record.adjusted_end_date = False

    def action_generate_report(self):
        data = {
            'airline_id': self.airline_id.id,
            'module': self.module,
            'start_date': self.adjusted_start_date,
            'end_date': self.adjusted_end_date,
            'doc_ids': self.ids,
        }
        return self.env.ref('yacl_airline.action_invoice_summary_report').report_action(self, data=data)