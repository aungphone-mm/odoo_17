from odoo import api, models


class CheckinSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_checkin_summary'
    _description = 'Check-in Counter Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data['start_date']
        end_date = data['end_date']

        checkins = self.env['checkin.counter'].search([
            ('state', '=', 'invoiced'),
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
                    'total_minutes': 0,
                    'amount': 0
                }

            for line in checkin.checkin_counter_line_ids:
                summary[airline]['frequency'] += 1
                summary[airline]['total_minutes'] += line.total_minutes
                summary[airline]['amount'] += line.amount

        report_data = list(summary.values())
        report_data.sort(key=lambda x: x['airline'])

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }