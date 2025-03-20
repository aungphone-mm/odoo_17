# models/account_payment_register.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # Add custom exchange rate field with better defaults and constraints
    custom_exchange_rate = fields.Float(
        string='Custom Exchange Rate',
        default=0.0,
        digits=(16, 4),
        help='Set your own exchange rate from USD to MMK'
    )
    use_custom_exchange_rate = fields.Boolean(
        string='Use Custom Exchange Rate',
        default=False
    )
    source_amount = fields.Monetary(
        string='Source Amount in USD',
        store=True,
        readonly=False
    )
    exchange_amount_preview = fields.Monetary(
        string='Calculated MMK Amount',
        compute='_compute_exchange_amount_preview',
        store=False,
        readonly=True,
        help='Preview of the payment amount after applying custom exchange rate'
    )
    show_custom_rate = fields.Boolean(
        string='Show Custom Rate',
        compute='_compute_show_custom_rate',
        help='Technical field to control visibility of custom rate fields'
    )

    @api.depends('source_currency_id', 'currency_id')
    def _compute_show_custom_rate(self):
        """Determine if custom rate fields should be shown"""
        for record in self:
            record.show_custom_rate = (
                    record.source_currency_id.name == 'USD' and
                    record.currency_id.name == 'MMK'
            )
            # Reset fields when not applicable
            if not record.show_custom_rate:
                record.use_custom_exchange_rate = False
                record.custom_exchange_rate = 0.0

    @api.depends('source_amount', 'custom_exchange_rate', 'use_custom_exchange_rate')
    def _compute_exchange_amount_preview(self):
        """Compute preview amount without changing actual amount"""
        for record in self:
            if (record.use_custom_exchange_rate and
                    record.custom_exchange_rate > 0 and
                    record.source_amount > 0):
                record.exchange_amount_preview = record.source_amount * record.custom_exchange_rate
                _logger.info(
                    f"Preview calculation: {record.source_amount} USD * {record.custom_exchange_rate} = {record.exchange_amount_preview} MMK")
            else:
                record.exchange_amount_preview = 0.0

    @api.onchange('amount', 'source_currency_id', 'currency_id')
    def _onchange_store_source_amount(self):
        """Store the original amount in source currency when it changes"""
        for record in self:
            _logger.info(f"Source amount onchange - Amount: {record.amount}, Currency: {record.currency_id.name}")

            if record.source_currency_id and record.source_currency_id.name == 'USD':
                # For USD source currency, correctly identify the amount
                if record.line_ids:
                    # Calculate from invoice lines
                    record.source_amount = sum(line.amount_residual_currency for line in record.line_ids)
                    _logger.info(f"Set source_amount from line_ids: {record.source_amount}")
                elif not record.source_amount or record.source_amount == 0:
                    # If direct amount entry, use the current amount
                    if record.currency_id.name == 'USD':
                        record.source_amount = record.amount
                        _logger.info(f"Set source_amount from amount field: {record.source_amount}")

                # When currency changed to MMK, update default exchange rate
                if record.currency_id.name == 'MMK' and (
                        not record.custom_exchange_rate or record.custom_exchange_rate == 0):
                    self._get_default_exchange_rate()

    @api.onchange('use_custom_exchange_rate')
    def _onchange_use_custom_exchange(self):
        """When custom exchange rate is enabled, update amount"""
        for record in self:
            if record.use_custom_exchange_rate:
                # Get default rate if not set
                if not record.custom_exchange_rate or record.custom_exchange_rate == 0:
                    self._get_default_exchange_rate()
                # Apply the rate
                self._apply_custom_rate()
            else:
                # Revert to standard conversion if custom rate disabled
                self._revert_to_standard_rate()

    @api.onchange('custom_exchange_rate')
    def _onchange_custom_exchange_rate(self):
        """Apply custom exchange rate when it changes"""
        for record in self:
            _logger.info(f"Custom rate changed to: {record.custom_exchange_rate}")

            # Only proceed for USD to MMK conversion
            if not (record.source_currency_id.name == 'USD' and record.currency_id.name == 'MMK'):
                return

            # Enable custom rate checkbox automatically if rate is entered
            if record.custom_exchange_rate > 0:
                record.use_custom_exchange_rate = True

            # Apply the rate to update amount
            self._apply_custom_rate()

    def _get_default_exchange_rate(self):
        """Get the default exchange rate from the system"""
        self.ensure_one()
        if self.source_currency_id.name == 'USD' and self.currency_id.name == 'MMK':
            try:
                company = self.company_id or self.env.company
                date = self.payment_date or fields.Date.context_today(self)

                # Get conversion rate from the currency's method
                rate = self.env['res.currency']._get_conversion_rate(
                    self.source_currency_id, self.currency_id, company, date)

                self.custom_exchange_rate = rate
                _logger.info(f"Got default exchange rate: {rate}")
            except Exception as e:
                _logger.error(f"Error getting default rate: {e}")
                self.custom_exchange_rate = 0.0

    def _apply_custom_rate(self):
        """Apply the custom exchange rate to update the amount"""
        self.ensure_one()

        # Validate required data
        if not (self.source_currency_id.name == 'USD' and self.currency_id.name == 'MMK'):
            return

        if not self.use_custom_exchange_rate or self.custom_exchange_rate <= 0:
            return

        # Ensure we have the correct source amount
        if not self.source_amount or self.source_amount == 0:
            if self.line_ids:
                self.source_amount = sum(line.amount_residual_currency for line in self.line_ids)
            elif self.payment_type == 'inbound':
                # For direct payments, try to get amount from context or current value
                context_amount = self.env.context.get('default_amount')
                if context_amount:
                    self.source_amount = context_amount

        # Only update if we have valid data
        if self.source_amount and self.source_amount > 0:
            old_amount = self.amount
            new_amount = self.source_amount * self.custom_exchange_rate
            self.amount = new_amount

            _logger.info(
                f"Applied custom rate: {self.source_amount} USD * {self.custom_exchange_rate} = {new_amount} MMK (old: {old_amount})")

    def _revert_to_standard_rate(self):
        """Revert to standard exchange rate calculation"""
        self.ensure_one()
        if self.source_currency_id.name == 'USD' and self.currency_id.name == 'MMK' and self.source_amount:
            try:
                company = self.company_id or self.env.company
                date = self.payment_date or fields.Date.context_today(self)

                # Get standard conversion rate
                rate = self.env['res.currency']._get_conversion_rate(
                    self.source_currency_id, self.currency_id, company, date)

                # Apply standard rate
                self.amount = self.source_amount * rate
                _logger.info(f"Reverted to standard rate: {self.source_amount} USD * {rate} = {self.amount} MMK")
            except Exception as e:
                _logger.error(f"Error reverting to standard rate: {e}")

    def apply_custom_rate_button(self):
        """Button method to explicitly apply custom rate"""
        self.ensure_one()
        self._apply_custom_rate()
        # Return None instead of 'ir.actions.do_nothing' which doesn't exist in Odoo 17
        return None

    def _create_payment_vals_from_wizard(self, batch_result):
        """Override payment values creation to apply custom exchange rate"""
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)

        if self.use_custom_exchange_rate and self.custom_exchange_rate > 0:
            if self.currency_id.name == 'MMK' and self.source_currency_id.name == 'USD':
                # Make sure we have the correct source amount
                source_amount = self.source_amount or sum(line.amount_residual_currency for line in self.line_ids)

                # Double-check the amount calculation
                calculated_amount = source_amount * self.custom_exchange_rate

                # Override the exchange rate in payment creation
                payment_vals.update({
                    'amount': calculated_amount,
                    'custom_exchange_rate': self.custom_exchange_rate,  # Store the used rate
                })

                # Log the values for debugging
                _logger.info(
                    f"Payment creation values: Source {source_amount} USD, Rate {self.custom_exchange_rate}, Final {payment_vals['amount']} MMK")

        return payment_vals

    def action_create_payments(self):
        """Override to handle case when Exchange Journal is not configured"""
        try:
            # Final check to ensure amount is correctly set with custom rate
            if (self.use_custom_exchange_rate and
                    self.custom_exchange_rate > 0 and
                    self.source_amount > 0 and
                    self.currency_id.name == 'MMK' and
                    self.source_currency_id.name == 'USD'):
                # Force correct amount before payment creation
                self.amount = self.source_amount * self.custom_exchange_rate

            # Try the standard payment creation process
            return super(AccountPaymentRegister, self).action_create_payments()
        except Exception as e:
            # Check if it's the Exchange Journal error
            if "Exchange Gain or Loss Journal" in str(e):
                # Provide a more user-friendly message with instructions
                raise UserError(_(
                    "You need to configure the Exchange Gain or Loss Journal before creating payments with custom exchange rates.\n\n"
                    "To fix this:\n"
                    "1. Go to Accounting → Configuration → Settings\n"
                    "2. Default Accounts -> Post Exchange difference entries in: \n"
                    "3. Journal Gain Loss ထည့်ပါ \n"
                    "4. Save your settings\n\n"
                    "Original error: %s") % str(e)
                                )
            else:
                # Re-raise the original exception if it's not about the Exchange Journal
                raise

    def open_rate_wizard(self):
        """Open a wizard to calculate rates with options"""
        self.ensure_one()

        return {
            'name': 'Exchange Rate Calculator',
            'type': 'ir.actions.act_window',
            'res_model': 'exchange.rate.calculator',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_currency_from': self.source_currency_id.id,
                'default_currency_to': self.currency_id.id,
                'default_amount': self.source_amount,
                'default_current_rate': self.custom_exchange_rate,
            }
        }

    def save_as_favorite_rate(self):
        """Save current rate as favorite for future use"""
        self.ensure_one()

        self.env['favorite.exchange.rate'].create({
            'name': f"USD to MMK on {fields.Date.today()}",
            'currency_from': self.source_currency_id.id,
            'currency_to': self.currency_id.id,
            'rate': self.custom_exchange_rate,
            'user_id': self.env.user.id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Rate saved to favorites: 1 USD = {self.custom_exchange_rate} MMK",
                'type': 'success',
                'sticky': False,
            }
        }

    def view_rate_history(self):
        """View the history of exchange rates"""
        self.ensure_one()

        return {
            'name': 'Exchange Rate History',
            'type': 'ir.actions.act_window',
            'res_model': 'exchange.rate.history',
            'view_mode': 'graph,tree,form',
            'domain': [
                ('currency_from.name', '=', 'USD'),
                ('currency_to.name', '=', 'MMK'),
            ],
            'context': {'create': False}
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Add the custom exchange rate field to the payment model
    custom_exchange_rate = fields.Float(
        string='Custom Exchange Rate',
        readonly=True,
        digits=(16, 4),
        help='Custom exchange rate used when creating this payment'
    )