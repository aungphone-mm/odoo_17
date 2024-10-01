from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    checkin_counter_id = fields.Many2one('checkin.counter', string='Checkin Counter', readonly=True)
    form_type = fields.Char('Form Type')

    def action_view_checkin_counter(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Check in Counter',
            'view_mode': 'form',
            'res_model': 'checkin.counter',
            'res_id': self.checkin_counter_id.id,
            'context': {'create': False},
        }


