{
    'name': 'YACL Airline',
    'version': '17.0.1.0',
    'category': 'Utilities',
    'license': 'AGPL-3',
    'summary': """Manage Airline""",
    'depends': ['mail', 'account', 'base'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'security/ir.model.access.csv',
        'views/yacl_airline_views.xml',
        'views/yacl_flights_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}