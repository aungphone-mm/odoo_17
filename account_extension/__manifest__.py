{
    'name': 'Account Extension',
    'version': '1.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'description': """
Accounting Extension to update journal information 
==============================================
Add Date, Reference and Name in Journal Item in Views.
    """,
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'depends': ['base','account'],
    'data': [
                'security/ir.model.access.csv',
                'view/account_view.xml',
                'view/account_category_view.xml',
                ],
    'installable': True,
    'application': False,
    'auto_install': False,
}