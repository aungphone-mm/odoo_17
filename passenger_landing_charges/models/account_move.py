from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_landing_id = fields.Many2one('passenger.landing', string='Passenger Landing', readonly=True)
    form_type = fields.Char('Form Type')

    def action_print_landing_invoice(self):
        return self.env.ref('passenger_landing_charges.action_landing_report').report_action(self)

    def action_print_parking_invoice(self):
        return self.env.ref('passenger_landing_charges.action_parking_report').report_action(self)

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
            # Safely get the date and registration number
            if line.passenger_landing_line_id and line.passenger_landing_line_id.start_time:
                date_key = line.passenger_landing_line_id.start_time.strftime('%d.%m.%y')
            else:
                date_key = ''

            if line.passenger_landing_line_id and line.passenger_landing_line_id.flight_registration_no:
                reg_key = line.passenger_landing_line_id.flight_registration_no.name or ''
            else:
                reg_key = ''

            group_key = f"{date_key}-{reg_key}"

            if group_key not in grouped_lines:
                grouped_lines[group_key] = {
                    'date': date_key,
                    'flight_no': line.passenger_landing_line_id.flight_no or '',
                    'aircraft_type': line.passenger_landing_line_id.aircraft_type_display or '',
                    'reg_no': reg_key,
                    'count': 1,
                    'amount': line.price_subtotal or 0.0,
                }
            else:
                grouped_lines[group_key]['count'] += 1
                grouped_lines[group_key]['amount'] += line.price_subtotal or 0.0

        # Convert falsy values to empty strings for sorting
        result = list(grouped_lines.values())
        return sorted(result, key=lambda x: (x['date'] or '', x['reg_no'] or ''))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_landing_line_id = fields.Many2one('passenger.landing.line', string='Passenger Landing Line')



