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

    # def action_post(self):
    #     """Additional validation before posting"""
    #     for move in self:
    #         if move.move_type in ('out_invoice', 'out_refund') and not move.account_receivable_id:
    #             raise ValidationError(_('Please select an account receivable before posting.'))
    #     return super().action_post()

    def action_print_custom_invoice(self):
        """Print the custom invoice report"""
        self.ensure_one()
        return self.env.ref('account_extension.action_report_custom_invoice').report_action(self)

    # @api.model
    # def write(self, vals):
    #     # print('hello world')
    #     res = super(AccountMove, self).write(vals)
    #     return res