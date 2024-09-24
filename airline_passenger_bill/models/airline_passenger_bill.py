from odoo import fields, models, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class AirlinePassengerBill(models.Model):
    _name = 'airline.passenger.bill'
    _description = 'Airline Passenger Bill'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, index=True, default='New')
    type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], default='domestic', string='Type', track_visibility='always', tracking=True)

    user_id = fields.Many2one('res.users', string='Receptionist', default=lambda self: self.env.uid, required=True,
                              track_visibility='always', tracking=True)
    date = fields.Date('Date', default=fields.Date.context_today, required=True, track_visibility='always',
                       tracking=True)
    start_time = fields.Float(string='Start Time', required=True, track_visibility='always', tracking=True)
    end_time = fields.Float(string='End Time', required=True, track_visibility='always', tracking=True)
    airline_passenger_bill_line_ids = fields.One2many('airline.passenger.bill.line', 'airline_passenger_bill_id',
                                                      string='Passenger Details')
    passenger_rate_id = fields.Many2one('passenger.rate', string='Passenger Rate', required=True, track_visibility='always',
                                        tracking=True, domain="[('type', '=', type)]")
    format_code = fields.Char(string='Code', tracking=True, track_visibility='always')
    number_of_legs_encoded = fields.Integer(string='Legs', tracking=True, track_visibility='always')
    passenger_name = fields.Char(string='Passenger', tracking=True, track_visibility='always')
    electronic_ticket_indicator = fields.Char(string='Ticket', tracking=True, track_visibility='always')
    pnr_code = fields.Char(string='PNR', tracking=True, track_visibility='always')
    from_city_airport_code = fields.Char(string='From', tracking=True, track_visibility='always')
    to_city_airport_code = fields.Char(string='To', tracking=True, track_visibility='always')
    operating_carrier_designator = fields.Many2one('airline', string='Airline', tracking=True,
                                                   track_visibility='always')
    flight_number = fields.Char(string='Flight', tracking=True, track_visibility='always')
    date_of_flight = fields.Char(string='Date', tracking=True, track_visibility='always')
    compartment_code = fields.Char(string='Class', tracking=True, track_visibility='always')
    seat_number = fields.Char(string='Seat', tracking=True, track_visibility='always')
    check_in_sequence_number = fields.Char(string='SEQ', tracking=True, track_visibility='always')
    passenger_status = fields.Char(string='Status', tracking=True, track_visibility='always')
    raw = fields.Char(string='Raw')
    invoice_id = fields.Many2one('account.move', string='Invoice', tracking=True, track_visibility='always')


    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.passenger_rate_id = self.env['passenger.rate'].search(
                [('from_date', '<=', self.date), ('to_date', '>=', self.date), ('active', '=', True)], limit=1).id

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            current_date = datetime.now().strftime('%Y/%m')
            sequence = self.env['ir.sequence'].next_by_code('airline.passenger.bill.seq') or '00001'
            if vals['type'] == 'domestic':
                vals['name'] = f'DPB/{current_date}/{sequence}'
            else:
                vals['name'] = f'IPB/{current_date}/{sequence}'
        return super(AirlinePassengerBill, self).create(vals)

    @api.onchange('raw')
    def _onchange_raw(self):
        if self.raw:
            raw = self.raw
            self.format_code = raw[0:1].strip()
            self.number_of_legs_encoded = int(raw[1:2].strip())
            self.passenger_name = raw[2:22].strip()
            self.passenger_status = raw[57:58].strip()
            self.electronic_ticket_indicator = raw[22:23].strip()
            self.pnr_code = raw[23:30].strip()
            self.from_city_airport_code = raw[30:33].strip()
            self.to_city_airport_code = raw[33:36].strip()
            self.operating_carrier_designator = self.env['airline'].search([('name', '=', raw[36:39].strip())]).id
            self.flight_number = raw[39:44].strip()
            self.date_of_flight = raw[44:47].strip()
            self.compartment_code = raw[47:48].strip()
            self.seat_number = raw[49:52].strip()
            self.check_in_sequence_number = raw[53:57].strip()
            self.passenger_status = raw[57:58].strip()
            self._generate_invoice()
            self.update({
                'airline_passenger_bill_line_ids': [(0, 0, {
                    'raw': self.raw,
                    'check_in_sequence_number': self.check_in_sequence_number,
                    'passenger_status': self.passenger_status,
                    'airline_passenger_bill_id': self.id,
                    'format_code': self.format_code,
                    'number_of_legs_encoded': self.number_of_legs_encoded,
                    'passenger_name': self.passenger_name,
                    'electronic_ticket_indicator': self.electronic_ticket_indicator,
                    'pnr_code': self.pnr_code,
                    'from_city_airport_code': self.from_city_airport_code,
                    'to_city_airport_code': self.to_city_airport_code,
                    'operating_carrier_designator': self.operating_carrier_designator,
                    'flight_number': self.flight_number,
                    'date_of_flight': self.date_of_flight,
                    'compartment_code': self.compartment_code,
                    'seat_number': self.seat_number,
                    'invoice_id': self.invoice_id
                })]

            })
            self.unlink_raw()

    def action_open_form(self):
        if self.airline_passenger_bill_line_ids:
            # Assuming you want to open the first line's form view
            line_id = self.airline_passenger_bill_line_ids[-1].id  # Get the first line ID
            return {
                'name': self.display_name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'airline.passenger.bill.line',
                'res_id': line_id,  # Pass the specific line ID
                'target': 'new'
            }
        else:
            # Optionally handle the case where there are no lines
            return {
                'type': 'ir.actions.act_window_message',
                'title': 'No Lines Found',
                'message': 'There are no airline passenger bill lines to open.',
            }

    def _generate_invoice(self):
        parent_customer = self.env['res.partner'].search(
            [('id', '=', self.passenger_rate_id.default_partner.id)])
        partner = self.env['res.partner']
        if parent_customer:
            partner = partner.create({
                'name': self.passenger_name,
                'parent_id': parent_customer.id,
            })
        if self.passenger_name:
            invoice = self.env['account.move'].create({
                'partner_id': partner.id,
                'currency_id': self.passenger_rate_id.currency_id.id,
                'invoice_date': self.date,
                'invoice_origin': self.passenger_name,
                'journal_id': self.passenger_rate_id.journal_id.id,
                'narration': f'Flight: {self.from_city_airport_code}-{self.to_city_airport_code} {self.flight_number}',
                'move_type': 'out_invoice',
                'invoice_line_ids': [],  # Start with no lines
            })
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': self.passenger_rate_id.product_id.id,
                'quantity': 1,
                'name': f'{self.passenger_name}',
                'price_unit': self.passenger_rate_id.amount,
            })

            invoice.action_post()

            self.invoice_id = invoice.id
            self._create_invoice_download()

    def unlink_raw(self):
        if self.raw:
            self.raw = False

    def _create_invoice_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.invoice_id}/download',
            'target': 'self',
        }


class PassengerRate(models.Model):
    _name = 'passenger.rate'
    _description = 'Passenger Rate'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Name', required=True)
    receivable_account_id = fields.Many2one(comodel_name='account.account', string='Receivable Account', required=True,
                                            track_visibility='always')
    from_date = fields.Date('From Date', default=fields.Date.context_today, required=True, track_visibility='always')
    to_date = fields.Date('To Date', default=fields.Date.context_today, required=True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, track_visibility='always')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, track_visibility='always')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True,
                                 track_visibility='always')
    default_partner = fields.Many2one(comodel_name='res.partner', string='Default Partner', track_visibility='always')
    active = fields.Boolean(string='Active', default=True, track_visibility='onchange')
    type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], default='domestic', string='Domestic/International', track_visibility='always', tracking=True)
