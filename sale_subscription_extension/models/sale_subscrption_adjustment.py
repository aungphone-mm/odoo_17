from odoo import models, fields


class SubscriptionType(models.Model):

    _name = 'sale.subscription.type'
    _description = 'Subscription Type'

    name = fields.Char('Subscription Field')


class SaleOrder(models.Model):

        _inherit = 'sale.order'

        subscription_type_id = fields.Many2one('sale.subscription.type', 'Type')