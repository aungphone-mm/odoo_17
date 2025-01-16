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

        # Calculate exchange rates
        mmk_to_usd_rate = usd_rate / mmk_rate if mmk_rate else 0
        usd_to_mmk_rate = mmk_rate / usd_rate if usd_rate else 0

        # 1. Passenger Service Charges
        passenger_services = self.env['passenger.service.line'].search([
            ('start_time', '>=', date_from),
            ('start_time', '<=', date_to),
        ])

        # Calculate USD amounts for passenger services
        passenger_usd = sum(
            line.invoice_pax * line.passenger_service_rate_id.pax_price
            for service in passenger_services.filtered(
                lambda x: x.passenger_service_rate_id.currency_id == usd_currency)
            for line in service
        )

        # Calculate MMK amounts for passenger services
        passenger_mmk = sum(
            line.invoice_pax * line.passenger_service_rate_id.pax_price
            for service in passenger_services.filtered(
                lambda x: x.passenger_service_rate_id.currency_id == mmk_currency)
            for line in service
        )

        # Calculate totals with currency conversion
        passenger_total_usd = passenger_usd + (passenger_mmk / mmk_to_usd_rate if mmk_to_usd_rate else 0)
        passenger_total_mmk = passenger_mmk + (passenger_usd * usd_to_mmk_rate if usd_to_mmk_rate else 0)

        # 2. Security Service Charges
        security_services = self.env['airline.security.service.line'].search([
            ('start_time', '>=', date_from),
            ('end_time', '<=', date_to),
        ])

        # Calculate amounts for security services
        security_usd = sum(
            line.amount
            for line in security_services
            if line.security_rate_id.currency_id == usd_currency
        )

        security_mmk = sum(
            line.amount
            for line in security_services
            if line.security_rate_id.currency_id == mmk_currency
        )

        # Calculate totals with currency conversion
        security_total_usd = security_usd + (security_mmk / mmk_to_usd_rate if mmk_to_usd_rate else 0)
        security_total_mmk = security_mmk + (security_usd * usd_to_mmk_rate if usd_to_mmk_rate else 0)

        # 3. Check-in Counter Charges
        checkin_services = self.env['checkin.counter.line'].search([
            ('start_time', '>=', date_from),
            ('end_time', '<=', date_to),
        ])

        # Calculate amounts for check-in services
        checkin_usd = sum(
            service.amount
            for service in checkin_services.filtered(
                lambda x: x.checkin_counter_rate_id.currency_id == usd_currency)
        )

        checkin_mmk = sum(
            service.amount
            for service in checkin_services.filtered(
                lambda x: x.checkin_counter_rate_id.currency_id == mmk_currency)
        )

        # Calculate totals with currency conversion
        checkin_total_usd = checkin_usd + (checkin_mmk / mmk_to_usd_rate if mmk_to_usd_rate else 0)
        checkin_total_mmk = checkin_mmk + (checkin_usd * usd_to_mmk_rate if usd_to_mmk_rate else 0)

        # 4. Boarding Bridge Charges
        bridge_services = self.env['passenger.boarding.bridge.charges.line'].search([
            ('start_time', '>=', date_from),
            ('end_time', '<=', date_to),
        ])

        # Calculate amounts for bridge services
        bridge_usd = sum(
            service.amount
            for service in bridge_services.filtered(
                lambda x: x.bridge_rate_id.currency_id == usd_currency)
        )

        bridge_mmk = sum(
            service.amount
            for service in bridge_services.filtered(
                lambda x: x.bridge_rate_id.currency_id == mmk_currency)
        )

        # Calculate totals with currency conversion
        bridge_total_usd = bridge_usd + (bridge_mmk / mmk_to_usd_rate if mmk_to_usd_rate else 0)
        bridge_total_mmk = bridge_mmk + (bridge_usd * usd_to_mmk_rate if usd_to_mmk_rate else 0)

        # Calculate overall totals
        total_usd = security_usd + checkin_usd + bridge_usd + passenger_usd
        total_mmk = security_mmk + checkin_mmk + bridge_mmk + passenger_mmk
        grand_total_usd = security_total_usd + checkin_total_usd + bridge_total_usd + passenger_total_usd
        grand_total_mmk = security_total_mmk + checkin_total_mmk + bridge_total_mmk + passenger_total_mmk

        # Return all calculated values
        return {
            'date_from': date_from,
            'date_to': date_to,
            # Security service values
            'security_usd': security_usd,
            'security_mmk': security_mmk,
            'security_total_usd': security_total_usd,
            'security_total_mmk': security_total_mmk,
            # Check-in counter values
            'checkin_usd': checkin_usd,
            'checkin_mmk': checkin_mmk,
            'checkin_total_usd': checkin_total_usd,
            'checkin_total_mmk': checkin_total_mmk,
            # Bridge service values
            'bridge_usd': bridge_usd,
            'bridge_mmk': bridge_mmk,
            'bridge_total_usd': bridge_total_usd,
            'bridge_total_mmk': bridge_total_mmk,
            # Passenger service values
            'passenger_usd': passenger_usd,
            'passenger_mmk': passenger_mmk,
            'passenger_total_usd': passenger_total_usd,
            'passenger_total_mmk': passenger_total_mmk,
            # Grand totals
            'total_usd': total_usd,
            'total_mmk': total_mmk,
            'grand_total_usd': grand_total_usd,
            'grand_total_mmk': grand_total_mmk,
        }