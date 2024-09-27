from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    airline_security_service_id = fields.Many2one('airline.security.service', string='Security Service', readonly=True)
    form_type = fields.Char('Form Type')

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


