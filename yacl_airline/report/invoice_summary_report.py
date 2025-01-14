from odoo import api, models

class InvoiceSummaryReport(models.AbstractModel):
    _name = 'report.yacl_airline.report_invoice_summary'
    _description = 'Invoice Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            return {}

        wizard_model = self.env['report.selection.wizard']
        wizard = wizard_model.browse(docids[0]) if docids else None

        # If data not passed directly, get from wizard
        if not data and wizard:
            data = {
                'airline_id': wizard.airline_id.id,
                'module': wizard.module,
                'start_date': wizard.start_date,
                'end_date': wizard.end_date
            }

        airline = self.env['airline'].browse(data['airline_id'])

        return {
            'doc_ids': docids,
            'doc_model': 'report.selection.wizard',
            'docs': wizard,
            'airline': airline,
            'module': data['module'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'get_module_name': self._get_module_name,
            'get_invoice_data': lambda: self._get_invoice_data(data),
            'get_total_amount': lambda: self._get_total_amount(data),
            'get_currency': lambda: self.env.company.currency_id,
        }

    def _get_module_name(self, module_code):
        module_names = {
            'security': 'Security Service',
            'bridge': 'Boarding Bridge',
            'landing': 'Aircraft Landing',
            'checkin': 'Check-in Counter',
            'passenger': 'Passenger Service'
        }
        return module_names.get(module_code, '')

    def _get_invoice_data(self, data):
        domain = [
            # ('move_type', '=', 'out_invoice'),
            # ('state', '=', 'posted'),
            ('invoice_date', '>=', data['start_date']),
            ('invoice_date', '<=', data['end_date'])
        ]

        airline = self.env['airline'].browse(data['airline_id'])
        if airline.partner_id:
            domain.append(('partner_id', '=', airline.partner_id.id))

        # Add module-specific domain
        module_field_map = {
            'security': 'airline_security_service_id',
            'bridge': 'passenger_boarding_bridge_charges_id',
            'checkin': 'checkin_counter_id',
            'landing': 'passenger_landing_id',
            'passenger': 'passenger_service_id'
        }

        if data['module'] in module_field_map:
            domain.append((module_field_map[data['module']], '!=', False))

        return self.env['account.move'].search(domain, order='invoice_date')

    def _get_total_amount(self, data):
        invoices = self._get_invoice_data(data)
        return sum(invoices.mapped('amount_total_signed'))