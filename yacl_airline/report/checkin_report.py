from odoo import api, models
from datetime import datetime, timedelta

class CheckinSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_checkin_summary'
    _description = 'Check-in Counter Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Convert string date to datetime object with correct format
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        # Subtract 6:30 from date
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)
        # Rest of your code remains the same
        checkins = self.env['checkin.counter.line'].search([
            ('start_time', '>=', adjusted_start_date),
            ('end_time', '<=', adjusted_end_date),
        ])

        summary = {}
        for line in checkins:
            airline = line.checkin_counter_id.airline_id.name
            if airline not in summary:
                summary[airline] = {
                    'airline': airline,
                    'frequency': 0,
                    'unique_flights': set(),
                    'amount': 0
                }

            summary[airline]['frequency'] += 1
            date = line.end_time.date()
            flight_no = line.flightno_id if line.flightno_id else False
            if flight_no:
                summary[airline]['unique_flights'].add((date, flight_no))
            summary[airline]['amount'] += line.amount

        report_data = []
        for airline, airline_data in summary.items():
            report_data.append({
                'airline': airline,
                'frequency': airline_data['frequency'],
                'unique_flight_count': len(airline_data['unique_flights']),
                'amount': airline_data['amount']
            })

        report_data.sort(key=lambda x: x['airline'])

        return {
            'doc_ids': docids,
            'doc_model': 'report.checkin.selection.wizard',
            'data': {
                'start_date': start_date,
                'end_date': end_date
            },
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }