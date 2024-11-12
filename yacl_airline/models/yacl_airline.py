from odoo import fields, models, api

class Airline(models.Model):
    _name = 'airline'
    _description = 'Airline Information'

    name = fields.Char('Airline', required=True)
    description = fields.Text('Code', required=True)
    partner_id = fields.Many2one('res.partner', string='Company')
    flight_ids = fields.One2many('flights', 'airline_id', string='Flights')

    @api.model
    def create(self, vals):
        # Create partner first
        partner = self.env['res.partner'].create({
            'name': vals.get('name'),
            'company_type': 'company',
            'is_airline': True,
        })
        # Add partner_id to vals
        vals['partner_id'] = partner.id
        return super(Airline, self).create(vals)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_airline = fields.Boolean(string='Is Airline', default=False)