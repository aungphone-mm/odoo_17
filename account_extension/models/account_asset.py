from dateutil.relativedelta import relativedelta
from docutils.utils import math
from odoo import api, fields, models

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    # Existing fields
    asset_category = fields.Many2one('account.asset.category', string='Asset Category')
    per_depreciation_amount = fields.Float(string='Per Depreciation Amount')
    dep_ref = fields.Char(string='Reference')
    dep_rate = fields.Char(string='Depreciation Rate %')
    remark = fields.Char(string='Remark')

    # Currency fields
    asset_currency = fields.Selection([
        ('MMK', 'MMK'),
        ('USD', 'USD')
    ], string='Asset Currency', default='MMK')

    original_value_usd = fields.Float(
        string='Original Value (USD)',
        compute='_compute_usd_amounts',
        store=True
    )

    exchange_rate = fields.Float(
        string='Exchange Rate (USD)',
        default=1.0,
        help='Exchange rate for converting MMK to USD'
    )

    # Computed USD fields
    per_depreciation_amount_usd = fields.Float(
        string='Per Depreciation Amount (USD)',
        compute='_compute_usd_amounts',
        store=True
    )

    book_value_usd = fields.Float(
        string='Book Value (USD)',
        compute='_compute_usd_amounts',
        store=True
    )
    depreciation_usd = fields.Float(
        string='Depreciation (USD)',
        compute='_compute_board_values_usd',
        store=True
    )
    cumulative_depreciation_usd = fields.Float(
        string='Cumulative Depreciation (USD)',
        compute='_compute_board_values_usd',
        store=True
    )
    depreciable_value_usd = fields.Float(
        string='Depreciable Value (USD)',
        compute='_compute_board_values_usd',
        store=True
    )
    depreciated_amount_usd = fields.Float(
        string='Depreciated Amount (USD)',
        compute='_compute_depreciated_amount_usd',
        store=True
    )

    @api.depends('cumulative_depreciation_usd')
    def _compute_depreciated_amount_usd(self):
        for asset in self:
            asset.depreciated_amount_usd = asset.cumulative_depreciation_usd

    @api.depends('original_value', 'book_value', 'exchange_rate', 'asset_currency')
    def _compute_board_values_usd(self):
        for asset in self:
            if asset.asset_currency == 'USD' and asset.exchange_rate:
                asset.depreciation_usd = asset.original_value / asset.exchange_rate
                asset.cumulative_depreciation_usd = (asset.original_value - asset.book_value) / asset.exchange_rate
                asset.depreciable_value_usd = asset.book_value / asset.exchange_rate
            else:
                asset.depreciation_usd = 0.0
                asset.cumulative_depreciation_usd = 0.0
                asset.depreciable_value_usd = 0.0

    @api.depends('original_value', 'per_depreciation_amount', 'book_value', 'exchange_rate', 'asset_currency')
    def _compute_usd_amounts(self):
        for asset in self:
            if asset.asset_currency == 'USD' and asset.exchange_rate:
                # Convert MMK to USD by dividing by exchange rate
                asset.original_value_usd = asset.original_value / asset.exchange_rate
                asset.per_depreciation_amount_usd = asset.per_depreciation_amount / asset.exchange_rate
                asset.book_value_usd = asset.book_value / asset.exchange_rate
            else:
                asset.original_value_usd = 0.0
                asset.per_depreciation_amount_usd = 0.0
                asset.book_value_usd = 0.0

    def compute_depreciation_board(self):
        self.ensure_one()

        if self.per_depreciation_amount > 0 and self.prorata_date:
            self.depreciation_move_ids.filtered(lambda x: x.state == 'draft').unlink()

            # Use USD amounts if currency is USD
            if self.asset_currency == 'USD' and self.exchange_rate:
                remaining_value = self.book_value_usd
                depreciation_amount = self.per_depreciation_amount_usd
            else:
                remaining_value = self.book_value
                depreciation_amount = self.per_depreciation_amount

            number_of_periods = math.ceil(remaining_value / depreciation_amount)
            commands = []
            base_date = self.prorata_date + relativedelta(day=31)

            for i in range(number_of_periods):
                depreciation_date = base_date + relativedelta(months=i, day=31)

                if i == number_of_periods - 1:
                    current_depreciation = remaining_value
                else:
                    current_depreciation = min(depreciation_amount, remaining_value)

                # Convert amount to MMK if using USD
                move_amount = current_depreciation
                if self.asset_currency == 'USD':
                    move_amount = current_depreciation * self.exchange_rate

                vals = {
                    'asset_id': self.id,
                    'amount_total': move_amount,
                    'date': depreciation_date,
                    'ref': f'{self.name}: Depreciation ({self.asset_currency})',
                    'move_type': 'entry',
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': [
                        (0, 0, {
                            'name': f'{self.name}: Depreciation',
                            'debit': move_amount,
                            'account_id': self.account_depreciation_expense_id.id,
                        }),
                        (0, 0, {
                            'name': f'{self.name}: Depreciation',
                            'credit': move_amount,
                            'account_id': self.account_depreciation_id.id,
                        })
                    ]
                }

                move = self.env['account.move'].create(vals)
                move.write({'auto_post': 'at_date'})
                commands.append((4, move.id))

                remaining_value -= current_depreciation
                if remaining_value <= 0:
                    break

            self.write({'depreciation_move_ids': commands})
            return True

        return super(AccountAsset, self).compute_depreciation_board()

    @api.onchange('asset_currency')
    def _onchange_asset_currency(self):
        if self.asset_currency == 'MMK':
            self.exchange_rate = 1.0

class AccountAssetCategory(models.Model):

    _name = 'account.asset.category'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    description = fields.Text(string='Description', help='Additional payment details')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    description = fields.Text(string='Description', help='Additional payment details')

    # Transfer the description to the created payment
    @api.depends('description')
    def _create_payments(self):
        payments = super()._create_payments()
        for payment in payments:
            payment.description = self.description

            # Update the ref_desc in related move lines
            if payment.move_id:
                payment.move_id.line_ids.write({'ref_desc': self.description})
        return payments