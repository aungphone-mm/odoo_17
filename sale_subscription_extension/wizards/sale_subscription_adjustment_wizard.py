from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class SubscriptionInvoiceWizard(models.TransientModel):

    _name = 'subscription.invoice.wizard'
    _description = 'Subscription Invoice Wizard'

    subscription_type_id = fields.Many2one('sale.subscription.type', string='Subscription Type')
    subscription_ids = fields.Many2many('sale.order', string='Subscriptions')
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month', required=True)

    year = fields.Selection(
        selection='_get_years',
        string='Year',
        required=True
    )

    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        if self.subscription_type_id:
            matching_subscriptions = self.env['sale.order'].search([
                ('subscription_type_id', '=', self.subscription_type_id.id)
            ])
            self.subscription_ids = [(6, 0, matching_subscriptions.ids)]
        else:
            self.subscription_ids = [(6, 0, [])]

    @api.model
    def _get_years(self):
        # Generate a list of years from 2020 to current year + 1
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(2024, current_year + 1)]

    def action_confirm(self):
        _logger.info('Selected Month: %s, Year: %s', self.month, self.year, self.subscription_type_id.id)
        return {
            'type': 'ir.actions.act_window_close'
        }

    #TODO: Filter the subscriptions based on in progress state and expiration date
    def action_create_invoices(self):
        subscriptions = self.env['sale.order'].search([('subscription_type_id', '=', self.subscription_type_id.id)])
        res = {
            'name': 'Subscriptions',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'sale.order',
            'domain': [('id', 'in', subscriptions.ids)],
            'target': 'new',
        }
        return res

