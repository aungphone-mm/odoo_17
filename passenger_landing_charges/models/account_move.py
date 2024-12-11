from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_landing_id = fields.Many2one('passenger.landing', string='Passenger Landing', readonly=True)
    form_type = fields.Char('Form Type')

    def action_print_landing_invoice(self):
        return self.env.ref('passenger_landing_charges.action_landing_report').report_action(self)

    def action_view_passenger_landing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Aircraft Landing',
            'view_mode': 'form',
            'res_model': 'passenger.landing',
            'res_id': self.passenger_landing_id.id,
            'context': {'create': False},
        }

    def get_grouped_landing_lines(self):
        grouped_lines = {}
        for line in self.invoice_line_ids:
            date_key = line.passenger_landing_line_id.start_time.strftime('%d.%m.%y')
            reg_key = line.passenger_landing_line_id.flight_registration_no.name
            group_key = f"{date_key}-{reg_key}"

            if group_key not in grouped_lines:
                grouped_lines[group_key] = {
                    'date': date_key,
                    'flight_no': line.passenger_landing_line_id.flight_no,
                    'aircraft_type': line.passenger_landing_line_id.aircraft_type_display,
                    'reg_no': reg_key,
                    'count': 1,
                    'amount': line.price_subtotal,
                }
            else:
                grouped_lines[group_key]['count'] += 1
                grouped_lines[group_key]['amount'] += line.price_subtotal

        return sorted(grouped_lines.values(), key=lambda x: (x['date'], x['reg_no']))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_landing_line_id = fields.Many2one('passenger.landing.line', string='Passenger Landing Line')



