from markupsafe import Markup
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class ElectricMeter(models.Model):
    _name = 'electric.meter'
    _description = 'Electric Meter'

    name = fields.Char(string='Name', required=True)
    meter_number = fields.Char(string='Meter Number', required=True)
    location_id = fields.Many2one('location', string='Location', required=True)
    latest_reading_unit = fields.Integer(string='Latest Reading Unit')
    partner_id = fields.Many2one('res.partner', string="Customer", domain=[('customer_rank', '>', 0), ('is_company', '=', True), ('active', '=', True)])
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    active = fields.Boolean(string='Active', required=False, default=True)
    mgm_percentage= fields.Integer("Management Fee")

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
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', domain=[('type', '=', 'sale')],
                                 required=True)
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
    _order = 'id desc'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    description = fields.Text(string='Description', tracking=True)
    reading_date = fields.Date(string='Reading Date', required=True, default=fields.Date.today, tracking=True)
    for_date = fields.Date(string='Invoice For',default=fields.Date.today, tracking=True)
    reading_line_ids = fields.One2many(comodel_name='electric.meter.reading.line', inverse_name='reading_id',
                                       string='Reading Line', required=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
        required=True, default='draft', tracking=True)
    inv_desc = fields.Html(string='Invoice Description')
    note_desc = fields.Html(string='Note Description')

    @api.model
    def read(self, fields=None, load='_classic_read'):
        return super(ElectricMeterReading, self).read(fields, load)

    @api.model
    def write(self, vals):
        return super(ElectricMeterReading, self).write(vals)

    def delete_selected_lines(self):
        """Delete selected lines from the reading_line_ids field."""
        if self.state != 'draft':
            raise UserError('You can only delete lines in Draft state.')
        for line in self.reading_line_ids:
            if line.selection_line:
                line.unlink()

        reload_action = {
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        }

        return reload_action

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('electric.meter.reading.seq') or '00001'
            vals['name'] = f'EMR/{current_date}/{sequence}'
        return super(ElectricMeterReading, self).create(vals)

    def default_get(self, field_list):
        res = super(ElectricMeterReading, self).default_get(field_list)

        # Auto populate reading lines with active meters
        meter_obj = self.env['electric.meter']
        active_meters = meter_obj.search([('active', '=', True)])
        reading_lines = [(0, 0, {'meter_id': meter.id, 'partner_id': meter.partner_id}) for meter in active_meters]

        res.update({
            'reading_line_ids': reading_lines,
        })
        return res

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # First group readings by meter number
        meter_readings = {}
        for line in self.reading_line_ids:
            meter_number = line.meter_id.meter_number
            if meter_number not in meter_readings:
                meter_readings[meter_number] = []
            meter_readings[meter_number].append(line)
        # Process each meter's readings
        for meter_number, lines in meter_readings.items():
            if len(lines) > 1:
                # Multiple readings for same meter - combine them
                total_units = sum(line.total_unit for line in lines)
                if total_units <= 0:
                    continue
                base_line = lines[0]  # Use first line as base for calculations
                if base_line.partner_id and base_line.partner_id.business_source_id:
                    rate = base_line.partner_id.business_source_id.rate_id
                    remaining_units = total_units
                    total_amount = 0
                    # narration = f'<b>Meter No : {base_line.meter_id.name}</b><br/>'
                    # Calculate combined amount
                    for rate_line in rate.rate_line_ids:
                        units_in_bracket = min(remaining_units,
                                               rate_line.to_unit - rate_line.from_unit + 1)
                        bracket_amount = units_in_bracket * rate_line.unit_price
                        total_amount += bracket_amount
                        # narration += f'{rate_line.from_unit:,} - {rate_line.to_unit:,}: {units_in_bracket:,} units x {rate_line.unit_price:,} = {bracket_amount:,}<br/>'
                        remaining_units -= units_in_bracket
                        if remaining_units <= 0:
                            break
                    # Apply management fee if any
                    if base_line.meter_id.mgm_percentage:
                        mgm_charge = (total_amount / 100) * base_line.meter_id.mgm_percentage
                        total_amount += mgm_charge
                        # narration += f'Management Charge ({base_line.meter_id.mgm_percentage}%): {mgm_charge:,}<br/>'
                    # Distribute total amount proportionally among lines
                    for line in lines:
                        if total_units > 0:
                            line_proportion = line.total_unit / total_units
                            line.amount = total_amount * line_proportion
                            # line.narration = narration
            else:
                # Single reading - process normally
                line = lines[0]
                # line.narration = f'<b>Meter No : {line.meter_id.name}</b><br/>'
                if line.total_unit > 0:
                    if line.partner_id and line.partner_id.business_source_id:
                        rate = line.partner_id.business_source_id.rate_id
                        remaining_units = line.total_unit
                        total_amount = 0
                        # Calculate charges for each rate bracket
                        for rate_line in rate.rate_line_ids:
                            units_in_bracket = min(remaining_units,
                                                   rate_line.to_unit - rate_line.from_unit + 1)
                            bracket_amount = units_in_bracket * rate_line.unit_price
                            total_amount += bracket_amount
                            # line.narration += f'{rate_line.from_unit:,} - {rate_line.to_unit:,}: {units_in_bracket:,} units x {rate_line.unit_price:,} = {bracket_amount:,}<br/>'
                            remaining_units -= units_in_bracket
                            if remaining_units <= 0:
                                break
                        # Set the total amount
                        line.amount = total_amount
                        # Apply management fee if configured
                        if line.meter_id.mgm_percentage:
                            mgm_charge = (line.amount / 100) * line.meter_id.mgm_percentage
                            line.amount += mgm_charge
                            # line.narration += f'Management Charge ({line.meter_id.mgm_percentage}%): {mgm_charge:,}<br/>'

    def action_done(self):
        self.write({'state': 'done'})
        for line in self.reading_line_ids:
            if line.current_reading_unit > line.latest_reading_unit:
                line.write({'state': 'done'})
        self._update_latest_reading_units()
        self._generate_invoice()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Electric Meter Bill Invoice(s) are already created',
                'type': 'rainbow_man',
            }
        }

    def action_cancel(self):
        self.write({'state': 'canceled'})

    def _update_latest_reading_units(self):
        for line in self.reading_line_ids:
            if line.current_reading_unit > line.latest_reading_unit:
                line.meter_id.write({'latest_reading_unit': line.current_reading_unit})

    def _generate_invoice(self):
        meter_invoices = {}  # Will store {meter_number: invoice} for same meter invoices
        partner_invoices = {}  # Will store {partner: invoice} for same partner invoices

        for line in self.reading_line_ids:
            if line.amount > 0:
                partner = line.partner_id
                meter_number = line.meter_id.meter_number

                # First check if there's an existing invoice for this meter number
                if meter_number in meter_invoices:
                    invoice = meter_invoices[meter_number]
                # Then check if there's an existing invoice for this partner
                elif partner in partner_invoices:
                    invoice = partner_invoices[partner]
                else:
                    # Create a new invoice
                    invoice = self.env['account.move'].create({
                        'partner_id': partner.id,
                        'currency_id': line.currency_id.id,
                        'invoice_date': self.reading_date,
                        'invoice_origin': self.name,
                        'journal_id': partner.business_source_id.rate_id.journal_id.id,
                        'narration': line.narration,
                        'move_type': 'out_invoice',
                        'reading_line_id': line.id,
                        'invoice_line_ids': [],
                        'form_type': 'electric',
                        'for_date': self.for_date,
                    })
                    # Store invoice reference in both dictionaries
                    meter_invoices[meter_number] = invoice
                    partner_invoices[partner] = invoice

                # Update existing invoice with additional details
                # if invoice.narration:
                #     rate_description = partner.business_source_id.rate_id.description or ''
                #     new_narration = Markup(line.narration or '') + \
                #                     Markup('<div style="break-after:page"></div>') + \
                #                     Markup(rate_description)
                #     invoice.narration = (invoice.narration or '') + new_narration

                # Create invoice lines
                invoice_line = self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': line.meter_id.product_id.id,
                    'quantity': 1,
                    'name': f'{line.meter_id.name} - {line.total_unit} Units',
                    'price_unit': line.amount,
                    'reading_line_id': line.id,
                })

                # Set invoice reference on reading line
                line.invoice_id = invoice.id

    def _get_rate_breakdown(self, total_unit, rate):
        """
        Return a list of tuples containing the rate breakdown.
        Each tuple will have (from_unit, to_unit, units_in_bracket, unit_price, bracket_amount).
        """
        breakdown = []
        remaining_units = total_unit

        for rate_line in rate.rate_line_ids:
            if remaining_units <= 0:
                break

            units_in_bracket = min(remaining_units, rate_line.to_unit - rate_line.from_unit + 1)
            bracket_amount = units_in_bracket * rate_line.unit_price
            breakdown.append((rate_line.from_unit, rate_line.to_unit, units_in_bracket, rate_line.unit_price, bracket_amount))

            remaining_units -= units_in_bracket

        return breakdown

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

    _inherit = ['mail.activity.mixin', 'mail.thread']

    reading_id = fields.Many2one('electric.meter.reading', string='Reading', required=True)
    selection_line = fields.Boolean(string='Select', default=False)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True, automatic=True, store=True)
    meter_id = fields.Many2one('electric.meter', string='Electric Meter', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=True)
    latest_reading_unit = fields.Integer(string='Latest Reading Unit', compute='_compute_latest_reading_unit',
                                         store=True, readonly=False)
    current_reading_unit = fields.Integer(string='Current Reading Unit', required=True, tracking=True)
    total_unit = fields.Integer(string='Total Unit', required=True, store=True)
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice', required=False,
                                 inverse_name="reading_line_id")
    amount = fields.Float(string='Amount', required=True, default=0.0, currency_field='currency_id')
    narration = fields.Text(string='Narration')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
        required=True, default='draft', related="reading_id.state")
    mgm_percentage = fields.Integer("Management Fee")
    location_id = fields.Many2one('location', string='Location', related='meter_id.location_id', store=True,
                                  readonly=True)
    # currency_id = fields.Many2one('res.currency', string='Currency',
    #                               compute='_compute_currency_id', store=True)
    #
    # @api.depends('partner_id', 'partner_id.business_source_id.rate_id.currency_id')
    # def _compute_currency_id(self):
    #     for record in self:
    #         if record.partner_id and record.partner_id.business_source_id.rate_id.currency_id:
    #             record.currency_id = record.partner_id.business_source_id.rate_id.currency_id
    #         else:
    #             # Default to company currency if no specific currency is set
    #             record.currency_id = self.env.company.currency_id

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

    reading_line_id = fields.Many2one('electric.meter.reading.line', string='Electric Meter Reading Line',
                                      required=False)
    form_type = fields.Char('Form Type')
    for_date = fields.Date(string='Invoice For', tracking=True)

    # In the AccountMove class
    def action_print_electric_meter_invoice(self):
        return self.env.ref('electric_meter_bill.action_report_electric_meter_invoice').report_action(self)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reading_line_id = fields.Many2one('electric.meter.reading.line', string='Electric Meter Reading Line',
                                      required=False)