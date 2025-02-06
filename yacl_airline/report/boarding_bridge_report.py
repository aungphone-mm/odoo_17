from odoo import models, api
from collections import defaultdict
from datetime import datetime, timedelta

class BoardingBridgeReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_boarding_bridge'
    _description = 'Boarding Bridge Report'

    def _group_by_airline(self, bridge_lines):
        airline_data = defaultdict(lambda: {
            'flight_freq': 0,
            'total_hours': 0,
            'total_amount': 0,
            'total_tax': 0
        })

        for line in bridge_lines:
            airline_name = line.passenger_boarding_bridge_charges_id.airline_id.name

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
        end_date = end_date.replace(hour=23, minute=59, second=59)
        adjusted_start_date = start_date - timedelta(hours=6, minutes=30)
        adjusted_end_date = end_date - timedelta(hours=6, minutes=30)
        # Get boarding bridge lines within date range
        bridge_lines = self.env['passenger.boarding.bridge.charges.line'].search([
            ('start_time', '>=', adjusted_start_date),
            ('end_time', '<=', adjusted_end_date)
        ], order='passenger_boarding_bridge_charges_id, start_time')

        # Group data by airline
        grouped_data = self._group_by_airline(bridge_lines)

        # Calculate grand totals
        grand_totals = {
            'total_freq': sum(data['flight_freq'] for data in grouped_data.values()),
            'total_hours': sum(data['total_hours'] for data in grouped_data.values()),
            'total_amount': sum(data['total_amount'] for data in grouped_data.values()),
            'total_tax': sum(data['total_tax'] for data in grouped_data.values())
        }

        return {
            'doc_ids': docids,
            'doc_model': 'boarding.bridge.report.wizard',
            'data': data,
            'airlines': grouped_data,
            'grand_totals': grand_totals,
        }