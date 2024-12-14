from odoo import fields, models

class AirlineChargesReportWizard(models.TransientModel):
    _name = 'airline.charges.report.wizard'
    _description = 'Airline Charges Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    def action_print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('yacl_airline.action_airline_charges_report').report_action(self, data=data)