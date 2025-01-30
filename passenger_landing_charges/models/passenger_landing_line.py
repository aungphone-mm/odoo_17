import math
from odoo import fields, models, api, _

class PassengerLandingLine(models.Model):
    _name = 'passenger.landing.line'
    _description = 'Passenger Landing Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'sequence, id'

    passenger_landing_id = fields.Many2one('passenger.landing', string='Aircraft Landing',
                                         tracking=True, index=True)
    # passenger_landing_rate_id = fields.Many2one('passenger.landing.rate',string='Landing Rate')
    passenger_landing_rate_id = fields.Many2one('passenger.landing.rate', string='Rate',
                                              compute='_compute_landing_rate',
                                              inverse='_inverse_landing_rate',
                                              store=True, tracking=True)
    flight_no = fields.Char(string='Flight No', required=True)
    # flight_registration_no = fields.Many2one('passenger.landing.rate.line',
    #                                        string='Registration No.',
    #                                        domain="[('rate_id', '=', parent.passenger_landing_rate_id)]")
    flight_registration_no = fields.Many2one('passenger.landing.rate.line',
                                             string='Registration No.')
    flight_aircraft = fields.Many2one('passenger.landing.rate.line',
                                      string='Aircraft Type',
                                      domain="[('id', '=', flight_registration_no.id)]")
    aircraft_type_display = fields.Char(related='flight_aircraft.aircraft_type', string='Aircraft Type')
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Date & Time', tracking=True, default=fields.Datetime.now)
    amount = fields.Float(string="Landing Amount", compute='_compute_amount', store=True)
    parking_amount = fields.Float(string="Parking Amount", compute='_compute_parking_amount', store=True)
    route = fields.Char(string='Route')
    serial_number = fields.Integer(string='S/N', compute='_compute_serial_number', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    airline_id = fields.Many2one('airline', string='Airline')
    parking_rate = fields.Float(string='Parking Rate', required=True, tracking=True)

    @api.depends('passenger_landing_id.passenger_landing_line_ids', 'passenger_landing_id.passenger_landing_line_ids.sequence')
    def _compute_serial_number(self):
        for parent in self.mapped('passenger_landing_id'):
            sequence = 1
            for line in parent.passenger_landing_line_ids.sorted('sequence'):
                line.serial_number = sequence
                sequence += 1

    # Auto-set flight_aircraft based on registration
    @api.onchange('flight_registration_no')
    def _onchange_flight_registration(self):
        if self.flight_registration_no:
            self.flight_aircraft = self.flight_registration_no

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('flight_registration_no') and not vals.get('flight_aircraft'):
                vals['flight_aircraft'] = vals['flight_registration_no']
        return super().create(vals_list)

    @api.depends('passenger_landing_id.passenger_landing_rate_id')
    def _compute_landing_rate(self):
        for line in self:
            line.passenger_landing_rate_id = line.passenger_landing_id.passenger_landing_rate_id

    def _inverse_landing_rate(self):
        for line in self:
            if line.passenger_landing_rate_id != line.passenger_landing_id.passenger_landing_rate_id:
                # You can add any necessary logic here when the rate changes
                pass

    @api.onchange('flight_registration_no')
    def _onchange_flight_registration_no(self):
        for record in self:
            record.flight_aircraft = record.flight_registration_no

    @api.depends('flight_aircraft', 'start_time')
    def _compute_amount(self):
        for record in self:
            if record.flight_aircraft:
                record.amount = record.flight_aircraft.unit_price
                record.parking_rate = record.flight_aircraft.parking_rate
            else:
                record.amount = 0.0

    @api.depends('flight_aircraft', 'start_time', 'end_time', 'parking_rate')
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
            record.parking_amount = days * record.parking_rate