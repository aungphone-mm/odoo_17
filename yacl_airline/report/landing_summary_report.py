from odoo import api, models
from datetime import datetime, timedelta

class LandingSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_landing_summary'
    _description = 'Landing Summary Report'

    def _get_report_values(self, docids, data=None):
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        # First adjust the end_date to 23:59:59
        end_date = end_date.replace(hour=23, minute=59, second=59)
        # Then subtract 6:30 from both dates
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)
        landing_lines = self.env['passenger.landing.line'].search([
            ('start_time', '>=', adjusted_start_date),
            ('start_time', '<=', adjusted_end_date),
        ])

        summary = {}
        non_schedule_summary = {}

        for line in landing_lines:
            landing = line.passenger_landing_id  # Access the related 'passenger.landing' record
            if landing.non_schedule:
                # Handle non-schedule flights
                airline = landing.airline_id.name
                if airline not in non_schedule_summary:
                    non_schedule_summary[airline] = {
                        'airline': f"Non Schedule - {airline}",
                        'frequency': 0,
                        'amount': 0,
                        'tax_5': 0,
                        'total': 0,
                        'remark': ''
                    }

                non_schedule_summary[airline]['frequency'] += 1
                non_schedule_summary[airline]['amount'] += line.amount
                non_schedule_summary[airline]['tax_5'] += line.amount * 0.05
                non_schedule_summary[airline]['total'] += line.amount * 1.05
            else:
                # Regular flights
                airline = landing.airline_id.name
                if airline not in summary:
                    summary[airline] = {
                        'airline': airline,
                        'frequency': 0,
                        'amount': 0,
                        'tax_5': 0,
                        'total': 0,
                        'remark': ''
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