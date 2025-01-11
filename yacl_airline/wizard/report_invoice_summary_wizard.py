from odoo import fields, models

class ReportSelectionWizard(models.TransientModel):
    _name = 'report.selection.wizard'
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


    def action_generate_report(self):
        data = {
            'airline_id': self.airline_id.id,
            'module': self.module,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'doc_ids': self.ids,
        }
        return self.env.ref('yacl_airline.action_invoice_summary_report').report_action(self, data=data)