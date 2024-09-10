from odoo import fields, models, api, _
import qrcode
import base64
from io import BytesIO

class AirlinePassengerBillLine(models.Model):
    _name = 'airline.passenger.bill.line'
    _description = 'Airline Passenger Bill Line'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    format_code = fields.Char(string='Code', tracking=True, track_visibility='always')
    # Number of Legs Encoded: 1 leg for direct flight (RGN-KUL), 2 legs if there's a stopover (RGN-KUL-SIN).
    number_of_legs_encoded = fields.Integer(string='Legs', tracking=True, track_visibility='always')
    passenger_name = fields.Char(string='Passenger', tracking=True, track_visibility='always')
    # Electronic Ticket Indicator: 'E' for E-ticket (issued electronically), 'P' for paper ticket (rarely used).
    electronic_ticket_indicator = fields.Char(string='Ticket', tracking=True, track_visibility='always')
    # Operating Carrier PNR [Booking Reference] Code: PNR code of the airline that operates the flight.
    pnr_code = fields.Char(string='PNR', tracking=True, track_visibility='always')
    # From City/Airport Code: IATA code of the departure city or airport.
    from_city_airport_code = fields.Char(string='From', tracking=True, track_visibility='always')
    # To City/Airport Code: IATA code of the arrival city or airport.
    to_city_airport_code = fields.Char(string='To', tracking=True, track_visibility='always')
    # Operating Carrier Designator: IATA code of the airline that operates the flight.
    # operating_carrier_designator = fields.Char(string='Airline')
    operating_carrier_designator = fields.Many2one('airline', string='Airline', tracking=True, track_visibility='always')
    # Flight Number: Flight number of the flight.
    flight_number = fields.Char(string='Flight', tracking=True, track_visibility='always')
    # Date of Flight: Date of the flight in DDMM format.
    date_of_flight = fields.Char(string='Date', tracking=True, track_visibility='always')
    # Compartment Code: Class of service (F = First, J = Business, Y = Economy).
    compartment_code = fields.Char(string='Class', tracking=True, track_visibility='always')
    # Seat Number: Seat number of the passenger.
    seat_number = fields.Char(string='Seat', tracking=True, track_visibility='always')
    # Check-in Sequence Number: Sequence number of the passenger during check-in.
    check_in_sequence_number = fields.Char(string='SEQ', tracking=True, track_visibility='always')
    # Passenger Status: Status of the passenger (A = Adult, C = Child, I = Infant).
    passenger_status = fields.Char(string='Status', tracking=True, track_visibility='always')
    airline_passenger_bill_id = fields.Many2one('airline.passenger.bill', string='Airlines Passenger Bill', tracking=True, track_visibility='always')
    # Bar Code Raw Data: Raw data of the bar code.
    raw = fields.Char(string='Raw', tracking=True, track_visibility='always')
    invoice_id = fields.Many2one('account.move', string='Invoice', tracking=True, track_visibility='always')
    payment_state = fields.Selection([('not_paid', 'Not Paid'),
                                    ('in_payment', 'In Payment'),
                                    ('paid', 'Paid'),
                                    ('partial', 'Partially Paid'),
                                    ('reversed', 'Reversed'),
                                    ('invoicing_legacy', 'Invoicing App Legacy'),
                            ], String='State', related='invoice_id.payment_state')
    qr_code = fields.Binary("QR Code", compute='generate_qr_code')

    def generate_qr_code(self):
        for rec in self:
            if qrcode and base64:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=4,
                    border=4,
                )
                form_url = rec.invoice_id.name
                qr.add_data(form_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.update({'qr_code': qr_image})

    def action_print_slip(self):
        return self.env.ref('airline_passenger_bill.action_airline_passenger_bill_slip').report_action(self)

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

    def _generate_invoice(self):
        parent_customer = self.env['res.partner'].search([('id', '=', self.airline_passenger_bill_id.passenger_rate_id.default_partner.id)])
        partner = self.env['res.partner']
        if parent_customer:
            partner = partner.create({
                'name': self.passenger_name,
                'parent_id': parent_customer.id,
            })
        if self.passenger_name:
            invoice = self.env['account.move'].create({
                'partner_id': partner.id,
                'currency_id': self.airline_passenger_bill_id.passenger_rate_id.currency_id.id,
                'invoice_date': self.airline_passenger_bill_id.date,
                'invoice_origin': self.passenger_name,
                'journal_id': self.airline_passenger_bill_id.passenger_rate_id.journal_id.id,
                'narration': f'Flight: {self.from_city_airport_code}-{self.to_city_airport_code} {self.flight_number}',
                'move_type': 'out_invoice',
                'invoice_line_ids': [],  # Start with no lines
            })
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': self.airline_passenger_bill_id.passenger_rate_id.product_id.id,
                'quantity': 1,
                'name': f'{self.passenger_name}',
                'price_unit': self.airline_passenger_bill_id.passenger_rate_id.amount,
            })

            invoice.action_post()

            self.invoice_id = invoice.id
            self._create_invoice_download()

    def _create_invoice_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.invoice_id}/download',
            'target': 'self',
        }

    def action_register_payment(self):
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.invoice_id.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, vals):
        passenger_bills = super(AirlinePassengerBillLine, self).create(vals)
        for passenger_bill in passenger_bills:
            msg = f"Airline Passenger Bill Line created."
            passenger_bill.airline_passenger_bill_id.message_post(body=msg)
            return passenger_bills

    def write(self, vals):
        self._log_billing_tracking(vals)
        return super().write(vals)

    def _log_billing_tracking(self, vals):
        template_id = self.env.ref('airline_passenger_bill.airline_passenger_bill_line_template')
        changes = []

        if 'format_code' in vals:
            old_value = self.format_code or 'N/A'
            new_value = vals.get('format_code', 'N/A')
            changes.append(f"Format Code: {old_value} → {new_value}")

        if 'number_of_legs_encoded' in vals:
            old_value = self.number_of_legs_encoded or 0
            new_value = vals.get('number_of_legs_encoded', 0)
            changes.append(f"Number of Legs: {old_value} → {new_value}")

        if 'passenger_name' in vals:
            old_value = self.passenger_name or 'N/A'
            new_value = vals.get('passenger_name', 'N/A')
            changes.append(f"Passenger Name: {old_value} → {new_value}")

        if 'electronic_ticket_indicator' in vals:
            old_value = self.electronic_ticket_indicator or 'N/A'
            new_value = vals.get('electronic_ticket_indicator', 'N/A')
            changes.append(f"Electronic Ticket Indicator: {old_value} → {new_value}")

        if 'pnr_code' in vals:
            old_value = self.pnr_code or 'N/A'
            new_value = vals.get('pnr_code', 'N/A')
            changes.append(f"PNR Code: {old_value} → {new_value}")

        if 'from_city_airport_code' in vals:
            old_value = self.from_city_airport_code or 'N/A'
            new_value = vals.get('from_city_airport_code', 'N/A')
            changes.append(f"From City/Airport Code: {old_value} → {new_value}")

        if 'to_city_airport_code' in vals:
            old_value = self.to_city_airport_code or 'N/A'
            new_value = vals.get('to_city_airport_code', 'N/A')
            changes.append(f"To City/Airport Code: {old_value} → {new_value}")

        if 'operating_carrier_designator' in vals:
            old_value = self.operating_carrier_designator.name or 'N/A'
            new_value = self.env['airline'].browse(vals['operating_carrier_designator']).name if vals.get(
                'operating_carrier_designator') else 'N/A'
            changes.append(f"Operating Carrier Designator: {old_value} → {new_value}")

        if 'flight_number' in vals:
            old_value = self.flight_number or 'N/A'
            new_value = vals.get('flight_number', 'N/A')
            changes.append(f"Flight Number: {old_value} → {new_value}")

        if 'date_of_flight' in vals:
            old_value = self.date_of_flight or 'N/A'
            new_value = vals.get('date_of_flight', 'N/A')
            changes.append(f"Date of Flight: {old_value} → {new_value}")

        if 'compartment_code' in vals:
            old_value = self.compartment_code or 'N/A'
            new_value = vals.get('compartment_code', 'N/A')
            changes.append(f"Compartment Code: {old_value} → {new_value}")

        if 'seat_number' in vals:
            old_value = self.seat_number or 'N/A'
            new_value = vals.get('seat_number', 'N/A')
            changes.append(f"Seat Number: {old_value} → {new_value}")

        if 'check_in_sequence_number' in vals:
            old_value = self.check_in_sequence_number or 'N/A'
            new_value = vals.get('check_in_sequence_number', 'N/A')
            changes.append(f"Check-in Sequence Number: {old_value} → {new_value}")

        if 'passenger_status' in vals:
            old_value = self.passenger_status or 'N/A'
            new_value = vals.get('passenger_status', 'N/A')
            changes.append(f"Passenger Status: {old_value} → {new_value}")

        if 'raw' in vals:
            old_value = self.raw or 'N/A'
            new_value = vals.get('raw', 'N/A')
            changes.append(f"Raw Data: {old_value} → {new_value}")

        if 'invoice_id' in vals:
            old_value = self.invoice_id.name or 'N/A'
            new_value = self.env['account.move'].browse(vals['invoice_id']).name if vals.get('invoice_id') else 'N/A'
            changes.append(f"Invoice: {old_value} → {new_value}")

        if changes:
            rendered_message = self.env['ir.qweb']._render(
                template_id.id, {'changes': changes}
            )

            self.airline_passenger_bill_id.message_post(
                body=rendered_message,
                message_type='notification',
                subtype_xmlid="mail.mt_note"
            )