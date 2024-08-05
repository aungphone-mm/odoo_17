from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from lxml import etree
import html

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
    #
    # active_subscription_ids = fields.Many2many(
    #     'sale.order',
    #     compute='_compute_active_subscription_ids',
    #     string='Active Subscriptions',
    #     store=True
    # )
    # @api.depends('sale_order_ids', 'sale_order_ids.state')
    # def _compute_active_subscription_ids(self):
    #     for template in self:
    #         template.active_subscription_ids = template._get_active_subscriptions()
    #
    # def _get_active_subscriptions(self):
    #     return self.sale_order_ids.filtered(lambda o: o.state == 'sale')

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
        return {
            'name': 'Sale Order Template Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.template',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'view_id': self.env.ref('subscriptions_extension.view_sale_order_template_wizard_form').id,
            'context': {
                'default_sale_order_template_id': self.id,
                'default_sale_order_template_line_ids': [(6, 0, self.sale_order_template_line_ids.ids)],
            }
        }

    def action_create_invoices(self):
        self.ensure_one()
        Invoice = self.env['account.move']
        created_invoices = Invoice

        # Use the edited HTML if available, otherwise use the original
        html_content = self.env.context.get('edited_html', self.sale_order_template_html)

        # Parse the HTML content
        tree = etree.fromstring(html_content, etree.HTMLParser())
        rows = tree.xpath('//tr')[2:]  # Skip header rows

        for row in rows:
            cells = row.xpath('.//td | .//th')
            if len(cells) < 2:
                continue

            customer_name = cells[0].text.strip() if cells[0].text else ''
            customer = self.env['res.partner'].search([('name', '=', customer_name)], limit=1)

            if not customer:
                continue

            invoice_lines = []
            for i, cell in enumerate(cells[1:], start=1):
                quantity = float(cell.text.strip() if cell.text else '0')
                if quantity > 0:
                    product = self.sale_order_template_line_ids[i - 1].product_id
                    invoice_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': product.name,
                        'quantity': quantity,
                        'price_unit': product.lst_price,
                    }))

            if invoice_lines:
                invoice_vals = {
                    'partner_id': customer.id,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': invoice_lines,
                }
                invoice = Invoice.create(invoice_vals)
                created_invoices += invoice

        if created_invoices:
            action = self.env.ref('account.action_move_out_invoice_type').read()[0]
            action['domain'] = [('id', 'in', created_invoices.ids)]
            return action
        return {'type': 'ir.actions.act_window_close'}

    def action_edit_html(self):
        self.ensure_one()
        return {
            'name': 'Edit Units',
            'type': 'ir.actions.act_window',
            'res_model': 'edit.html.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
            'flags': {'form': {'action_buttons': True}},
            'width': '80%',
            'height': '80%',
        }

    sale_order_template_html = fields.Html(string='Template Line Information',
                                           compute='_compute_sale_order_template_html')
    show_as_columns = fields.Boolean(string='Show as Columns', default=True)


    @api.depends('sale_order_template_line_ids', 'sale_order_template_line_ids.product_uom_qty', 'sale_order_ids',
                     'sale_order_ids.order_line.product_uom_qty', 'show_as_columns')
    def _compute_sale_order_template_html(self):
        for record in self:
            if record.show_as_columns:
                formatted_html = record._get_column_view_html()
            else:
                formatted_html = record._get_row_view_html()
            record.sale_order_template_html = formatted_html

    def _get_column_view_html(self):
        self.ensure_one()
        template_lines = self.sale_order_template_line_ids.sorted(key=lambda l: l.sequence)
        active_subscriptions = self.sale_order_ids.filtered(lambda o: o.state == 'sale')

        html = """
        <table class="table table-sm table-bordered table-hover">
            <thead>
                <tr>
                    <th class="text-center align-middle" rowspan="2">Info</th>
        """
        for line in template_lines:
            html += f'<th class="text-center">{line.product_id.name}</th>'
        html += """
                </tr>
                <tr>
        """
        for line in template_lines:
            html += f'<th class="text-center">{line.product_id.uom_id.name}</th>'
        html += """
                </tr>
            </thead>
            <tbody>
                <tr>
                    <th class="text-left">Template Quantity</th>
        """
        for line in template_lines:
            html += f'<td class="text-right">{line.product_uom_qty}</td>'
        html += """
                </tr>
        """

        for subscription in active_subscriptions:
            html += f"""
                <tr>
                    <th class="text-left">{subscription.partner_id.name}</th>
            """
            for template_line in template_lines:
                subscription_line = subscription.order_line.filtered(lambda l: l.product_id == template_line.product_id)
                quantity = subscription_line.product_uom_qty if subscription_line else 0
                html += f'<td class="text-right">{quantity}</td>'
            html += """
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def _get_row_view_html(self):
        self.ensure_one()
        template_lines = self.sale_order_template_line_ids.sorted(key=lambda l: l.sequence)
        html = """
           <table class="table table-sm table-hover">
               <thead>
                   <tr>
                       <th class="text-left">Product</th>
                       <th class="text-right">Quantity</th>
                   </tr>
               </thead>
               <tbody>
           """
        for line in template_lines:
            html += f"""
                   <tr>
                       <td class="text-left">{line.product_id.name}</td>
                       <td class="text-right">{line.product_uom_qty}</td>
                   </tr>
               """
        html += """
               </tbody>
           </table>
           """
        return html

    # def action_recompute_html(self):
    #     self._compute_sale_order_template_html()
class EditHTMLWizard(models.TransientModel):
    _name = 'edit.html.wizard'
    _description = 'Edit HTML Wizard'

    template_id = fields.Many2one('sale.order.template', string='Subscription Template', required=True)
    html_content = fields.Html(string='HTML Content', sanitize=False)

    @api.model
    def default_get(self, fields):
        res = super(EditHTMLWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
            template = self.env['sale.order.template'].browse(self.env.context['active_id'])
            res.update({
                'template_id': template.id,
                'html_content': template.sale_order_template_html,
            })
        return res

    def action_confirm(self):
        self.ensure_one()
        self.template_id.write({
            'sale_order_template_html': self.html_content,
        })
        return self.template_id.with_context(edited_html=self.html_content).action_create_invoices()


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
    _description = 'Create Subscription Wizard'

    template_id = fields.Many2one('sale.order.template', string='Subscription Template', required=True)
    validity_date = fields.Date(string='Validity Date', required=True, default=lambda self: fields.Date.today() + timedelta(days=30))
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    plan_id = fields.Many2one('sale.subscription.plan',related='template_id.plan_id', string='Recurring Plan')
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
