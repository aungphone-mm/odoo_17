{
    'name': 'Electric Meter Billing Management',
    'version': '1.0',
    'category': 'Sales',
    'license': 'AGPL-3',
    'summary': """Efficiently manage electric meter readings and generate accurate bills for customers. 
                This module allows you to track meter readings, calculate consumption, generate invoices, 
                and manage payment collections seamlessly. 
                Ideal for utility companies and property managers to streamline their billing processes.""",
    'depends': ['sale_subscription'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'views/location.xml',
        'views/menu_views.xml',
        'views/electric_meter.xml',
        'views/res_partner.xml',
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}