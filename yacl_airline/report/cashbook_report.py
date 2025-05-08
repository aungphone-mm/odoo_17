from odoo import models, api
from collections import defaultdict


class CashbookReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_cashbook'
    _description = 'Cashbook Report'

    def _group_by_main_account(self, cashbooks):
        """Group cashbook entries by main account"""
        main_account_data = defaultdict(lambda: {
            'name': '',
            'count': 0,
            'total_amount': 0,
            'entries': []
        })

        for cashbook in cashbooks:
            main_account = cashbook.main_account_id
            main_account_name = main_account.name if main_account else 'Undefined'

            # Add entry to the group
            main_account_data[main_account_name]['name'] = main_account_name
            main_account_data[main_account_name]['count'] += 1
            main_account_data[main_account_name]['total_amount'] += cashbook.total_amount
            main_account_data[main_account_name]['entries'].append(cashbook)

        return dict(main_account_data)

    def _group_by_type(self, cashbooks):
        """Group cashbook entries by type (payment/receive)"""
        type_data = {
            'payment': {
                'count': 0,
                'total_amount': 0,
            },
            'receive': {
                'count': 0,
                'total_amount': 0,
            }
        }

        for cashbook in cashbooks:
            cashbook_type = cashbook.type  # 'payment' or 'receive'

            # Increment counters for this type
            type_data[cashbook_type]['count'] += 1
            type_data[cashbook_type]['total_amount'] += cashbook.total_amount

        return type_data

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            return {}

        date_from = data['date_from']
        date_to = data['date_to']

        # Get cashbook entries for the selected date range with state 'confirm' or 'done'
        # Filter to only include payment type (not receive)
        cashbooks = self.env['account.cashbook'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', 'in', ['confirm', 'done']),
            ('type', '=', 'payment')
        ], order='date, name')

        # Group data by main account
        grouped_by_account = self._group_by_main_account(cashbooks)

        # Group data by type
        grouped_by_type = self._group_by_type(cashbooks)

        # Calculate grand totals
        grand_totals = {
            'total_count': sum(data['count'] for data in grouped_by_account.values()),
            'total_amount': sum(data['total_amount'] for data in grouped_by_account.values()),
            'payment_total': grouped_by_type['payment']['total_amount'],
            'receive_total': grouped_by_type['receive']['total_amount']
        }

        return {
            'doc_ids': docids,
            'doc_model': 'cashbook.report.wizard',
            'data': data,
            'cashbooks': cashbooks,
            'accounts': grouped_by_account,
            'types': grouped_by_type,
            'grand_totals': grand_totals,
        }