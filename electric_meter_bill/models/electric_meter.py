import xlsxwriter
from io import BytesIO
import base64
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class ElectricMeter(models.Model):
    _name = 'electric.meter'
    _description = 'Electric Meter'

    name = fields.Char(string='Name', required=True)
    meter_number = fields.Char(string='Meter Number', required=True)
    location_id = fields.Many2one('location', string='Location', required=True)
    latest_reading_unit = fields.Float(string='Latest Reading Unit', digits=(16,3))
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
    unit_price = fields.Float(string='Unit Price', required=True, digits=(10, 5))
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

    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super(ElectricMeterReading, self)._valid_field_parameter(field, name)

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    description = fields.Text(string='Description', tracking=True)
    reading_date = fields.Date(string='Reading Date', required=True, default=fields.Date.today, tracking=True)
    for_date = fields.Date(string='Invoice For',default=fields.Date.today)
    reading_line_ids = fields.One2many(comodel_name='electric.meter.reading.line', inverse_name='reading_id',
                                       string='Reading Line', required=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
        required=True, default='draft', tracking=True)
    inv_desc = fields.Html(string='Invoice Description')
    note_desc = fields.Html(string='Note Description')
    xlsx_file = fields.Binary('Excel File')

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                current_date = datetime.now().strftime('%Y/%m')
                sequence = self.env['ir.sequence'].next_by_code('electric.meter.reading.seq') or '00001'
                vals['name'] = f'EMR/{current_date}/{sequence}'
        return super().create(vals_list)

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
        for line in self.reading_line_ids:
            if line.total_unit > 0 and line.partner_id and line.partner_id.business_source_id:
                rate = line.partner_id.business_source_id.rate_id
                total_units = line.total_unit
                remaining_units = total_units
                total_amount = 0

                # Sort rate lines by from_unit to ensure correct order
                rate_lines = rate.rate_line_ids.sorted(key=lambda r: r.from_unit)

                for rate_line in rate_lines:
                    bracket_size = rate_line.to_unit - rate_line.from_unit
                    units_in_bracket = min(remaining_units, bracket_size)

                    if units_in_bracket <= 0:
                        break

                    bracket_amount = float(units_in_bracket * rate_line.unit_price)
                    total_amount += bracket_amount
                    remaining_units -= units_in_bracket

                # Apply MGM percentage if exists
                if line.meter_id.mgm_percentage:
                    mgm_amount = float((total_amount * line.meter_id.mgm_percentage) / 100)
                    total_amount += mgm_amount

                line.amount = total_amount
    # def action_confirm(self):
    #     self.write({'state': 'confirmed'})
    #     for line in self.reading_line_ids:
    #         # line.narration = f'<b>Meter No : {line.meter_id.name}</b><br/>'
    #         if line.total_unit > 0:
    #             if line.partner_id and line.partner_id.business_source_id:
    #                 rate = line.partner_id.business_source_id.rate_id
    #                 remaining_units = line.total_unit
    #                 total_amount = 0
    #
    #                 for rate_line in rate.rate_line_ids:
    #                     # Calculate units in the current bracket
    #                     units_in_bracket = min(remaining_units, rate_line.to_unit - rate_line.from_unit)
    #
    #                     # Calculate amount for the current bracket
    #                     bracket_amount = units_in_bracket * rate_line.unit_price
    #                     total_amount += bracket_amount
    #
    #                     # Subtract units that have been accounted for
    #                     remaining_units -= units_in_bracket
    #
    #                     # line.narration += f'{rate_line.from_unit:,} - {rate_line.to_unit:,}: {units_in_bracket:,} units x {rate_line.unit_price:,} = {bracket_amount:,}<br/>'
    #
    #                     # Break if there are no remaining units
    #                     if remaining_units <= 0:
    #                         break
    #                         #aung
    #
    #                 line.amount = total_amount
    #                 if line.meter_id.mgm_percentage:
    #                     mgm_charge = (line.amount / 100) * line.meter_id.mgm_percentage
    #                     line.amount += mgm_charge
    #                     # line.narration += f'Management Charge ({line.meter_id.mgm_percentage}%): {mgm_charge:,}<br/>'

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
        meter_invoices = {}
        partner_invoices = {}

        for line in self.reading_line_ids:
            if line.final_amount > 0:
                partner = line.partner_id
                meter_number = line.meter_id.meter_number

                # Get or create invoice
                if meter_number in meter_invoices:
                    invoice = meter_invoices[meter_number]
                elif partner in partner_invoices:
                    invoice = partner_invoices[partner]
                else:
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
                    })
                    meter_invoices[meter_number] = invoice
                    partner_invoices[partner] = invoice

                # Create main invoice line
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': line.meter_id.product_id.id,
                    'quantity': 1,
                    'name': f'{line.meter_id.name} - {line.total_unit} Units',
                    'price_unit': line.amount,
                    'reading_line_id': line.id,
                })

                # Create subtraction lines if any exist
                if line.subtraction_line_ids:
                    for sub_line in line.subtraction_line_ids:
                        self.env['account.move.line'].create({
                            'move_id': invoice.id,
                            'name': f'Subtraction: {sub_line.name}',
                            'quantity': 1,
                            'price_unit': -sub_line.subtraction_amount,  # Negative to show as reduction
                            'reading_line_id': line.id,
                        })

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
                if line.current_reading_unit >= line.latest_reading_unit:
                    line.total_unit = line.current_reading_unit - line.latest_reading_unit
                else:
                    line.total_unit = 0

    def _compute_consolidated_readings(self):
        """Compute consolidated readings grouped by customer"""
        consolidated = {}
        for line in self.reading_line_ids:
            customer = line.partner_id.name
            if customer not in consolidated:
                consolidated[customer] = {
                    'meter_details': [],
                    'prev_reading': 0,
                    'curr_reading': 0,
                    'total_units': 0,
                    'total_amount': 0,
                }

            meter_detail = {
                'meter_no': line.meter_id.name,
                'location': line.location_id.name or '',
                'invoice': line.invoice_id.name or '',
            }
            consolidated[customer]['meter_details'].append(meter_detail)
            consolidated[customer]['prev_reading'] += line.latest_reading_unit
            consolidated[customer]['curr_reading'] += line.current_reading_unit
            consolidated[customer]['total_units'] += line.total_unit
            consolidated[customer]['total_amount'] += line.amount

        return consolidated

    def action_print_consolidated_report(self):
        return self.env.ref('electric_meter_bill.action_report_consolidated_meter_reading').report_action(self)

    def action_export_excel(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Meter Readings')

        # Add headers with subtraction columns
        headers = ['Meter', 'Customer', 'Previous Reading', 'Current Reading',
                   'Total Units', 'Amount', 'Subtractions', 'Final Amount']
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#1a73e8',
            'font_color': 'white'
        })

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Add data
        row = 1
        for line in self.reading_line_ids:
            worksheet.write(row, 0, line.meter_id.name)
            worksheet.write(row, 1, line.partner_id.name)
            worksheet.write(row, 2, line.latest_reading_unit)
            worksheet.write(row, 3, line.current_reading_unit)
            worksheet.write(row, 4, line.total_unit)
            worksheet.write(row, 5, f"{line.amount:,.2f}")

            # Add subtraction details
            subtraction_details = []
            for sub in line.subtraction_line_ids:
                subtraction_details.append(f"{sub.name}: {sub.subtraction_amount:,.2f}")
            worksheet.write(row, 6, "\n".join(subtraction_details))

            worksheet.write(row, 7, f"{line.final_amount:,.2f}")
            row += 1

        # Adjust column widths
        worksheet.set_column('A:A', 20)  # Meter
        worksheet.set_column('B:B', 40)  # Customer
        worksheet.set_column('C:D', 15)  # Readings
        worksheet.set_column('E:E', 12)  # Total Units
        worksheet.set_column('F:F', 15)  # Amount
        worksheet.set_column('G:G', 30)  # Subtractions
        worksheet.set_column('H:H', 15)  # Final Amount

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        self.xlsx_file = base64.b64encode(xlsx_data)

        filename = f'Meter_Readings_{self.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=xlsx_file&filename={filename}&download=true',
            'target': 'self',
        }
    def action_export_excel_consolidated(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Meter Readings')

        # Add styles
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#1a73e8',
            'font_color': 'white',
            'border': 1
        })

        # Add headers
        headers = ['Invoice No.', 'Customer', 'Meter Details', 'Previous Reading',
                   'Current Reading', 'Total Units', 'Amount']

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Group data by invoice number
        invoice_data = {}
        row = 1

        for line in self.reading_line_ids:
            if line.invoice_id and line.invoice_id.name:
                inv_num = line.invoice_id.name
                if inv_num not in invoice_data:
                    invoice_data[inv_num] = {
                        'rows': [],
                        'total_amount': 0
                    }

                invoice_data[inv_num]['rows'].append({
                    'customer': line.partner_id.name,
                    'meter_details': f"Meter: {line.meter_id.name}\nLocation: {line.meter_id.location_id.name}",
                    'prev_reading': line.latest_reading_unit,
                    'curr_reading': line.current_reading_unit,
                    'total_units': line.total_unit,
                    'amount': line.amount
                })
                invoice_data[inv_num]['total_amount'] += line.amount

        # Write data with subtotals
        row = 1
        for inv_num, data in invoice_data.items():
            for entry in data['rows']:
                worksheet.write(row, 0, inv_num)
                worksheet.write(row, 1, entry['customer'])
                worksheet.write(row, 2, entry['meter_details'])
                worksheet.write(row, 3, entry['prev_reading'])
                worksheet.write(row, 4, entry['curr_reading'])
                worksheet.write(row, 5, entry['total_units'])
                worksheet.write(row, 6, entry['amount'])
                row += 1

            # Add subtotal for invoice
            if len(data['rows']) > 1:
                worksheet.write(row, 5, 'Invoice Total:')
                worksheet.write(row, 6, data['total_amount'])
                row += 1
                row += 1  # Add blank row after subtotal

        # Adjust column widths
        worksheet.set_column('A:A', 15)  # Invoice No
        worksheet.set_column('B:B', 40)  # Customer
        worksheet.set_column('C:C', 35)  # Meter Details
        worksheet.set_column('D:D', 15)  # Previous Reading
        worksheet.set_column('E:E', 15)  # Current Reading
        worksheet.set_column('F:F', 12)  # Total Units
        worksheet.set_column('G:G', 15)  # Amount

        workbook.close()
        output.seek(0)

        # Set binary field and return download action
        self.xlsx_file = base64.b64encode(output.read())

        filename = f'Meter_Readings_{self.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=xlsx_file&filename={filename}&download=true',
            'target': 'self',
        }

