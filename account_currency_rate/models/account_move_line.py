from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    currency_rate_display = fields.Float(string="Exchange Rate")

    @api.depends('currency_id', 'company_id', 'move_id.date','move_id.currency_rate')
    def _compute_currency_rate(self):
        for line in self:
            if line.move_id.company_currency_id != line.move_id.currency_id and line.move_id.currency_rate > 0:
                line.currency_rate = 1.0 / line.move_id.currency_rate
                line.currency_rate_display = line.move_id.currency_rate
            else:
                if line.currency_id:
                    line.currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=line.company_currency_id,
                        to_currency=line.currency_id,
                        company=line.company_id,
                        date=line._get_rate_date(),
                    )
                    line.currency_rate_display = 1.0 / line.currency_rate
                else:
                    line.currency_rate = 1.0

    @api.onchange('move_id.currency_rate')
    def _onchange_move_currency_rate(self):
        """Update currency_rate_display when the header currency rate changes"""
        for line in self:
            if line.move_id.company_currency_id != line.move_id.currency_id and line.move_id.currency_rate > 0:
                line.currency_rate = 1.0 / line.move_id.currency_rate
                line.currency_rate_display = line.move_id.currency_rate

                # Recalculate debit/credit based on amount_currency
                if line.amount_currency:
                    company_amount = abs(line.amount_currency) * line.currency_rate_display
                    if line.amount_currency > 0:
                        line.debit = company_amount
                        line.credit = 0.0
                    else:
                        line.credit = company_amount
                        line.debit = 0.0

    @api.onchange('debit', 'credit')
    def _onchange_debit_credit(self):
        """Update amount_currency with proper sign when debit/credit changes"""
        for line in self:
            if not line.currency_id or not line.currency_rate_display:
                continue

            # If debit was entered
            if line.debit > 0:
                line.amount_currency = abs(line.debit) / line.currency_rate_display

            # If credit was entered
            elif line.credit > 0:
                line.amount_currency = -abs(line.credit) / line.currency_rate_display

    @api.onchange('currency_rate_display', 'amount_currency')
    def _onchange_currency_rate_display(self):
        """Automatically calculate debit/credit when exchange rate or amount_currency change"""
        for line in self:
            if not line.currency_id or not line.currency_rate_display:
                continue

            if line.amount_currency:
                # Calculate the amount in company currency
                company_amount = abs(line.amount_currency) * line.currency_rate_display

                # Update debit or credit based on the sign of amount_currency
                if line.amount_currency > 0:
                    line.debit = company_amount
                    line.credit = 0.0
                else:
                    line.credit = company_amount
                    line.debit = 0.0

    @api.model
    def default_get(self, fields_list):
        # Inherit default_get to set currency based on other lines
        result = super(AccountMoveLine, self).default_get(fields_list)

        # Check if we're creating a line in context of a move
        if self._context.get('default_move_id'):
            move_id = self._context.get('default_move_id')
            move = self.env['account.move'].browse(move_id)

            # If move has existing lines with currency, use that currency
            existing_lines = move.line_ids.filtered(lambda l: l.currency_id)
            if existing_lines:
                result['currency_id'] = existing_lines[0].currency_id.id

        return result

    @api.onchange('move_id')
    def _onchange_move_id(self):
        # When a line is added, check if other lines have currency
        if self.move_id:
            other_lines = self.move_id.line_ids.filtered(lambda l: l.id != self.id and l.currency_id)
            if other_lines:
                self.currency_id = other_lines[0].currency_id

    def _get_rate_date(self):
        self.ensure_one()
        return self.move_id.invoice_date or self.move_id.date or fields.Date.context_today(self)