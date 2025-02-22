from datetime import timedelta

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
            # Get date
            landing_line = line.passenger_landing_line_id
            date_key = ''
            if landing_line and landing_line.start_time:
                adjusted_time = landing_line.start_time + timedelta(hours=6, minutes=30) #to correct at report UI time
                date_key = adjusted_time.strftime('%d.%m.%y')

            # Get registration number
            reg_key = ''
            if landing_line and landing_line.flight_registration_no:
                reg_key = landing_line.flight_registration_no.name or ''

            # Group key combines just date and registration
            group_key = f"{date_key}-{reg_key}"

            if group_key not in grouped_lines:
                grouped_lines[group_key] = {
                    'date': date_key,
                    'flight_no': landing_line.flight_no or '',  # Keep first flight number seen
                    'aircraft_type': landing_line.aircraft_type_display or '',
                    'reg_no': reg_key,
                    'count': 1,
                    'amount': line.price_subtotal or 0.0,
                }
            else:
                # Combine counts and amounts for same date+registration
                grouped_lines[group_key]['count'] += 1
                grouped_lines[group_key]['amount'] += line.price_subtotal or 0.0

        result = list(grouped_lines.values())
        return sorted(result, key=lambda x: (x['date'] or '', x['reg_no'] or ''))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_landing_line_id = fields.Many2one('passenger.landing.line', string='Passenger Landing Line')



