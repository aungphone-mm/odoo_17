{
    'name': 'Landing Check In Management',
    'version': '17.0.1.0',
    'category': 'Utilities',
    'license': 'AGPL-3',
    'summary': """Manage the check-in process for landing operations efficiently. 
                This module helps in tracking and managing the check-in details of various entities, 
                ensuring smooth operations and accurate record-keeping. 
                Ideal for companies and organizations that require precise check-in management.""",
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'security/ir.model.access.csv',
        'views/landing_check_in_lines_views.xml',
        'views/landing_check_in_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}