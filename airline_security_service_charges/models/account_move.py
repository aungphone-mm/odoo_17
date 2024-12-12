from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    airline_security_service_id = fields.Many2one('airline.security.service', string='Security Service', readonly=True)
    form_type = fields.Char('Form Type')

    def action_print_security_invoice(self):
        return self.env.ref('airline_security_service_charges.action_security_service_report').report_action(self)

    def action_view_security_service(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Airline Security Service',
            'view_mode': 'form',
            'res_model': 'airline.security.service',
            'res_id': self.airline_security_service_id.id,
            'context': {'create': False},
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    airline_security_service_line_id = fields.Many2one('airline.security.service.line', string='Security Service Line')

    def _get_time_from_rate_security(self):
        self.ensure_one()
        if not self.price_unit:
            return False

        rate_line = self.env['airline.security.rate.line'].search([
            ('unit_price', '=', self.price_unit)
        ], limit=1)

        return rate_line.time if rate_line else False