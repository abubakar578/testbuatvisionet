# -*- coding: utf-8 -*-
{
    "name": "Invoice Merge",
    'version': '14.0.1.0.0',
    'license': 'OPL-1',
    'summary': 'Merge two or more draft invoices',
    'category': 'Invoicing Management',
    'author': "CLuedoo",
    'website': "https://www.cluedoo.com",
    'support': 'cluedoo@falinwa.com',
    "description": """
Invoice Merge
==================================

Merge two or more draft invoices
    """,
    "depends": [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/fal_invoice_merge_views.xml',
    ],
    'images': [
        'static/description/invoice_merge.png'
    ],
    'demo': [
    ],
    'price': 180.00,
    'currency': 'EUR',
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
