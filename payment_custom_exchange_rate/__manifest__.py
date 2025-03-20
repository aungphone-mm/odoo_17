# __manifest__.py
{
    'name': 'Custom Payment Exchange Rate',
    'version': '1.0',
    'category': 'Accounting/Payment',
    'summary': 'Allow manual exchange rate input when registering payments',
    'description': """
        This module adds an exchange rate field to the payment registration wizard,
        allowing users to manually set the exchange rate when paying in a different currency.
    """,
    'depends': ['account'],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}