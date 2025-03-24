from odoo import api, fields, models

class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    # Change date to datetime field
    name = fields.Datetime(
        string='Date & Time',
        required=True,
        index=True,
        default=fields.Datetime.now,
        help="Timestamp when this rate is effective"
    )

    _sql_constraints = [
        ('unique_name_per_currency_company',
         'unique (name,currency_id,company_id)',
         'Only one currency rate per datetime, currency and company allowed!')
    ]