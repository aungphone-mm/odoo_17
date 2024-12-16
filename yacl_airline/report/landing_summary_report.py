from odoo import api, models

class LandingSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_landing_summary'
    _description = 'Landing Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data['start_date']
        end_date = data['end_date']

        landings = self.env['passenger.landing'].search([
            ('state', '=', 'invoiced'),
            ('start_time', '>=', start_date),
            ('start_time', '<=', end_date),
        ])

        summary = {}
        for landing in landings:
            airline = landing.airline_id.name
            if airline not in summary:
                summary[airline] = {
                    'airline': airline,
                    'frequency': 0,
                    'amount': 0,
                    'tax_5': 0,
                    'total': 0
                }

            for line in landing.passenger_landing_line_ids:
                summary[airline]['frequency'] += 1
                summary[airline]['amount'] += line.amount
                summary[airline]['tax_5'] += line.amount * 0.05
                summary[airline]['total'] += line.amount * 1.05

        # Add non-schedule row
        non_schedule = {
            'airline': 'Non Schedule',
            'frequency': 0,
            'amount': 0,
            'tax_5': 0,
            'total': 0
        }

        report_data = list(summary.values())
        report_data.append(non_schedule)

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }