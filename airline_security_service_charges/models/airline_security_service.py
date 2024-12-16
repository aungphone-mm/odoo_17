from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

class AirlineSecurityService(models.Model):
    _name = 'airline.security.service'
    _description = 'Airline Security Service'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], default='international', string='Type', tracking=True)
    airline_id = fields.Many2one('airline',string='Airline')
    airline_user_id = fields.Many2one('res.partner', string='Attention:', tracking=True)
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Date & Time', tracking=True)
    airline_security_service_line_ids = fields.One2many('airline.security.service.line', 'airline_security_service_id',
                                                      string='Security Details')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    security_rate_id = fields.Many2one('airline.security.rate', string='Security Rate')
    for_date = fields.Date(string='Invoice For', default=fields.Date.today, tracking=True)
    inv_desc = fields.Html(string='Invoice Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], string='Status', default='draft', tracking=True)

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
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, line) for line in self._prepare_invoice_line_vals()],
            'airline_security_service_id': self.id,
            'currency_id': self.security_rate_id.currency_id.id,
            'form_type': 'security',
            # 'for_date': self.for_date,
            'journal_id': self.security_rate_id.journal_id.id,
        }

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        lines = []
        for line in self.airline_security_service_line_ids:
            lines.append({
                'product_id': line.security_rate_id.product_id.id,
                'name': f"{line.flightno_id}",
                'quantity': 1,
                'price_unit': line.amount,  # You need to set the appropriate price
                'airline_security_service_line_id': line.id,
            })
        return lines

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('airline.security.bill.seq') or '00001'
            if vals['type'] == 'domestic':
                vals['name'] = f'DSC/{current_date}/{sequence}'
            else:
                vals['name'] = f'ISC/{current_date}/{sequence}'
        return super(AirlineSecurityService, self).create(vals)

