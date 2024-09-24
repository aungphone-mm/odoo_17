from odoo import fields, models, api, _

class AirlineSecurityRate(models.Model):
    _name = 'airline.security.rate'
    _description = 'Security Rate'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Rate', tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
                                 required=True)
    security_rate_line_ids = fields.One2many(comodel_name='airline.security.rate.line', inverse_name='rate_id', string='Rate Line',
                                    required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    active = fields.Boolean(string='Active', default=True)