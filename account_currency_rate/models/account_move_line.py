from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    currency_rate = fields.Float(string="Exchange Rate", compute='_compute_currency_rate', store=True)

    @api.depends('currency_id', 'move_id.date')
    def _compute_currency_rate(self):
        for line in self:
            # Ensure the line has a currency_id
            if line.currency_id:
                # Find the rate from res.currency.rate based on the currency_id and the date
                rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', line.currency_id.id),
                    ('name', '=', line.move_id.date)], limit=1)

                if rate:
                    line.currency_rate = rate.rate
                else:
                    # If no rate found, you can raise an error or default to 1.0
                    line.currency_rate = 1.0
            else:
                line.currency_rate = 1.0


