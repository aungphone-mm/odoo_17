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
        # Base views
        'views/yacl_airline_views.xml',
        'views/yacl_flights_view.xml',
        'views/menu.xml',
        # Invoice wizard and report
        'wizard/report_selection_wizard_view.xml',
        'report/invoice_summary_report.xml',
        # Passenger wizard and report
        'wizard/report_selection_wizard_passenger_view.xml',
        'report/passenger_summary_report.xml',

        'wizard/report_selection_wizard_landing_view.xml',
        'report/landing_summary_report.xml',

        'wizard/report_module_wizard_view.xml',
        'report/airline_charges_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}