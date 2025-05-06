# journal_report_wizard.py
from datetime import timedelta
from odoo import fields, models, api


class JournalReportWizard(models.TransientModel):
    _name = 'journal.report.wizard'
    _transient_max_count = 100
    _description = 'Journal Report Wizard'

    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    move_ids = fields.Many2many(
        'account.move',
        string='Journal Entries',
        compute='_compute_journal_entries'
    )

    total_debit = fields.Monetary(string='Total Debit', compute='_compute_totals', currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Credit', compute='_compute_totals', currency_field='currency_id')
    balance = fields.Monetary(string='Balance', compute='_compute_totals', currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')

    @api.depends('journal_id', 'start_date', 'end_date', 'company_id')
    def _compute_journal_entries(self):
        for wizard in self:
            domain = [
                ('journal_id', '=', wizard.journal_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date),
                ('company_id', '=', wizard.company_id.id),
                # ('state', '=', 'posted')
            ]
            wizard.move_ids = self.env['account.move'].search(domain)

    @api.depends('move_ids')
    def _compute_totals(self):
        for wizard in self:
            move_lines = self.env['account.move.line'].search([
                ('move_id', 'in', wizard.move_ids.ids)
            ])
            wizard.total_debit = sum(move_lines.mapped('debit'))
            wizard.total_credit = sum(move_lines.mapped('credit'))
            wizard.balance = wizard.total_debit - wizard.total_credit

    def action_generate_report(self):
        data = {
            'journal_id': self.journal_id.id,
            'journal_name': self.journal_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'ids': self.ids,
            'model': 'journal.report.wizard',
        }
        return self.env.ref('yacl_airline.action_journal_report').report_action(self, data=data)