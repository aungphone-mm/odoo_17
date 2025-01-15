from odoo import models, api
from collections import defaultdict
from datetime import datetime, timedelta

class BoardingBridgeReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_security_service'
    _description = 'Security Service Report'

    def _group_by_airline(self, security_lines):
        airline_data = defaultdict(lambda: {
            'flight_freq': 0,
            'total_hours': 0,
            'total_amount': 0,
            'total_tax': 0
        })

        for line in security_lines:
            airline_name = line.airline_security_service_id.airline_id.name

            # Simply increment frequency counter
            airline_data[airline_name]['flight_freq'] += 1
            airline_data[airline_name]['total_hours'] += line.total_minutes / 60
            airline_data[airline_name]['total_amount'] += line.amount
            airline_data[airline_name]['total_tax'] += line.amount * 0.05  # 5% tax

        return dict(airline_data)

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            return {}
        start_date = datetime.strptime(data['date_from'], '%Y-%m-%d')
        end_date = datetime.strptime(data['date_to'], '%Y-%m-%d')
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)
        # Get boarding bridge lines within date range
        security_lines = self.env['airline.security.service.line'].search([
            ('start_time', '>=', adjusted_start_date),
            ('end_time', '<=', adjusted_end_date)
        ], order='airline_security_service_id, start_time')

        # Group data by airline
        grouped_data = self._group_by_airline(security_lines)

        # Calculate grand totals
        grand_totals = {
            'total_freq': sum(data['flight_freq'] for data in grouped_data.values()),
            'total_hours': sum(data['total_hours'] for data in grouped_data.values()),
            'total_amount': sum(data['total_amount'] for data in grouped_data.values()),
            'total_tax': sum(data['total_tax'] for data in grouped_data.values())
        }

        return {
            'doc_ids': docids,
            'doc_model': 'security.service.report.wizard',
            'data': data,
            'airlines': grouped_data,
            'grand_totals': grand_totals,
        }