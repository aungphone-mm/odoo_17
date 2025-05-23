from odoo import fields, models, api

class Airline(models.Model):
    _name = 'airline'
    _description = 'Airline Information'
    _inherit = ['mail.activity.mixin', 'mail.thread']

    name = fields.Char('Airline', required=True)
    description = fields.Text('Code', required=True)
    partner_id = fields.Many2one('res.partner', string='Company')
    flight_ids = fields.One2many('flights', 'airline_id', string='Flights')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Create partner first
            partner = self.env['res.partner'].create({
                'name': vals.get('name'),
                'company_type': 'company',
                'is_airline': True,
            })
            # Add partner_id to vals
            vals['partner_id'] = partner.id
        return super().create(vals_list)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res'

    is_airline = fields.Boolean(string='Is Airline', default=False)
    old_ac = fields.Char(string='Old Account Code')

class AccountAsset(models.Model):
    _inherit = 'account.asset'
    _description = 'Account Asset'

    main_ac = fields.Char(string='Main Account Code')
