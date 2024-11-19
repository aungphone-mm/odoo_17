from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_service_id = fields.Many2one('passenger.service', string='Passenger Service', readonly=True)
    form_type = fields.Char('Form Type')

    def action_view_passenger_service(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Passenger Service',
            'view_mode': 'form',
            'res_model': 'passenger.service',
            'res_id': self.passenger_service_id.id,
            'context': {'create': False},
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_service_line_id = fields.Many2one('passenger.service.line', string='Passenger Service Line')



