from odoo import api, models

class CheckinSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_checkin_summary'
    _description = 'Check-in Counter Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # if not data:
        #     data = {}

        # start_date = data.get('start_date')
        # end_date = data.get('end_date')
        start_date = data['start_date']
        end_date = data['end_date']

        checkins = self.env['checkin.counter'].search([
            # ('state', '=', 'invoiced'),
            ('start_time', '>=', start_date),
            ('start_time', '<=', end_date),
        ])

        summary = {}
        for checkin in checkins:
            airline = checkin.airline_id.name
            if airline not in summary:
                summary[airline] = {
                    'airline': airline,
                    'frequency': 0,
                    'unique_flights': set(),
                    'amount': 0
                }

            for line in checkin.checkin_counter_line_ids:
                summary[airline]['frequency'] += 1
                date = line.end_time.date()
                flight_no = line.flightno_id if line.flightno_id else False  # Handle possible None value
                if flight_no:  # Only add if flight_no exists
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
