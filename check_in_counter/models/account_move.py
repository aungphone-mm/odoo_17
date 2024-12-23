from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    checkin_counter_id = fields.Many2one('checkin.counter', string='Checkin Counter', readonly=True)
    form_type = fields.Char('Form Type')

    def action_print_checkin_invoice(self):
        return self.env.ref('check_in_counter.action_checkin_report').report_action(self)

    def action_view_checkin_counter(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Check in Counter',
            'view_mode': 'form',
            'res_model': 'checkin.counter',
            'res_id': self.checkin_counter_id.id,
            'context': {'create': False},
        }

    # def _get_rate_totals(self):
    #     rate_totals = {}
    #     for line in self.invoice_line_ids:
    #         rate_name = line.checkin_counter_line_id.checkin_counter_rate_id.name
    #         if rate_name in rate_totals:
    #             rate_totals[rate_name] += line.price_subtotal
    #         else:
    #             rate_totals[rate_name] = line.price_subtotal
    #     return rate_totals

    def _get_unique_date_flights(self):
        # Create a set of tuples (date, flight_no) to count unique combinations
        unique_combinations = set()
        for line in self.invoice_line_ids:
            date = line.checkin_counter_line_id.end_time.date()
            flight_no = line.name
            unique_combinations.add((date, flight_no))
        return len(unique_combinations)

    def _get_amount_totals(self):
        amount_totals = {}
        for line in self.invoice_line_ids:
            amount = line.checkin_counter_line_id.amount
            if amount in amount_totals:
                amount_totals[amount]['count'] += 1
                amount_totals[amount]['total'] += line.price_subtotal
            else:
                amount_totals[amount] = {
                    'count': 1,
                    'total': line.price_subtotal
                }
        return amount_totals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    checkin_counter_line_id = fields.Many2one('checkin.counter.line', string='Check in Service Line')
