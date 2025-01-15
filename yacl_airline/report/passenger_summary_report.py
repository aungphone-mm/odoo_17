from odoo import api, models
from datetime import datetime, timedelta

class PassengerSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_passenger_summary'
    _description = 'Passenger Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        flight_type = data['flight_type']
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)

        domain = [
            # ('state', '=', 'invoiced'),
            ('start_time', '>=', adjusted_start_date),
            ('start_time', '<=', adjusted_end_date),
        ]

        if flight_type != 'all':
            domain.append(('passenger_service_id.type', '=', flight_type))

        invoices = self.env['passenger.service.line'].search(domain)

        summary = {}
        for invoice in invoices:
            airline = invoice.passenger_service_id.airline_id.name
            if airline not in summary:
                summary[airline] = {
                    'airline': airline,
                    'frequency': 0,
                    'total_pax': 0,
                    'inf': 0,
                    'tax_free': 0,
                    'ntl': 0,
                    'inad': 0,
                    'depor': 0,
                    'transit': 0,
                    'invoice_pax': 0,
                    'remark': ''
                }

            # for line in invoice.passenger_service_line_ids:
            summary[airline]['frequency'] += 1
            summary[airline]['total_pax'] += invoice.total_pax
            summary[airline]['inf'] += invoice.inf
            summary[airline]['tax_free'] += invoice.tax_free
            summary[airline]['ntl'] += invoice.ntl
            summary[airline]['inad'] += invoice.inad
            summary[airline]['depor'] += invoice.depor
            summary[airline]['transit'] += invoice.transit
            summary[airline]['invoice_pax'] += invoice.invoice_pax

        report_data = list(summary.values())

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data),
            'flight_type': flight_type
        }