class ElectricMeterSubtractionLine(models.Model):
    _name = 'electric.meter.subtraction.line'
    _description = 'Electric Meter Subtraction Line'

    reading_line_id = fields.Many2one(
        'electric.meter.reading.line',
        string='Reading Line',
        required=True
    )
    name = fields.Char(
        string='Description',
        required=True,
        help="Description of the subtraction"
    )
    subtraction_amount = fields.Float(
        string='Amount',
        required=True,
        digits=(10, 5)
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='reading_line_id.currency_id',
        string='Currency'
    )

class ElectricMeterReadingLine(models.Model):
    _name = 'electric.meter.reading.line'
    _description = 'Electric Meter Reading Line'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    @api.model
    def _valid_field_parameter(self, field, name):
        # The correct way to call super() with explicit class reference
        return name == 'digits' or super(ElectricMeterReadingLine, self)._valid_field_parameter(field, name)

    reading_id = fields.Many2one('electric.meter.reading', string='Reading', required=True)
    selection_line = fields.Boolean(string='Select', default=False)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True, automatic=True, store=True)
    meter_id = fields.Many2one('electric.meter', string='Electric Meter', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    latest_reading_unit = fields.Float(string='Latest Reading Unit', compute='_compute_latest_reading_unit',
                                       store=True, readonly=False, digits=(16, 3))  # Changed from Integer to Float
    current_reading_unit = fields.Float(string='Current Reading Unit', required=True, digits=(16, 3))
    total_unit = fields.Float(string='Total Unit', required=True, digits=(16, 2))
    # invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice', required=False,
    #                              inverse_name="reading_line_id")
    invoice_id = fields.Many2one('account.move', string='Invoice')
    amount = fields.Monetary(string='Amount', required=True, default=0.0, currency_field='currency_id',digits=(10, 5))
    # Update amount field definition
    # amount = fields.Monetary(string='Amount', required=True, default=0.0, currency_field='currency_id')
    narration = fields.Text(string='Narration')
    # state = fields.Selection(
    #     [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')], string='Status',
    #     required=True, default='draft', related="reading_id.state")
    state = fields.Selection(related="reading_id.state", readonly=True)
    mgm_percentage = fields.Integer("Management Fee")
    location_id = fields.Many2one('location', string='Location', related='meter_id.location_id', store=True,
                                  readonly=True)
    subtraction_line_ids = fields.One2many(
        'electric.meter.subtraction.line',
        'reading_line_id',
        string='Subtraction Lines'
    )
    final_amount = fields.Monetary(
        string='Final Amount',
        compute='_compute_final_amount',
        store=True,
        currency_field='currency_id',
        digits=(10, 5)
    )

    @api.depends('amount', 'subtraction_line_ids.subtraction_amount')
    def _compute_final_amount(self):
        for record in self:
            total_subtraction = sum(line.subtraction_amount for line in record.subtraction_line_ids)
            record.final_amount = record.amount - total_subtraction

    # @api.depends('partner_id', 'partner_id.business_source_id.rate_id.currency_id')
    # def _compute_currency_id(self):
    #     for record in self:
    #         if record.partner_id and record.partner_id.business_source_id.rate_id.currency_id:
    #             record.currency_id = record.partner_id.business_source_id.rate_id.currency_id
    #         else:
    #             # Default to company currency if no specific currency is set
    #             record.currency_id = self.env.company.currency_id

    @api.onchange('current_reading_unit', 'latest_reading_unit')
    def _onchange_reading_units(self):
        if self.current_reading_unit is not False and self.latest_reading_unit is not False:
            if self.current_reading_unit >= self.latest_reading_unit:
                self.total_unit = float(self.current_reading_unit - self.latest_reading_unit)
            else:
                self.total_unit = 0.0

    @api.depends('meter_id.latest_reading_unit')
    def _compute_latest_reading_unit(self):
        for record in self:
            if record.state == 'draft':
                meter = record.meter_id
                record.latest_reading_unit = meter.latest_reading_unit
                record.partner_id = meter.partner_id
                record.currency_id = meter.partner_id.business_source_id.rate_id.currency_id


class AddSubtractionWizard(models.TransientModel):
    _name = 'add.subtraction.wizard'
    _description = 'Add Subtraction Wizard'
    _transient_max_count = 100

    reading_line_id = fields.Many2one(
        'electric.meter.reading.line',
        string='Reading Line',
        required=True
    )
    name = fields.Char(
        string='Description',
        required=True
    )
    subtraction_amount = fields.Float(
        string='Amount to Subtract',
        required=True,
        digits=(10, 5)
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='reading_line_id.currency_id',
        readonly=True
    )

    def action_add_subtraction(self):
        self.ensure_one()
        if self.subtraction_amount <= 0:
            raise UserError('Subtraction amount must be positive')

        self.env['electric.meter.subtraction.line'].create({
            'name': self.name,
            'reading_line_id': self.reading_line_id.id,
            'subtraction_amount': self.subtraction_amount
        })

        return {'type': 'ir.actions.act_window_close'}

class AccountMove(models.Model):
    _inherit = 'account.move'

    reading_line_id = fields.Many2one('electric.meter.reading.line', string='Electric Meter Reading Line',
                                      required=False)
    form_type = fields.Char('Form Type')

    # In the AccountMove class
    def action_print_electric_meter_invoice(self):
        return self.env.ref('electric_meter_bill.action_report_electric_meter_invoice').report_action(self)

    def _compute_meter_details(self):
        """Compute the meter details including rates and subtractions"""
        self.ensure_one()
        result = []

        # Group by meter to avoid duplicates
        seen_meters = set()
        for line in self.invoice_line_ids.filtered(lambda l: l.reading_line_id):
            meter = line.reading_line_id.meter_id
            if meter.id in seen_meters:
                continue
            seen_meters.add(meter.id)

            reading_line = line.reading_line_id
            rate = reading_line.partner_id.business_source_id.rate_id

            # Calculate base amount with rate brackets
            total_unit = reading_line.total_unit
            remain_unit = total_unit
            subtotal_amount = 0

            rate_details = []
            for rate_line in rate.rate_line_ids:
                if remain_unit <= 0:
                    break

                units_in_bracket = min(remain_unit, rate_line.to_unit - rate_line.from_unit)
                bracket_amount = units_in_bracket * rate_line.unit_price

                rate_details.append({
                    'units': units_in_bracket,
                    'rate': rate_line.unit_price,
                    'amount': bracket_amount
                })

                subtotal_amount += bracket_amount
                remain_unit -= units_in_bracket

            # Calculate MGM charge if applicable
            mgm_charge = 0
            if meter.mgm_percentage:
                mgm_charge = (subtotal_amount * meter.mgm_percentage) / 100

            # Get subtractions
            subtractions = [{
                'name': sub.name,
                'amount': sub.subtraction_amount
            } for sub in reading_line.subtraction_line_ids]

            # Calculate final amount
            total_subtractions = sum(sub['amount'] for sub in subtractions)
            final_amount = subtotal_amount + mgm_charge - total_subtractions

            result.append({
                'meter_id': meter.id,
                'meter_number': meter.name,
                'partner_name': meter.partner_id.name,
                'location': meter.location_id.name,
                'latest_reading': reading_line.latest_reading_unit,
                'current_reading': reading_line.current_reading_unit,
                'total_units': total_unit,
                'rate_details': rate_details,
                'subtotal': subtotal_amount,
                'mgm_percentage': meter.mgm_percentage,
                'mgm_charge': mgm_charge,
                'subtractions': subtractions,
                'final_amount': final_amount
            })

        return result

    def get_final_total(self):
        """Get final total amount after all calculations and deductions"""
        final_total = 0
        for line in self.invoice_line_ids.filtered(lambda l: l.reading_line_id):
            if line.reading_line_id:
                # Add the main amount
                if line.price_unit > 0:
                    final_total += line.price_unit
                # Subtract any deduction amounts (which are stored as negative values)
                else:
                    final_total += line.price_unit  # Adding negative values will subtract them
        return final_total

    # def get_total_units(self):
    #     """Get total units across all meters"""
    #     return sum(line.reading_line_id.total_unit
    #                for line in self.invoice_line_ids.filtered(lambda l: l.reading_line_id))

    def get_total_units(self):
        """Calculate total units from all meter readings, including adjustments"""
        total_units = 0
        for meter in self._compute_meter_details():
            total_units += meter['total_units']
        return total_units

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reading_line_id = fields.Many2one('electric.meter.reading.line', string='Electric Meter Reading Line',
                                      required=False)