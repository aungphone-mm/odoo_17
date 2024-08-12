from markupsafe import Markup
from odoo import fields, models, api
from datetime import datetime


class ElectricMeter(models.Model):
    _name = 'electric.meter'
    _description = 'Electric Meter'

    name = fields.Char(string='Name', required=True)
    meter_number = fields.Char(string='Meter Number', required=True)
    location_id = fields.Many2one('location', string='Location', required=True)
    latest_reading_unit = fields.Integer(string='Latest Reading Unit')
    partner_id = fields.Many2one('res.partner', string="Customer", domain=[('customer_rank', '>', 0)])
    product_id = fields.Many2one(comodel_name='product.product',string='Product', required=True)
    active = fields.Boolean(string='Active', required=False, default=True)


class ElectricRate(models.Model):
    _name = 'electric.rate'
    _description = 'Electric Rate'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    business_source_id = fields.One2many(
        comodel_name='business.source',
        inverse_name='rate_id',
        string='Business Source',
        required=False)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')], required=True)
    rate_line_ids = fields.One2many(comodel_name='electric.rate.line', inverse_name='rate_id', string='Rate Line',
                                    required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    active = fields.Boolean(string='Active', default=True)


class ElectricRateLine(models.Model):
    _name = 'electric.rate.line'
    _description = 'Electric Rate Line'

    from_unit = fields.Integer(string='From Unit', required=True)
    to_unit = fields.Integer(string='To Unit')
    unit_price = fields.Float(string='Unit Price', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='rate_id.currency_id',
        store=True,
        readonly=True
    )
    rate_id = fields.Many2one(comodel_name='electric.rate', string='Rate', required=True)


class ElectricMeterReading(models.Model):
    _name = 'electric.meter.reading'
    _description = 'Electric Meter Reading'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    description = fields.Text(string='Description', tracking=True)
    reading_date = fields.Date(string='Reading Date', required=True, default=fields.Date.today, tracking=True)
    reading_line_ids = fields.One2many(comodel_name='electric.meter.reading.line', inverse_name='reading_id',
                                       string='Reading Line', required=False, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
                             required=True, default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('electric.meter.reading.seq') or '00001'
            vals['name'] = f'EMR/{current_date}/{sequence}'
        return super(ElectricMeterReading, self).create(vals)

    def default_get(self, field_list):
        res = super(ElectricMeterReading, self).default_get(field_list)

        # Auto-populate reading lines with active meters
        meter_obj = self.env['electric.meter']
        active_meters = meter_obj.search([('active', '=', True)])
        reading_lines = [(0, 0, {'meter_id': meter.id, 'partner_id': meter.partner_id}) for meter in active_meters]

        res.update({
            'reading_line_ids': reading_lines,
        })
        return res

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for line in self.reading_line_ids:
            line.narration = f'<b>Meter No : {line.meter_id.name}</b><br/>'
            if line.total_unit > 0:
                if line.partner_id and line.partner_id.business_source_id:
                    rate = line.partner_id.business_source_id.rate_id
                    remaining_units = line.total_unit
                    total_amount = 0

                    for rate_line in rate.rate_line_ids:
                        # Calculate units in the current bracket
                        units_in_bracket = min(remaining_units, rate_line.to_unit - rate_line.from_unit + 1)

                        # Calculate amount for the current bracket
                        bracket_amount = units_in_bracket * rate_line.unit_price
                        total_amount += bracket_amount

                        # Subtract units that have been accounted for
                        remaining_units -= units_in_bracket

                        line.narration += f'{rate_line.from_unit:,} - {rate_line.to_unit:,}: {units_in_bracket:,} units x {rate_line.unit_price:,} = {bracket_amount:,}<br/>'

                        # Break if there are no remaining units
                        if remaining_units <= 0:
                            break

                    line.amount = total_amount

    def action_done(self):
        self.write({'state': 'done'})
        for line in self.reading_line_ids:
            if line.current_reading_unit > line.latest_reading_unit:
                line.write({'state': 'done'})
        self._update_latest_reading_units()
        self._generate_invoice()

    def action_cancel(self):
        self.write({'state': 'canceled'})

    def _update_latest_reading_units(self):
        for line in self.reading_line_ids:
            if line.current_reading_unit > line.latest_reading_unit:
                line.meter_id.write({'latest_reading_unit': line.current_reading_unit})

    def _generate_invoice(self):
        invoices = {}

        for line in self.reading_line_ids:
            if line.amount > 0:
                partner = line.partner_id
                # Check if an invoice for this partner already exists
                if partner not in invoices:
                    # Create a new invoice if it doesn't exist
                    invoice = self.env['account.move'].create({
                        'partner_id': partner.id,
                        'currency_id': line.currency_id.id,
                        'invoice_date': self.reading_date,
                        'invoice_origin': self.name,
                        'journal_id': partner.business_source_id.rate_id.journal_id.id,
                        'narration': line.narration,
                        'move_type': 'out_invoice',
                        'invoice_line_ids': [],  # Start with no lines
                    })
                    invoices[partner] = invoice
                else:
                    invoice = invoices[partner]
                    invoice.narration = (invoice.narration or '') + Markup(line.narration)

                # Add the invoice line to the existing or new invoice
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': line.meter_id.product_id.id,
                    'quantity': 1,
                    'name': f'{line.meter_id.name} - {line.total_unit} Units',
                    'price_unit': line.amount,
                })

                line.invoice_id = invoice.id

    @api.onchange('reading_line_ids')
    def _onchange_reading_line_ids(self):
        for line in self.reading_line_ids:
            if line.current_reading_unit is not False and line.latest_reading_unit is not False:
                if line.current_reading_unit > line.latest_reading_unit:
                    line.total_unit = line.current_reading_unit - line.latest_reading_unit
                else:
                    line.total_unit = 0


class ElectricMeterReadingLine(models.Model):
    _name = 'electric.meter.reading.line'
    _description = 'Electric Meter Reading Line'

    reading_id = fields.Many2one('electric.meter.reading', string='Reading', required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    meter_id = fields.Many2one('electric.meter', string='Electric Meter', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=True)
    latest_reading_unit = fields.Integer(string='Latest Reading Unit', compute='_compute_latest_reading_unit', store=True, readonly=False)
    current_reading_unit = fields.Integer(string='Current Reading Unit', required=True)
    total_unit = fields.Integer(string='Total Unit', required=True, store=True)
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice', required=False, inverse_name="reading_line_id")
    amount = fields.Float(string='Amount', required=True, default=0.0, currency_field='currency_id')
    narration = fields.Text(string='Narration')
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
                             required=True, default='draft', related="reading_id.state")

    @api.depends('meter_id.latest_reading_unit')
    def _compute_latest_reading_unit(self):
        for record in self:
            if record.state == 'draft':
                meter = record.meter_id
                record.latest_reading_unit = meter.latest_reading_unit
                record.partner_id = meter.partner_id
                record.currency_id = meter.partner_id.business_source_id.rate_id.currency_id

class AccountMove(models.Model):
    _inherit = 'account.move'

    reading_line_id = fields.Many2one('electric.meter.reading.line', string='Electric Meter Reading Line', required=False)
