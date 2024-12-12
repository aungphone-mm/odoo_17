from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PassengerServiceLine(models.Model):
    _name = 'passenger.service.line'
    _description = 'Passenger Service Line'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    passenger_service_id = fields.Many2one('passenger.service', string='Passenger Service', tracking=True)
    flightno_id = fields.Char(string='Flight No.')
    flight_registration_no = fields.Char(string='Registration No.')
    flight_aircraft = fields.Char(string='Aircraft Type')
    start_time = fields.Datetime(string='Start Date & Time', default=fields.Datetime.now, tracking=True)
    # end_time = fields.Datetime(string='End Date & Time', tracking=True)
    # total_minutes = fields.Integer(string='Total Minutes', compute='_compute_total_minutes', store=True)
    passenger_service_rate_id = fields.Many2one('passenger.service.rate', string='Rate',
                                       compute='_compute_passenger_service_rate',
                                       inverse='_inverse_passenger_service_rate',
                                       store=True, tracking=True)
    # amount = fields.Float(string="Amount", compute='_compute_amount', store=True)
    total_pax = fields.Integer(string='Total Pax', tracking=True)
    osc = fields.Integer(string='O.S.C', tracking=True)
    inf = fields.Integer(string='INF', tracking=True)
    transit = fields.Integer(string='Transit', tracking=True)
    ntl = fields.Integer(string='NTL', tracking=True)
    inad = fields.Integer(string='INAD', tracking=True)
    depor = fields.Integer(string='Depor', tracking=True)
    tax_free = fields.Integer(string='Tax Free', tracking=True)
    invoice_pax = fields.Integer(string='Invoice Pax', compute='_compute_invoice_pax', store=True)

    @api.depends('total_pax', 'inf', 'transit', 'ntl', 'inad', 'depor', 'tax_free')
    def _compute_invoice_pax(self):
        for record in self:
            deductions = sum([
                record.inf or 0,
                record.transit or 0,
                record.ntl or 0,
                record.inad or 0,
                record.depor or 0,
                record.tax_free or 0
            ])
            record.invoice_pax = record.total_pax - deductions

    @api.depends('passenger_service_id.passenger_service_rate_id')
    def _compute_passenger_service_rate(self):
        for line in self:
            line.passenger_service_rate_id = line.passenger_service_id.passenger_service_rate_id

    def _inverse_passenger_service_rate(self):
        for line in self:
            if line.passenger_service_rate_id != line.passenger_service_id.passenger_service_rate_id:
                # You can add any necessary logic here when the rate changes
                pass

    @api.constrains('flightno_id')
    def _passenger_service_service(self):
        for record in self:
            if not record.flightno_id:
                raise ValidationError(_("Flight No. must be set for each PassengerService line."))

    # #aungphone
    # @api.depends('start_time', 'end_time')
    # def _compute_total_minutes(self):
    #     for record in self:
    #         if record.start_time and record.end_time:
    #             duration = record.end_time - record.start_time
    #             record.total_minutes = int(duration.total_seconds() / 60)
    #         else:
    #             record.total_minutes = 0
    #
    # @api.depends('total_minutes', 'passenger_service_rate_id')
    # def _compute_amount(self):
    #     for record in self:
    #         amount = 0
    #         if record.passenger_service_rate_id and record.total_minutes:
    #             rate_lines = record.passenger_service_rate_id.passenger_service_rate_line_ids.sorted(key=lambda r: r.from_unit)
    #             max_rate_line = rate_lines[-1] if rate_lines else None
    #             for rate_line in rate_lines:
    #                 if not rate_line.to_unit or record.total_minutes <= rate_line.to_unit:
    #                     amount = rate_line.unit_price
    #                     break
    #             else:
    #                 # If no suitable range is found, use the maximum unit price
    #                 if max_rate_line:
    #                     amount = max_rate_line.unit_price
    #                 else:
    #                     raise ValidationError(f"No rates defined for PassengerService rate {record.passenger_service_rate_id.name}")
    #         record.amount = amount
    #
    # @api.onchange('total_minutes', 'passenger_service_rate_id')
    # def _onchange_rate_details(self):
    #     self._compute_amount()
    #     if self.passenger_service_rate_id and self.total_minutes:
    #         rate_lines = self.passenger_service_rate_id.passenger_service_rate_line_ids.sorted(key=lambda r: r.from_unit)
    #         max_rate_line = rate_lines[-1] if rate_lines else None
    #         if max_rate_line and self.total_minutes > max_rate_line.to_unit:
    #             return {
    #                 'warning': {
    #                     'title': "Maximum Rate Used",
    #                     'message': f"Using maximum rate {self.amount} for {self.total_minutes} minutes"
    #                 }
    #             }

    # @api.model
    # def create(self, vals):
    #     passenger_lines = super(PassengerServiceLine, self).create(vals)
    #     for passenger_line in passenger_lines:
    #         passenger_line._log_tracking(vals)
    #         return passenger_lines
    #
    # def _log_tracking(self, vals):
    #     template_id = self.env.ref('passenger_service_charges.airline_passenger_service_line_template')
    #     changes = []
    #
    #     if 'flightno_id' in vals:
    #         flight = self.env['flights'].browse(vals['flightno_id'])
    #         changes.append(f"Flight Number: → {flight.name}")
    #         changes.append(f"Flight Registration No: → {flight.name or 'N/A'}")
    #
    #     if 'start_time' in vals:
    #         new_value = vals.get('start_time', 'N/A')
    #         changes.append(f"Start Time:  → {new_value}")
    #
    #     if 'end_time' in vals:
    #         new_value = vals.get('end_time', 'N/A')
    #         changes.append(f"End Time:  → {new_value}")
    #
    #     if 'start_time' in vals or 'end_time' in vals:
    #         self._compute_total_minutes()
    #         changes.append(f"Total Minutes: → {self.total_minutes}")
    #
    #     if 'passenger_service_rate_id' in vals:
    #         bridge_rate = self.env['passenger.landing.rate'].browse(vals['passenger_service_rate_id'])
    #         new_value = bridge_rate.name  # or whatever field contains the rate name
    #         changes.append(f"Service Rate: → {new_value}")
    #
    #     if changes:
    #         rendered_message = self.env['ir.qweb']._render(
    #             template_id.id, {'changes': changes}
    #         )
    #
    #         self.passenger_service_id.message_post(
    #             body=rendered_message,
    #             message_type='notification',
    #             subtype_xmlid="mail.mt_note"
    #         )
