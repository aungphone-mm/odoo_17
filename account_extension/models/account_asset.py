from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

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

    def compute_depreciation_board(self, date=False):
        # Need to unlink draft moves before adding new ones because if we create new moves before, it will cause an error
        self.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').unlink()
        new_depreciation_moves_data = []
        for asset in self:
            new_depreciation_moves_data.extend(asset._recompute_board(date))

        # Create the new moves
        new_depreciation_moves = self.env['account.move'].create(new_depreciation_moves_data)

        # Set auto_post and apply old account code for each move
        for move in new_depreciation_moves:
            move.write({'auto_post': 'at_date'})
            move.action_apply_old_account_code()

        new_depreciation_moves_to_post = new_depreciation_moves.filtered(lambda move: move.asset_id.state == 'open')
        # In case of the asset is in running mode, we post in the past and set to auto post move in the future
        new_depreciation_moves_to_post._post()

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
    ref_no = fields.Char(string="Reference No.")


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    description = fields.Text(string='Description', help='Additional payment details')
    ref_no = fields.Char(string="Reference No.")
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', readonly=True)
    show_total_amount = fields.Boolean(compute='_compute_show_total_amount')

    @api.depends('line_ids')
    def _compute_total_amount(self):
        for wizard in self:
            # In Odoo 17, use 'amount_residual' instead of 'amount'
            wizard.total_amount = sum(wizard.line_ids.mapped('amount_residual'))

    @api.depends('line_ids')
    def _compute_show_total_amount(self):
        for wizard in self:
            wizard.show_total_amount = len(wizard.line_ids) > 1

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['description'] = self.description
        payment_vals['ref_no'] = self.ref_no
        return payment_vals

    # def _create_payments(self):
    #     payments = super()._create_payments()
    #     for payment in payments:
    #         if self.description and payment.move_id:
    #             # Update all move lines with the description
    #             payment.move_id.line_ids.write({'ref_desc': self.description})
    #             payment.move_id.line_ids.write({'ref_no': self.ref_no})
    #
    #             # For reconciliations, find invoice lines and update them
    #             for line in payment.move_id.line_ids.filtered(
    #                     lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')):
    #
    #                 # Get reconciled lines
    #                 reconciled_lines = line.matched_debit_ids.debit_move_id + line.matched_credit_ids.credit_move_id
    #                 if reconciled_lines:
    #                     reconciled_lines.write({'ref_desc': self.description})
    #                     reconciled_lines.write({'ref_no': self.ref_no})
    #     return payments

    def _create_payments(self):
        payments = super()._create_payments()
        for payment in payments:
            if payment.move_id:
                # Apply the old account code logic to the payment move
                payment.move_id.action_apply_old_account_code()

                # Update all move lines with the description and ref_no
                if self.description:
                    payment.move_id.line_ids.write({'ref_desc': self.description})
                if self.ref_no:
                    payment.move_id.line_ids.write({'ref_no': self.ref_no})

                # For reconciliations, find invoice lines and update them
                for line in payment.move_id.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')):

                    # Get reconciled lines
                    reconciled_lines = line.matched_debit_ids.debit_move_id + line.matched_credit_ids.credit_move_id
                    if reconciled_lines:
                        if self.description:
                            reconciled_lines.write({'ref_desc': self.description})
                        if self.ref_no:
                            reconciled_lines.write({'ref_no': self.ref_no})
        return payments
