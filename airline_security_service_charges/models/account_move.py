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
        """Get time value based on total service duration in minutes"""
        self.ensure_one()
        if not self.airline_security_service_line_id:
            return False
        # Get total minutes from the service line
        total_minutes = self.airline_security_service_line_id.total_minutes
        # Find matching rate line based on duration range
        rate_line = self.env['airline.security.rate.line'].search([
            ('rate_id', '=', self.airline_security_service_line_id.security_rate_id.id),
            ('from_unit', '<=', total_minutes),
            ('to_unit', '>=', total_minutes)
        ], limit=1)
        if rate_line:
            return str(rate_line.time)

        return False