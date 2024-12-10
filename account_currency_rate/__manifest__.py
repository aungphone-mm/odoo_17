# -*- coding: utf-8 -*-
##############################################################################
#
#    Mingalar Sky Company Limited.
#
#    Copyright (C) 2024-TODAY Mingalar Sky Company Limited (<https://www.mingalarsky.com>)
#    Author: Thant Shwe Aung (cto@mingalarsky.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "Account Currency Rate",
    'version': "17.0.1.0.0",
    'category': 'Accounting',
    'summary': 'Show currency rate after currency field',
    'description': '''
         This module adds a feature that displays the currency exchange rate immediately after the currency field in all currency-related fields across Odoo. 
         It affects all models that contain currency fields, providing users with an easy-to-view rate next to the respective currency field. 
         This feature enhances user experience by allowing quick access to the current exchange rate, enabling efficient currency management without having to manually check rates elsewhere. 
         It is a helpful tool for businesses that deal with multiple currencies, streamlining financial processes.
    ''',
    'author': 'Thant Shwe Aung',
    'company': 'Mingalar Sky Company Limited',
    'maintainer': 'Mingalar Sky Company Limited',
    'website': 'https://www.mingalarsky.com',
    'depends': ['mail', 'account_accountant'],
    'data': [
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
