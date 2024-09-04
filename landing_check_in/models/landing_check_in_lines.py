from odoo import fields, models



class LandingCheckInLine(models.Model):
    _name = 'landing.check.in.line'
    _description = 'Landing Check In Line'

    format_code = fields.Char(string='Format Code')
    number_of_legs_encoded = fields.Integer(string='Number of Legs Encoded')
    passenger_name = fields.Char(string='Passenger Name')
    electronic_ticket_indicator = fields.Char(string='Electronic Ticket Indicator')
    pnr_code = fields.Char(string='PNR Code')
    from_city_airport_code = fields.Char(string='From City/Airport Code')
    to_city_airport_code = fields.Char(string='To City/Airport Code')
    operating_carrier_designator = fields.Char(string='Operating Carrier Designator')
    flight_number = fields.Char(string='Flight Number')
    date_of_flight = fields.Char(string='Date of Flight')
    compartment_code = fields.Char(string='Compartment Code')
    seat_number = fields.Char(string='Seat Number')
    check_in_sequence_number = fields.Char(string='Check-in Sequence Number')
    passenger_status = fields.Char(string='Passenger Status')
    landing_check_in_id = fields.Many2one('landing.check.in', string='Landing Check In')
    raw = fields.Char(string='Bar Code Raw Data')