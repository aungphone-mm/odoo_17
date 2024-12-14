from odoo import api, models


class PassengerSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_passenger_summary'
    _description = 'Passenger Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data['start_date']
        end_date = data['end_date']

        invoices = self.env['account.move'].search([
            ('form_type', '=', 'PassengerService'),
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('state', '=', 'posted'),
        ])

        summary = {}
        for invoice in invoices:
            airline = invoice.partner_id.name
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

            for line in invoice.passenger_service_id.passenger_service_line_ids:
                summary[airline]['frequency'] += 1
                summary[airline]['total_pax'] += line.total_pax
                summary[airline]['inf'] += line.inf
                summary[airline]['tax_free'] += line.tax_free
                summary[airline]['ntl'] += line.ntl
                summary[airline]['inad'] += line.inad
                summary[airline]['depor'] += line.depor
                summary[airline]['transit'] += line.transit
                summary[airline]['invoice_pax'] += line.invoice_pax

        report_data = list(summary.values())

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }