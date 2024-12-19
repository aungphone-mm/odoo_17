from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

class PassengerService(models.Model):
    _name = 'passenger.service'
    _description = 'Passenger Service'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], default='international', string='Type', tracking=True)
    airline_id = fields.Many2one('airline',string='Airline')
    airline_user_id = fields.Many2one('res.partner', string='Attention:', tracking=True)
    start_time = fields.Datetime(string='Start Date & Time', default=fields.Datetime.now, tracking=True)
    end_time = fields.Datetime(string='End Date & Time', tracking=True)
    passenger_service_line_ids = fields.One2many('passenger.service.line', 'passenger_service_id',
                                                      string='Passenger Service Details')
    currency_id = fields.Many2one('res.currency', string='Currency', related='passenger_service_rate_id.currency_id',store=True,tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    passenger_service_rate_id = fields.Many2one('passenger.service.rate', string='Passenger Service Rate')
    for_date = fields.Date(string='Invoice For', default=fields.Date.today, tracking=True)
    inv_desc = fields.Html(string='Invoice Description')
    # product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    # journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
    #                              required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], string='Status', default='draft', tracking=True)

    @api.constrains('total_pax', 'inf', 'transit', 'ntl', 'inad', 'depor', 'tax_free','osc')
    def _check_integer_fields(self):
        for record in self:
            fields_to_check = ['total_pax', 'inf', 'transit', 'ntl', 'inad', 'depor', 'tax_free']
            for field in fields_to_check:
                value = getattr(record, field)
                if value and not isinstance(value, int):
                    raise ValidationError(_(f"The field {field} must be a valid integer number."))
                if value and value < 0:
                    raise ValidationError(_(f"The field {field} cannot be negative."))

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'context': {'create': False},
        }

    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                invoice = record.create_invoice()
                record.state='confirmed'
                if invoice:
                    record.write({
                        'state': 'invoiced',
                        'invoice_id': invoice.id
                    })

    def create_invoice(self):
        self.ensure_one()
        invoice_vals = self._prepare_invoice_vals()
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice

    def _prepare_invoice_vals(self):
        self.ensure_one()
        partner = self.airline_id.partner_id
        if not partner:
            raise ValidationError(_("No partner found for airline %s") % self.airline_id.name)

        return {
            'move_type': 'out_invoice',
            'partner_id': partner.id,  # You may want to change this to an actual customer
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, line) for line in self._prepare_invoice_line_vals()],
            'passenger_service_id': self.id,
            'currency_id': self.passenger_service_rate_id.currency_id.id,
            'form_type': 'PassengerService',
            'for_date': self.for_date,
            'journal_id': self.passenger_service_rate_id.journal_id.id,
        }

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        lines = []
        for line in self.passenger_service_line_ids:
            lines.append({
                'product_id': line.passenger_service_rate_id.product_id.id,
                'name': f"{line.flightno_id}",
                'quantity': line.invoice_pax,
                'price_unit': line.passenger_service_rate_id.pax_price,  # You need to set the appropriate price
                'passenger_service_line_id': line.id,
            })
        return lines

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('passenger.service.bill.seq') or '00001'
            if vals['type'] == 'domestic':
                vals['name'] = f'DPS/{current_date}/{sequence}'
            else:
                vals['name'] = f'IPS/{current_date}/{sequence}'
        return super(PassengerService, self).create(vals)

