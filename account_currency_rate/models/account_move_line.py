from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    currency_rate_display = fields.Float(string="Exchange Rate")

    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        for line in self:
            if line.move_id.company_currency_id != line.move_id.currency_id and line.move_id.currency_rate > 0:
                line.currency_rate = 1.0/line.move_id.currency_rate
                line.currency_rate_display = line.move_id.currency_rate
            else:
                if line.currency_id:
                    line.currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=line.company_currency_id,
                        to_currency=line.currency_id,
                        company=line.company_id,
                        date=line._get_rate_date(),
                    )
                    line.currency_rate_display = 1.0/line.currency_rate
                else:
                    line.currency_rate = 1.0

    def _get_rate_date(self):
        self.ensure_one()
        return self.move_id.invoice_date or self.move_id.date or fields.Date.context_today(self)


