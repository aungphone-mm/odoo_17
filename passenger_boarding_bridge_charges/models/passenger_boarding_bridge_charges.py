from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

class PassengerBoardingBridgeCharges(models.Model):
    _name = 'passenger.boarding.bridge.charges'
    _description = 'Passenger Boarding Bridge Charges'
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
    currency_id = fields.Many2one('res.currency', string='Currency', related='bridge_rate_id.currency_id',
                                  store=True,
                                  readonly=True)
    passenger_boarding_bridge_charges_line_ids = fields.One2many('passenger.boarding.bridge.charges.line', 'passenger_boarding_bridge_charges_id',
                                                      string='Bridge Details')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    bridge_rate_id = fields.Many2one('passenger.boarding.bridge.charges.rate', string='Bridge Rate')
    for_date = fields.Date(string='Invoice For', default=fields.Date.today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], string='Status', default='draft', tracking=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)

    @api.depends('passenger_boarding_bridge_charges_line_ids.amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.passenger_boarding_bridge_charges_line_ids.mapped('amount'))

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
    def unlink(self):
        for record in self:
            if record.passenger_boarding_bridge_charges_line_ids:
                raise ValidationError(
                    _("You cannot delete this Passenger Boarding record because it has related line items. Please delete all Passenger Boarding Lines first."))
        return super(PassengerBoardingBridgeCharges, self).unlink()

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
            'passenger_boarding_bridge_charges_id': self.id,
            'currency_id': self.bridge_rate_id.currency_id.id,
            'form_type': 'bridge',
            # 'for_date': self.for_date,
            'journal_id': self.bridge_rate_id.journal_id.id,
        }

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        lines = []
        for line in self.passenger_boarding_bridge_charges_line_ids:
            lines.append({
                'product_id': line.bridge_rate_id.product_id.id,
                'name': f"{line.flightno_id}",
                'quantity': 1,
                'price_unit': line.amount,  # You need to set the appropriate price
                'passenger_boarding_bridge_charges_line_id': line.id,
            })
        return lines

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('passenger.boarding.bridge.charges.seq') or '00001'
            if vals['type'] == 'domestic':
                vals['name'] = f'DPB/{current_date}/{sequence}'
            else:
                vals['name'] = f'IPB/{current_date}/{sequence}'
        return super(PassengerBoardingBridgeCharges, self).create(vals)

