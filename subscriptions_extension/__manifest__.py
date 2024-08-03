{
    'name': 'Subscriptions Extension',
    'version': '1.0',
    'category': 'Sales',
    'license': 'AGPL-3',
    'summary': 'Extend subscription functionality',
    'external_dependencies': {'python': ['lxml']},
    'depends': ['sale_subscription', 'sale_management', 'sale'],
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'data': [
        'security/ir.model.access.csv',
        'views/sale_subscription_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}