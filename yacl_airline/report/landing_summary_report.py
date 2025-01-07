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
        non_schedule_summary = {}  # New dictionary for non-schedule entries

        for landing in landings:
            for line in landing.passenger_landing_line_ids:
                if landing.non_schedule:
                    # Use airline from the line for non-schedule
                    airline = line.airline_id.name or 'Unknown'
                    if airline not in non_schedule_summary:
                        non_schedule_summary[airline] = {
                            'airline': f"Non Schedule - {airline}",
                            'frequency': 0,
                            'amount': 0,
                            'tax_5': 0,
                            'total': 0
                        }

                    # Add to non-schedule airline specific row
                    non_schedule_summary[airline]['frequency'] += 1
                    non_schedule_summary[airline]['amount'] += line.amount
                    non_schedule_summary[airline]['tax_5'] += line.amount * 0.05
                    non_schedule_summary[airline]['total'] += line.amount * 1.05
                else:
                    # Regular scheduled flights
                    airline = landing.airline_id.name
                    if airline not in summary:
                        summary[airline] = {
                            'airline': airline,
                            'frequency': 0,
                            'amount': 0,
                            'tax_5': 0,
                            'total': 0
                        }

                    summary[airline]['frequency'] += 1
                    summary[airline]['amount'] += line.amount
                    summary[airline]['tax_5'] += line.amount * 0.05
                    summary[airline]['total'] += line.amount * 1.05

        # Combine regular and non-schedule entries
        report_data = list(summary.values()) + list(non_schedule_summary.values())

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }