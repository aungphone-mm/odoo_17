from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_boarding_bridge_charges_id = fields.Many2one('passenger.boarding.bridge.charges', string='Boarding Bridge Service', readonly=True)
    form_type = fields.Char('Form Type')

    def action_view_bridge_service(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Passenger Boarding Bridge Charges',
            'view_mode': 'form',
            'res_model': 'passenger.boarding.bridge.charges',
            'res_id': self.passenger_boarding_bridge_charges_id.id,
            'context': {'create': False},
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_boarding_bridge_charges_line_id = fields.Many2one('passenger.boarding.bridge.charges.line', string='Bridge Service Line')

    def _get_time_from_rate(self):
        self.ensure_one()
        if not self.price_unit:
            return False

        rate_line = self.env['passenger.boarding.bridge.charges.rate.line'].search([
            ('unit_price', '=', self.price_unit)
        ], limit=1)

        return rate_line.time if rate_line else False
