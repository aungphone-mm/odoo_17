from odoo import fields, models, api, _
from datetime import datetime


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
                                                      string='Passenger Details', track_visibility='always',
                                                      tracking=True)
    passenger_rate_id = fields.Many2one('passenger.rate', string='Passenger Rate', required=True, track_visibility='always',
                                        tracking=True)

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.passenger_rate_id = self.env['passenger.rate'].search([('from_date', '<=', self.date), ('to_date', '>=', self.date), ('active', '=', True)], limit=1).id

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


class PassengerRate(models.Model):
    _name = 'passenger.rate'
    _description = 'Passenger Rate'

    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char(string='Name', required=True)
    receivable_account_id = fields.Many2one(comodel_name='account.account', string='Receivable Account', required=True, track_visibility='always')
    from_date = fields.Date('From Date', default=fields.Date.context_today, required=True, track_visibility='always')
    to_date = fields.Date('To Date', default=fields.Date.context_today, required=True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, track_visibility='always')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, track_visibility='always')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True, track_visibility='always')
    default_partner = fields.Many2one(comodel_name='res.partner', string='Default Partner', track_visibility='always')
    active = fields.Boolean(string='Active', default=True, track_visibility='onchange')
