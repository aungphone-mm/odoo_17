from odoo import fields, models, _

class PassengerServiceRate(models.Model):
    _name = 'passenger.service.rate'
    _description = 'PassengerService Rate'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Rate', tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
                                 required=True)
    passenger_service_rate_line_ids = fields.One2many(comodel_name='passenger.service.rate.line', inverse_name='rate_id', string='Rate Line',
                                    required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    active = fields.Boolean(string='Active', default=True)