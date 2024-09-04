from odoo import fields, models



class LandingCheckInLine(models.Model):
    _name = 'landing.check.in.line'
    _description = 'Landing Check In Line'

    format_code = fields.Char(string='Format Code', required=True)
    number_of_legs_encoded = fields.Integer(string='Number of Legs Encoded', required=True)
    passenger_name = fields.Char(string='Passenger Name', required=True)
    electronic_ticket_indicator = fields.Char(string='Electronic Ticket Indicator', required=True)
    pnr_code = fields.Char(string='PNR Code', required=True)
    from_city_airport_code = fields.Char(string='From City/Airport Code', required=True)
    to_city_airport_code = fields.Char(string='To City/Airport Code', required=True)
    operating_carrier_designator = fields.Char(string='Operating Carrier Designator', required=True)
    flight_number = fields.Char(string='Flight Number', required=True)
    date_of_flight = fields.Char(string='Date of Flight', required=True)
    compartment_code = fields.Char(string='Compartment Code', required=True)
    seat_number = fields.Char(string='Seat Number', required=True)
    check_in_sequence_number = fields.Char(string='Check-in Sequence Number', required=True)
    passenger_status = fields.Char(string='Passenger Status', required=True)
    landing_check_in_id = fields.Many2one('landing.check.in', string='Landing Check In')
    raw = fields.Char(string='Bar Code Raw Data', required=True)