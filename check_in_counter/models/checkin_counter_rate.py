from odoo import fields, models, _

class CheckinCounterRate(models.Model):
    _name = 'checkin.counter.rate'
    _description = 'Checkin Rate'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Rate', tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
                                 required=True)
    checkin_counter_rate_line_ids = fields.One2many(comodel_name='checkin.counter.rate.line', inverse_name='rate_id', string='Rate Line',
                                    required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    active = fields.Boolean(string='Active', default=True)