from odoo import models, fields, api


class SubscriptionType(models.Model):

    _name = 'sale.subscription.type'
    _description = 'Subscription Type'
    name = fields.Char('Subscription Field')


class SaleOrder(models.Model):

    _inherit = 'sale.order'
    subscription_type_id = fields.Many2one('sale.subscription.type', 'Type')
    product_id = fields.Char(string='Products', compute='_compute_product_names')

    @api.depends('order_line.product_id.name')
    def _compute_product_names(self):
        for order in self:
            product_names = ', '.join(order.order_line.mapped('product_id.name'))
            order.product_id = product_names


