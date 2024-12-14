from odoo import models, api, fields


class AirlineChargesReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_airline_charges'
    _description = 'Airline Charges Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['date_from']
        date_to = data['date_to']

        # Get USD and MMK currencies
        usd_currency = self.env.ref('base.USD')
        mmk_currency = self.env.ref('base.MMK')

        # Get current MMK to USD exchange rate
        mmk_rate = mmk_currency._get_rates(self.env.company, fields.Date.today())[mmk_currency.id]
        usd_rate = usd_currency._get_rates(self.env.company, fields.Date.today())[usd_currency.id]
        mmk_to_usd_rate = mmk_rate / usd_rate if usd_rate else 0

        # Security Service amounts
        security_services = self.env['airline.security.service'].search([
            ('for_date', '>=', date_from),
            ('for_date', '<=', date_to),
            ('state', '=', 'invoiced')
        ])
        security_usd = sum(security_services.filtered(
            lambda x: x.security_rate_id.currency_id == usd_currency
        ).mapped('invoice_id.amount_total'))
        security_mmk = sum(security_services.filtered(
            lambda x: x.security_rate_id.currency_id == mmk_currency
        ).mapped('invoice_id.amount_total'))
        security_total_usd = security_usd + (security_mmk / mmk_to_usd_rate)

        # Check-in Counter amounts
        checkin_services = self.env['checkin.counter'].search([
            ('for_date', '>=', date_from),
            ('for_date', '<=', date_to),
            ('state', '=', 'invoiced')
        ])
        checkin_usd = sum(checkin_services.filtered(
            lambda x: x.checkin_counter_rate_id.currency_id == usd_currency).mapped('invoice_id.amount_total'))
        checkin_mmk = sum(checkin_services.filtered(
            lambda x: x.checkin_counter_rate_id.currency_id == mmk_currency).mapped('invoice_id.amount_total'))
        checkin_total_usd = checkin_usd + (checkin_mmk / mmk_to_usd_rate)

        # Boarding Bridge amounts
        bridge_services = self.env['passenger.boarding.bridge.charges'].search([
            ('for_date', '>=', date_from),
            ('for_date', '<=', date_to),
            ('state', '=', 'invoiced')
        ])
        bridge_usd = sum(bridge_services.filtered(
            lambda x: x.bridge_rate_id.currency_id == usd_currency).mapped('invoice_id.amount_total'))
        bridge_mmk = sum(bridge_services.filtered(
            lambda x: x.bridge_rate_id.currency_id == mmk_currency).mapped('invoice_id.amount_total'))
        bridge_total_usd = bridge_usd + (bridge_mmk / mmk_to_usd_rate)

        return {
            'date_from': date_from,
            'date_to': date_to,
            'security_usd': security_usd,
            'security_mmk': security_mmk,
            'security_total_usd': security_total_usd,
            'checkin_usd': checkin_usd,
            'checkin_mmk': checkin_mmk,
            'checkin_total_usd': checkin_total_usd,
            'bridge_usd': bridge_usd,
            'bridge_mmk': bridge_mmk,
            'bridge_total_usd': bridge_total_usd,
            'total_usd': security_usd + checkin_usd + bridge_usd,
            'total_mmk': security_mmk + checkin_mmk + bridge_mmk,
            'grand_total_usd': security_total_usd + checkin_total_usd + bridge_total_usd,
        }