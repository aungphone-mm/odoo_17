from odoo import api, models

class PassengerSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_passenger_summary'
    _description = 'Passenger Summary Report'

    def _get_report_values(self, docids, data=None):
        start_date = data['start_date']
        end_date = data['end_date']

        invoices = self.env['passenger.service'].search([
            # ('state', '=', 'invoiced'),
            ('start_time', '>=', start_date),
            ('start_time', '<=', end_date),
        ])

        summary = {}
        non_schedule_summary = {}  # New dictionary for non-schedule entries

        for invoice in invoices:
            if invoice.non_schedule:
                # Handle non-schedule flights
                airline = invoice.airline_id.name
                if airline not in non_schedule_summary:
                    non_schedule_summary[airline] = {
                        'airline': f"Non Schedule - {airline}",
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

                for line in invoice.passenger_service_line_ids:
                    non_schedule_summary[airline]['frequency'] += 1
                    non_schedule_summary[airline]['total_pax'] += line.total_pax
                    non_schedule_summary[airline]['inf'] += line.inf
                    non_schedule_summary[airline]['tax_free'] += line.tax_free
                    non_schedule_summary[airline]['ntl'] += line.ntl
                    non_schedule_summary[airline]['inad'] += line.inad
                    non_schedule_summary[airline]['depor'] += line.depor
                    non_schedule_summary[airline]['transit'] += line.transit
                    non_schedule_summary[airline]['invoice_pax'] += line.invoice_pax
            else:
                # Regular flights (existing logic)
                airline = invoice.airline_id.name
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

                for line in invoice.passenger_service_line_ids:
                    summary[airline]['frequency'] += 1
                    summary[airline]['total_pax'] += line.total_pax
                    summary[airline]['inf'] += line.inf
                    summary[airline]['tax_free'] += line.tax_free
                    summary[airline]['ntl'] += line.ntl
                    summary[airline]['inad'] += line.inad
                    summary[airline]['depor'] += line.depor
                    summary[airline]['transit'] += line.transit
                    summary[airline]['invoice_pax'] += line.invoice_pax

        # Combine regular and non-schedule entries
        report_data = list(summary.values()) + list(non_schedule_summary.values())

        return {
            'data': data,
            'docs': report_data,
            'get_report_data': lambda: report_data,
            'get_total': lambda field: sum(line[field] for line in report_data)
        }