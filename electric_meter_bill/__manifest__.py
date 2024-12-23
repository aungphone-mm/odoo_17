{
    'name': 'Electric Meter Billing Management',
    'version': '1.0',
    'category': 'Sales',
    'license': 'AGPL-3',
    'summary': """Efficiently manage electric meter readings and generate accurate bills for customers. 
                This module allows you to track meter readings, calculate consumption, generate invoices, 
                and manage payment collections seamlessly. 
                Ideal for utility companies and property managers to streamline their billing processes.""",
    'depends': ['sale_subscription','yacl_airline','web'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'security/ir.model.access.csv',
        'views/location.xml',
        'views/menu_views.xml',
        'report/invoice_custom_template.xml',
        'views/electric_meter.xml',
        'views/res_partner.xml',
        'report/report_electric_meter_reading.xml',
        'report/report_electric_invoice.xml',
        'data/ir_sequence_data.xml',
        'report/report_consolidated_meter_reading.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}