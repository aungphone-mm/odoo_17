{
    'name': 'Airline Passenger Bill Management',
    'version': '17.0.1.0',
    'category': 'Utilities',
    'license': 'AGPL-3',
    'summary': """Manage the check-in process for landing operations efficiently. 
                This module helps in tracking and managing the check-in details of various entities, 
                ensuring smooth operations and accurate record-keeping. 
                Ideal for companies and organizations that require precise check-in management.""",
    'depends': ['mail', 'account', 'base', 'web', 'hr'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'security/ir.model.access.csv',
        'report/custom_template.xml',
        'views/airline_passenger_bill_line_view.xml',
        'views/airline_passenger_bill_views.xml',
        'data/ir_sequence_data.xml',
        'views/airline_view.xml',
        'views/ailine_bill_counter_view.xml',
        'report/airline_invoice_template.xml',
        'views/menu_views.xml',
    ],
    'assets' : {
        'web.assets_backend': [
            'airline_passenger_bill/static/src/js/*.js',
            'airline_passenger_bill/static/src/scss/*.scss'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
