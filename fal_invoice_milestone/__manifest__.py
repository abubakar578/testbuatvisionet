# -*- coding: utf-8 -*-
{
    "name": "Invoice Milestone",
    'version': '14.0.1.0.0',
    'license': 'OPL-1',
    'summary': 'Extend Sales App to have Invoice Milestone menu',
    'category': 'Invoicing Management',
    'author': "CLuedoo",
    'website': "https://www.cluedoo.com",
    'support': 'cluedoo@falinwa.com',
    "description": """
        Module to add invoice milestone
        ==================================

        Invoice Rule and subscription
    """,
    # To avoid Having to check fields. Just make it depends on Additional Info
    "depends": [
        'sale_management',
        'fal_invoice_merge',
        'fal_sale_additional_info',
    ],
    'data': [
        'data/ir_cron_data.xml',
        'data/invoice_rule_template.xml',
        'wizard/change_term_line_view.xml',
        'wizard/view_invoice_milestone.xml',
        'views/res_config_settings.xml',
        'views/fal_invoice_milestone_views.xml',
        'views/account_views.xml',
        'views/sale_views.xml',
        'security/ir.model.access.csv',
        'security/milestone_security.xml',
    ],
    'qweb': ['static/src/xml/invoice_template.xml'],
    'images': [
        'static/description/milestone_screenshot.png'
    ],
    'demo': [
    ],
    'price': 540.00,
    'currency': 'EUR',
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
