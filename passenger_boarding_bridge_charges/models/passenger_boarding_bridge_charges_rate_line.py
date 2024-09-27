from odoo import fields, models, api, _

class PassengerBoardingBridgeChargesRateLine(models.Model):
    _name = 'passenger.boarding.bridge.charges.rate.line'
    _description = 'Passenger Boarding Bridge Charges Rate Line'

    from_unit = fields.Integer(string='From', required=True)
    to_unit = fields.Integer(string='To')
    unit_price = fields.Float(string='Unit Price', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='rate_id.currency_id',
        store=True,
        readonly=True
    )
    rate_id = fields.Many2one(comodel_name='passenger.boarding.bridge.charges.rate', string='Rate', required=True)
