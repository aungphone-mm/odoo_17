from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    manual_exchange_rate = fields.Float(string="Manual Exchange Rate", digits=(12, 6))
    show_manual_exchange_rate = fields.Boolean(compute='_compute_show_manual_exchange_rate')
    manual_rate_id = fields.Many2one('res.currency.rate', string="Manual Rate Record",
                                     help="Technical field to track created exchange rate record")

    @api.depends('currency_id', 'company_id')
    def _compute_show_manual_exchange_rate(self):
        for wizard in self:
            # Only show the field if currency differs from company currency
            wizard.show_manual_exchange_rate = wizard.currency_id != wizard.company_id.currency_id

    def action_apply_manual_rate(self):
        self.ensure_one()
        if not self.manual_exchange_rate or self.manual_exchange_rate <= 0:
            raise UserError(_("Please enter a valid exchange rate greater than zero."))

        # Get the current date or use the accounting date if set
        rate_date = self.payment_date or fields.Date.context_today(self)

        # Check if a rate already exists for this date
        existing_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.currency_id.id),
            ('company_id', '=', self.company_id.id),
            ('name', '=', rate_date),
        ], limit=1)

        # Calculate the rate value (Odoo stores the inverse rate)
        rate_value = 1.0 / self.manual_exchange_rate

        if existing_rate:
            # Update existing rate
            existing_rate.write({
                'rate': rate_value,
            })
            self.manual_rate_id = existing_rate.id
        else:
            # Create new rate
            new_rate = self.env['res.currency.rate'].create({
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'name': rate_date,
                'rate': rate_value,
            })
            self.manual_rate_id = new_rate.id

        # Refresh the wizard to reflect the new rate
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }

    def _create_payments(self):
        # Call the original method to create payments
        payments = super()._create_payments()

        # After creating payments, remove the manual rate if it was set
        if self.manual_rate_id:
            try:
                self.manual_rate_id.sudo().unlink()
            except Exception as e:
                # Log the error but don't interrupt the flow
                _logger.error("Failed to delete manual exchange rate: %s", str(e))

        return payments