from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta

class SaleSubscriptionTemplate(models.Model):
    _inherit = 'sale.order.template'

    customer_ids = fields.One2many(
        'subscription.customer',
        'subscription_template_id',
        string='Customers',
        help="Customers associated with this subscription template"
    )
    customer_count = fields.Integer(
        string='Customer Count',
        compute='_compute_customer_count',
        store=True
    )
    sale_order_ids = fields.One2many(
        'sale.order',
        'sale_order_template_id',
        string='Sale Orders',
        help="Sale orders created from this subscription template"
    )
    @api.depends('customer_ids')
    def _compute_customer_count(self):
        for template in self:
            template.customer_count = len(template.customer_ids)

    active_subscription_ids = fields.Many2many(
        'sale.order',
        compute='_compute_active_subscription_ids',
        string='Active Subscriptions',
        store=True
    )
    @api.depends('sale_order_ids', 'sale_order_ids.state')
    def _compute_active_subscription_ids(self):
        for template in self:
            template.active_subscription_ids = template._get_active_subscriptions()

    def _get_active_subscriptions(self):
        return self.sale_order_ids.filtered(lambda o: o.state == 'sale')

    # @api.model
    # def _search_sale_orders(self, operator, value):
    #     return [('state', '=', 'sale')]

    def action_create_sale_orders(self):
        wizard = self.env['create.subscription.wizard'].create({
            'template_id': self.id,
        })
        return {
            'name': 'Create Subscription Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'create.subscription.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_view_sale_order_lines(self):
        self.ensure_one()
        sale_order_lines = self.env['sale.order.line'].search([
            ('order_id.sale_order_template_id', '=', self.id)
        ])

        if not sale_order_lines:
            return {'type': 'ir.actions.act_window_close'}

        wizard = self.env['sale.order.line.wizard'].create({'template_id': self.id})
        for line in sale_order_lines:
            try:
                self.env['sale.order.line.wizard.line'].create({
                    'wizard_id': wizard.id,
                    'sale_line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                })
            except Exception as e:
                _logger.error(f"Error creating wizard line for sale order line {line.id}: {str(e)}")

        return {
            'name': 'Sale Order Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'create': False},
        }
    # def action_view_sale_order_lines(self):
    #     self.ensure_one()
    #     sale_order_lines = self.env['sale.order.line'].search([
    #         ('order_id.sale_order_template_id', '=', self.id)
    #     ])
    #     action = {
    #         'name': 'Sale Order Lines',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'sale.order.line',
    #         'view_mode': 'tree,form',
    #         'domain': [('id', 'in', sale_order_lines.ids)],
    #         'context': {'create': False},
    #     }
    #     return action

class SubscriptionCustomer(models.Model):
    _name = 'subscription.customer'
    _description = 'Subscription Customer'

    name = fields.Char(string='Name', related='partner_id.name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    subscription_template_id = fields.Many2one('sale.order.template', string='Subscription Template',
                                               required=True, ondelete='cascade')
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.phone = self.partner_id.phone


class CreateSubscriptionWizard(models.TransientModel):
    _name = 'create.subscription.wizard'
    _transient_max_count = 100
    _description = 'Create Subscription Wizard'

    template_id = fields.Many2one('sale.order.template', string='Subscription Template', required=True)
    validity_date = fields.Date(string='Validity Date', required=True, default=lambda self: fields.Date.today() + timedelta(days=30))
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    plan_id = fields.Many2one('sale.subscription.plan', string='Recurring Plan')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    end_date = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.today() + timedelta(days=30))

    def action_create_orders(self):
        created_order_ids = []
        for customer in self.template_id.customer_ids:
            order = self.env['sale.order'].create({
                'partner_id': customer.partner_id.id,
                'sale_order_template_id': self.template_id.id,
                'validity_date': self.validity_date,
                'date_order': fields.Datetime.to_datetime(self.date_order),
                'plan_id': self.plan_id.id if self.plan_id else False,
                'payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
                'end_date': fields.Datetime.to_datetime(self.end_date),
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.product_id.lst_price,
                }) for line in self.template_id.sale_order_template_line_ids]
            })
            created_order_ids.append(order.id)
        return {
            'name': 'Created Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_order_ids)],
            'target': 'current',
        }

class SaleOrderLineWizard(models.TransientModel):
    _name = 'sale.order.line.wizard'
    _transient_max_count = 100
    _description = 'Sale Order Line Wizard'

    template_id = fields.Many2one('sale.order.template', string='Subscription Template')
    line_ids = fields.One2many('sale.order.line.wizard.line', 'wizard_id', string='Sale Order Lines')

    def default_get(self, fields):
        res = super(SaleOrderLineWizard, self).default_get(fields)
        if self._context.get('active_model') == 'sale.order.line' and self._context.get('active_ids'):
            lines = self.env['sale.order.line'].browse(self._context['active_ids'])
            wizard_lines = [(0, 0, {
                'sale_line_id': line.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
            }) for line in lines]
            res['line_ids'] = wizard_lines
        return res

    def action_create_invoices(self):
        Invoice = self.env['account.move']
        SaleOrder = self.env['sale.order']
        created_invoices = Invoice
        for order in self.line_ids.mapped('sale_line_id.order_id'):
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': order.partner_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [],
                'invoice_origin': order.name,  # Add the sale order reference
            }
            for wizard_line in self.line_ids.filtered(lambda l: l.sale_line_id.order_id == order):
                line_vals = {
                    'product_id': wizard_line.product_id.id,
                    'name': wizard_line.name,
                    'quantity': wizard_line.product_uom_qty,
                    'price_unit': wizard_line.price_unit,
                    'tax_ids': [(6, 0, wizard_line.sale_line_id.tax_id.ids)],
                    'product_uom_id': wizard_line.sale_line_id.product_uom.id,
                    'sale_line_ids': [(4, wizard_line.sale_line_id.id)],  # Link to the sale order line
                }
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
            try:
                invoice = Invoice.create(invoice_vals)
                created_invoices += invoice
                # Update the sale order
                order.write({
                    'invoice_ids': [(4, invoice.id)],
                    'invoice_status': 'invoiced',
                })
                # Change the sale order state to 'sale' if it's in 'draft' or 'sent' state
                if order.state in ['draft', 'sent']:
                    order.action_confirm()
            except Exception as e:
                raise UserError(f"Error creating invoice for order {order.name}: {str(e)}")
        if created_invoices:
            return {
                'name': 'Created Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_invoices.ids)],
                'target': 'current',
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

class SaleOrderLineWizardLine(models.TransientModel):
    _name = 'sale.order.line.wizard.line'
    _transient_max_count = 100
    _description = 'Sale Order Line Wizard Line'

    wizard_id = fields.Many2one('sale.order.line.wizard', string='Wizard')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    partner_id = fields.Many2one(related='sale_line_id.order_id.partner_id', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Description')
    product_uom_qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')