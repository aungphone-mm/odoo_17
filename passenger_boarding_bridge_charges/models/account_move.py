from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    passenger_boarding_bridge_charges_id = fields.Many2one('passenger.boarding.bridge.charges', string='Boarding Bridge Service', readonly=True)
    form_type = fields.Char('Form Type')
    def action_print_bridge_invoice(self):
        return self.env.ref('passenger_boarding_bridge_charges.action_boarding_report').report_action(self)

    def action_view_bridge_service(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Passenger Boarding Bridge Charges',
            'view_mode': 'form',
            'res_model': 'passenger.boarding.bridge.charges',
            'res_id': self.passenger_boarding_bridge_charges_id.id,
            'context': {'create': False},
        }

    def _get_amount_totals_bridge(self):
        amount_totals = {}
        for line in self.invoice_line_ids:
            time = line._get_time_from_rate()
            if time and line.price_subtotal:
                rate = line.price_unit / time  # Calculate rate

                if rate in amount_totals:
                    amount_totals[rate]['count'] += time  # Add the time value instead of incrementing by 1
                    amount_totals[rate]['total'] += line.price_subtotal
                else:
                    amount_totals[rate] = {
                        'count': time,  # Initialize with time value instead of 1
                        'total': line.price_subtotal
                    }
        return amount_totals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    passenger_boarding_bridge_charges_line_id = fields.Many2one('passenger.boarding.bridge.charges.line', string='Bridge Service Line')

    # def _get_time_from_rate(self):
    #     self.ensure_one()
    #     if not self.price_unit:
    #         return False
    #
    #     rate_line = self.env['passenger.boarding.bridge.charges.rate.line'].search([
    #         ('unit_price', '=', self.price_unit)
    #     ], limit=1)
    #
    #     return rate_line.time if rate_line else False

    def _get_time_from_rate(self):
        """Get time value based on total service duration in minutes"""
        self.ensure_one()
        if not self.passenger_boarding_bridge_charges_line_id:
            return False
        # Get total minutes from the service line
        total_minutes = self.passenger_boarding_bridge_charges_line_id.total_minutes
        # Find matching rate line based on duration range
        rate_line = self.env['passenger.boarding.bridge.charges.rate.line'].search([
            ('rate_id', '=', self.passenger_boarding_bridge_charges_line_id.bridge_rate_id.id),
            ('from_unit', '<=', total_minutes),
            ('to_unit', '>=', total_minutes)
        ], limit=1)
        if rate_line:
            return rate_line.time
        return 0.0

