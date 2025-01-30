import math
from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

class PassengerLanding(models.Model):
    _name = 'passenger.landing'
    _description = 'Passenger Landing'
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
    passenger_landing_line_ids = fields.One2many('passenger.landing.line', 'passenger_landing_id',
                                                      string='Aircraft Landing Details')
    currency_id = fields.Many2one('res.currency', string='Currency', related ='passenger_landing_rate_id.currency_id', store=True, readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    parking_invoice_id = fields.Many2one('account.move', string='Parking Invoice', readonly=True, copy=False)
    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate', string='Aircraft Landing Rate')
    for_date = fields.Date(string='Invoice For', default=fields.Date.today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], string='Status', default='draft', tracking=True)
    total_lines = fields.Integer(compute='_compute_total_lines', string='Total Lines', store=True)
    non_schedule = fields.Boolean(string='Non Schedule', default=False, tracking=True)

    @api.depends('passenger_landing_line_ids')
    def _compute_total_lines(self):
        for record in self:
            record.total_lines = len(record.passenger_landing_line_ids)

    def reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})

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

    def action_view_parking_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Parking Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.parking_invoice_id.id,
            'context': {'create': False}
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
        invoice_parking_vals = self._prepare_invoice_vals_parking()
        parking_invoice = self.env['account.move'].create(invoice_parking_vals)
        self.write({
            'invoice_id': invoice.id,
            'parking_invoice_id': parking_invoice.id
        })
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
            'passenger_landing_id': self.id,
            'currency_id': self.passenger_landing_rate_id.currency_id.id,
            'form_type': 'landing',
            # 'for_date': self.for_date,
            'journal_id': self.passenger_landing_rate_id.journal_id.id,
        }

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        lines = []
        for line in self.passenger_landing_line_ids:
            lines.append({
                'product_id': line.passenger_landing_rate_id.product_id.id,
                'name': f"{line.flight_registration_no.name}",
                'quantity': 1,
                'price_unit': line.amount,  # You need to set the appropriate price
                'passenger_landing_line_id': line.id,
            })
        return lines
    
    def _prepare_invoice_vals_parking(self):
        self.ensure_one()
        partner = self.airline_id.partner_id
        if not partner:
            raise ValidationError(_("No partner found for airline %s") % self.airline_id.name)

        return {
            'move_type': 'out_invoice',
            'partner_id': partner.id,  # You may want to change this to an actual customer
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, line) for line in self._prepare_invoice_line_vals_parking()],
            'passenger_landing_id': self.id,
            'currency_id': self.passenger_landing_rate_id.currency_id.id,
            'form_type': 'parking',
            # 'for_date': self.for_date,
            'journal_id': self.passenger_landing_rate_id.parking_journal_id.id,
        }

    def _prepare_invoice_line_vals_parking(self):
        self.ensure_one()
        lines = []
        for line in self.passenger_landing_line_ids:
            days = 1
            if line.end_time and line.start_time:
                time_diff = line.end_time - line.start_time
                days = max(1, math.ceil(time_diff.total_seconds() / (24 * 60 * 60)))

            lines.append({
                'product_id': line.passenger_landing_rate_id.parking_product_id.id,
                'name': f"{line.flight_registration_no.name}",
                'quantity': float(days),
                'price_unit': line.parking_rate,
                'passenger_landing_line_id': line.id,
            })
        return lines

    def _compute_parking_amount(self):
        for record in self:
            if not all([record.start_time, record.end_time, record.parking_rate]):
                record.parking_amount = 0.0
                continue
            # Calculate time difference in days
            time_diff = record.end_time - record.start_time
            days = time_diff.total_seconds() / (24 * 60 * 60)  # Convert to days
            # Round up to nearest day - any partial day counts as full day
            days = math.ceil(days)
            record.parking_amount = days

    def unlink(self):
        for record in self:
            if record.passenger_landing_line_ids:
                raise ValidationError(
                    _("You cannot delete this Landing record because it has related line items. Please delete all Landing Lines first."))
        return super(PassengerLanding, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('passenger.landing.bill.seq') or '00001'
            if vals['type'] == 'domestic':
                vals['name'] = f'DAL/{current_date}/{sequence}'
            else:
                vals['name'] = f'IAL/{current_date}/{sequence}'
        return super(PassengerLanding, self).create(vals)

