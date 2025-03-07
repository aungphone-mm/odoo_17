{
    'name': 'YACL Airline',
    'version': '17.0.1.0',
    'category': 'Utilities',
    'license': 'AGPL-3',
    'summary': """Manage Airline""",
    'depends': ['mail', 'account', 'base'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'depends': [
            'sale',
            'web',
            'sale_subscription',

        ],
    'data': [
        'security/ir.model.access.csv',
        # Base views
        'views/yacl_airline_views.xml',
        'views/yacl_flights_view.xml',
        'views/menu.xml',
        'wizard/report_airline_charges_wizard_view.xml',
        'report/airline_charges_report.xml',

        'wizard/report_landing_wizard_view.xml',
        'report/landing_summary_report.xml',

        'wizard/checkin_report_wizard_view.xml',
        'report/checkin_report_template.xml',
        # Invoice wizard and report
        'wizard/report_invoice_summary_wizard_view.xml',
        'report/invoice_summary_report.xml',
        # Passenger wizard and report
        'wizard/report_passenger_wizard_view.xml',
        'report/passenger_summary_report.xml',
        'report/report_rampbus_invoice.xml',
        'report/report_watermeter_invoice.xml',
        'report/report_lavatory_invoice.xml',
        'report/report_non_schedule_invoice.xml',
        'report/subscription_report.xml',
        'wizard/checkin_report_wizard_view.xml',
        'report/checkin_report_template.xml',
        'wizard/boarding_bridge_report_wizard_view.xml',
        'report/boarding_bridge_report.xml',
        'wizard/security_service_report_wizard_view.xml',
        'report/security_service_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}