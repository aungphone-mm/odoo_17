from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    custom_header = fields.Html(string='Custom Header')
    custom_note = fields.Html(string='Custom Note')

    account_receivable_id = fields.Many2one(
        'account.account',
        string='Account Receivable',
        domain="[('account_type', '=', 'asset_receivable')]",
        default=lambda self: self._get_default_account_receivable(),
        compute='_compute_account_receivable_id',
        store=True,
        readonly=False
    )

    # def write(self, vals):
    #     # First perform the original write operation
    #     res = super().write(vals)
    #
    #     # If payment reference was updated
    #     if 'payment_reference' in vals:
    #         for move in self:
    #             move.line_ids.write({
    #                 'ref': move.payment_reference
    #             })
    #     return res
    # @api.onchange('payment_reference')
    # def _onchange_payment_reference(self):
    #     for move in self:
    #         if move.payment_reference:
    #             # Update all journal items with the payment reference
    #             for line in move.line_ids:
    #                 line.ref = move.payment_reference
    @api.depends('line_ids', 'line_ids.account_id', 'partner_id')
    def _compute_account_receivable_id(self):
        """Compute account_receivable_id from existing move lines or partner"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # First try to get from existing receivable line
                receivable_line = move.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                )
                if receivable_line:
                    move.account_receivable_id = receivable_line[0].account_id
                # Fallback to partner's default receivable
                elif move.partner_id:
                    move.account_receivable_id = move.partner_id.property_account_receivable_id
                else:
                    move.account_receivable_id = False

    @api.model
    def _get_default_account_receivable(self):
        """Get default account receivable from partner or company"""
        if self.partner_id:
            return self.partner_id.property_account_receivable_id

        # Get default receivable from chart of accounts
        return self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('account_type', '=', 'asset_receivable'),
            ('deprecated', '=', False)
        ], limit=1)

    def _get_available_account_receivables(self):
        """Get available account receivables including those used in existing moves"""
        domain = [
            '|',
            ('account_type', '=', 'asset_receivable'),
            ('id', '=', self.account_receivable_id.id),  # Include current account even if deprecated
            ('company_id', '=', self.company_id.id),
        ]
        return self.env['account.account'].search(domain)

    @api.onchange('account_receivable_id')
    def _onchange_account_receivable(self):
        """Update journal items when account receivable changes"""
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                receivable_line = move.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                )
                if receivable_line and move.account_receivable_id:
                    receivable_line.account_id = move.account_receivable_id

    @api.onchange('partner_id')
    def _onchange_partner_account_receivable(self):
        """Update account receivable when partner changes"""
        if self.partner_id and self.move_type in ('out_invoice', 'out_refund'):
            self.account_receivable_id = self.partner_id.property_account_receivable_id

    def action_print_custom_invoice(self):
        """Print the custom invoice report"""
        self.ensure_one()
        return self.env.ref('account_extension.action_report_custom_invoice').report_action(self)

    depreciation_usd = fields.Float(
        string='Depreciation (USD)',
        compute='_compute_usd_amounts',
        store=True
    )
    cumulative_depreciation_usd = fields.Float(
        string='Cumulative Depreciation (USD)',
        compute='_compute_usd_amounts',
        store=True
    )
    depreciable_value_usd = fields.Float(
        string='Depreciable Value (USD)',
        compute='_compute_usd_amounts',
        store=True
    )

    @api.depends('amount_total', 'asset_id.exchange_rate', 'asset_id.asset_currency')
    def _compute_usd_amounts(self):
        for move in self:
            if move.asset_id.asset_currency == 'USD' and move.asset_id.exchange_rate:
                # Convert amount_total to USD
                move.depreciation_usd = move.amount_total / move.asset_id.exchange_rate

                # Calculate cumulative depreciation in USD
                previous_moves = self.env['account.move'].search([
                    ('asset_id', '=', move.asset_id.id),
                    ('date', '<=', move.date),
                    ('state', '!=', 'cancel')
                ], order='date')

                cumulative_mmk = sum(m.amount_total for m in previous_moves)
                move.cumulative_depreciation_usd = cumulative_mmk / move.asset_id.exchange_rate

                # Calculate depreciable value in USD
                if move.asset_id:
                    move.depreciable_value_usd = move.asset_id.book_value_usd
            else:
                move.depreciation_usd = 0.0
                move.cumulative_depreciation_usd = 0.0
                move.depreciable_value_usd = 0.0

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # The ref field already exists in account.move.line
    ref_no = fields.Char(string='Reference No', readonly=False)
    note = fields.Char(string='Note')
    received_date = fields.Char(string='Received Date')
