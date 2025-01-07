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
    flight_registration_no = fields.Many2one('passenger.landing.rate.line',
                                           string='Registration No.',
                                           domain="[('rate_id', '=', parent.passenger_landing_rate_id)]")
    flight_aircraft = fields.Many2one('passenger.landing.rate.line',
                                      string='Aircraft Type',
                                      domain="[('id', '=', flight_registration_no.id)]")
    aircraft_type_display = fields.Char(related='flight_aircraft.aircraft_type', string='Aircraft Type')
    start_time = fields.Datetime(string='Start Date & Time', tracking=True, default=fields.Datetime.now)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)
    route = fields.Char(string='Route')
    serial_number = fields.Integer(string='S/N', compute='_compute_serial_number', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    airline_id = fields.Many2one('airline', string='Airline', tracking=True)

    @api.depends('passenger_landing_id.passenger_landing_line_ids', 'passenger_landing_id.passenger_landing_line_ids.sequence')
    def _compute_serial_number(self):
        for parent in self.mapped('passenger_landing_id'):
            sequence = 1
            for line in parent.passenger_landing_line_ids.sorted('sequence'):
                line.serial_number = sequence
                sequence += 1

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
            else:
                record.amount = 0.0