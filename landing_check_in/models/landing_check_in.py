from odoo import fields, models, api, _

TIME_FORMAT = [
    ('12:00 AM', '12:00 AM'),
    ('12:30 AM', '12:30 AM'),
    ('1:00 AM', '1:00 AM'),
    ('1:30 AM', '1:30 AM'),
    ('2:00 AM', '2:00 AM'),
    ('2:30 AM', '2:30 AM'),
    ('3:00 AM', '3:00 AM'),
    ('3:30 AM', '3:30 AM'),
    ('4:00 AM', '4:00 AM'),
    ('4:30 AM', '4:30 AM'),
    ('5:00 AM', '5:00 AM'),
    ('5:30 AM', '5:30 AM'),
    ('6:00 AM', '6:00 AM'),
    ('6:30 AM', '6:30 AM'),
    ('7:00 AM', '7:00 AM'),
    ('7:30 AM', '7:30 AM'),
    ('8:00 AM', '8:00 AM'),
    ('8:30 AM', '8:30 AM'),
    ('9:00 AM', '9:00 AM'),
    ('9:30 AM', '9:30 AM'),
    ('10:00 AM', '10:00 AM'),
    ('10:30 AM', '10:30 AM'),
    ('11:00 AM', '11:00 AM'),
    ('11:30 AM', '11:30 AM'),
    ('12:00 PM', '12:00 PM'),
    ('12:30 PM', '12:30 PM'),
    ('1:00 PM', '1:00 PM'),
    ('1:30 PM', '1:30 PM'),
    ('2:00 PM', '2:00 PM'),
    ('2:30 PM', '2:30 PM'),
    ('3:00 PM', '3:00 PM'),
    ('3:30 PM', '3:30 PM'),
    ('4:00 PM', '4:00 PM'),
    ('4:30 PM', '4:30 PM'),
    ('5:00 PM', '5:00 PM'),
    ('5:30 PM', '5:30 PM'),
    ('6:00 PM', '6:00 PM'),
    ('6:30 PM', '6:30 PM'),
    ('7:00 PM', '7:00 PM'),
    ('7:30 PM', '7:30 PM'),
    ('8:00 PM', '8:00 PM'),
    ('8:30 PM', '8:30 PM'),
    ('9:00 PM', '9:00 PM'),
    ('9:30 PM', '9:30 PM'),
    ('10:00 PM', '10:00 PM'),
    ('10:30 PM', '10:30 PM'),
    ('11:00 PM', '11:00 PM'),
    ('11:30 PM', '11:30 PM'),
]

class LandingCheckIn(models.Model):
        _name = 'landing.check.in'
        _description =  'Landing Check In'

        name= fields.Char(string='Name', required=True)
        check_in = fields.Selection([
            ('airline', 'Airlines'),
            ('cooperate', 'Cooperate'),
            ('embassy', 'Embassy'),
            ('home_use', 'Home Use'),
            ('complimentary', 'Complimentary'),
            ('walkin', 'Walk-In'),
            ('miscellaneous', 'Miscellaneous'),
            ('membership', 'Membership'),
            ('agent', 'Agent'),
        ], string='Check In')

        location_type = fields.Selection([
            ('domestic', 'Domestic'),
            ('international', 'International'),
        ], string='Location Type')

        user_id = fields.Many2one('res.users', string='Receptionist', default=lambda self: self.env.uid, required=True)
        date = fields.Date('Date of Travel', default=fields.Date.context_today, required=True)
        start_time = fields.Selection(TIME_FORMAT, string='Start Time', required=True)
        end_time = fields.Selection(TIME_FORMAT, string='End Time', required=True)
        landing_check_in_line_ids = fields.One2many('landing.check.in.line', 'landing_check_in_id',
                                                    string='Landing Check In Lines')









   


