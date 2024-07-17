{
    'name': 'Website Extension',
    'version': '16.0.0.0',
    'category': 'Website',
    'license': 'AGPL-3',
    'description': """
Website Extension to update website interface
==============================================
Remove Block UI and Enterprise Theme.
    """,
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'depends': ['base', 'web'],
    'data': [
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'website_extension/static/src/js/*.js',
            'website_extension/static/src/css/*.css',
        ],
    },
    'installable': True,
    'active': False,
}