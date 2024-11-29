from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_landing_id = fields.Many2one('passenger.landing', string='Passenger Landing', readonly=True)
    form_type = fields.Char('Form Type')

    def action_view_passenger_landing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Aircraft Landing',
            'view_mode': 'form',
            'res_model': 'passenger.landing',
            'res_id': self.passenger_landing_id.id,
            'context': {'create': False},
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_landing_line_id = fields.Many2one('passenger.landing.line', string='Passenger Landing Line')



