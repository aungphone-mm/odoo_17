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
    'depends': ['base', 'account', 'account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'view/account_account_views.xml',
        'view/account_cashbook_views.xml',
        'view/account_asset_views.xml',
        'data/ir_sequence_data.xml',
        'report/journal_entry_invoice.xml',
        'report/cashbook_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
