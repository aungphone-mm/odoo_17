from datetime import timedelta

from odoo import fields, models, _, api


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


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def amount_to_text(self, amount):
        """
        Override the default amount_to_text to correctly handle cents for USD
        """
        self.ensure_one()

        def _num2words(number, lang):
            # You could use the num2words Python library here
            # This is a simplified implementation for USD
            # Replace with a more complete implementation if needed

            def _convert_nn(val):
                """Convert a value < 100 to English words."""
                if val < 20:
                    return {
                        0: 'Zero', 1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five',
                        6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten',
                        11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen',
                        15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen', 18: 'Eighteen',
                        19: 'Nineteen'
                    }[val]

                tens = {
                    2: 'Twenty', 3: 'Thirty', 4: 'Forty', 5: 'Fifty',
                    6: 'Sixty', 7: 'Seventy', 8: 'Eighty', 9: 'Ninety'
                }

                tens_digit = val // 10
                units_digit = val % 10

                if units_digit != 0:
                    return tens[tens_digit] + '-' + _convert_nn(units_digit).lower()
                return tens[tens_digit]

            def _convert_nnn(val):
                """Convert a value < 1000 to English words."""
                word = ''
                hundreds = val // 100
                remainder = val % 100

                if hundreds != 0:
                    word = _convert_nn(hundreds) + ' Hundred'
                    if remainder != 0:
                        word += ' And '

                if remainder != 0:
                    word += _convert_nn(remainder)

                return word

            def _convert_number(val):
                if val == 0:
                    return 'Zero'

                negative = val < 0
                val = abs(val)

                words = []

                if val < 1000:
                    words.append(_convert_nnn(val))
                else:
                    groups = []
                    while val > 0:
                        groups.append(val % 1000)
                        val //= 1000

                    group_names = ['', 'Thousand', 'Million', 'Billion', 'Trillion']

                    for i, group in enumerate(groups):
                        if group != 0:
                            words.insert(0, _convert_nnn(group) + (i > 0 and ' ' + group_names[i] or ''))

                text = ' '.join(words)
                if negative:
                    text = 'Negative ' + text

                return text

            return _convert_number(number)

        # Split amount into dollars and cents
        dollars, cents = divmod(round(amount * 100), 100)

        # Convert dollars to words
        dollars_text = _num2words(int(dollars), 'en').title()

        # Format full text
        if cents == 0:
            text = f"{dollars_text} Dollars"
        else:
            cents_text = _num2words(int(cents), 'en').title()
            text = f"{dollars_text} Dollars and {cents_text} Cents"

        return text