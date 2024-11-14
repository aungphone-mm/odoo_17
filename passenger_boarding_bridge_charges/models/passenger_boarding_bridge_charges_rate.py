from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PassengerBoardingBridgeChargesRate(models.Model):
    _name = 'passenger.boarding.bridge.charges.rate'
    _description = 'bridge Rate'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Rate', tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
                                 required=True)
    bridge_rate_line_ids = fields.One2many(comodel_name='passenger.boarding.bridge.charges.rate.line', inverse_name='rate_id', string='Rate Line',
                                    required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    active = fields.Boolean(string='Active', default=True)
    seat_capacity = fields.Integer(string='Seat Capacity', required=True, tracking=True)

    @api.constrains('seat_capacity')
    def _check_unique_seat_capacity(self):
        for record in self:
            existing = self.search([
                ('id', '!=', record.id),
                ('seat_capacity', '=', record.seat_capacity),
                ('active', '=', True)
            ])
            if existing:
                raise ValidationError(
                    f"A rate already exists for {record.seat_capacity} seats: {existing[0].name}"
                )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Rate name must be unique!')
    ]