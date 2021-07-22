# -*- coding: utf-8 -*-
# Part of Odoo Falinwa Edition. See LICENSE file for full copyright and licensing details.
{
    'name': 'Visionet CRM Extension',
    'version': '14.0.1.0.0',
    'license': 'OPL-1',
    'summary': " ",
    'category': 'CRM',
    'author': "CLuedoo",
    'website': "https://www.cluedoo.com",
    'support': 'cluedoo@falinwa.com',
    'description': '''
        This module has features:
        =============================

        Add Feature for Visionet
    ''',
    'depends': ['sale_crm', 'crm', 'product', 'fal_invoice_milestone', 'base_automation', 'ks_dashboard_ninja'],
    'data': [
        'data/ir_cron_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/res_users_view.xml',
        'views/res_partner_view.xml',
        'views/invoice_milestone_view.xml',
        'views/product_views.xml',
        'report/crm_activity_report_views.xml',
    ],
    'images': [
        'static/description/lead_project_screenshot.png'
    ],
    'demo': [
    ],
    'price': 0.00,
    'currency': 'EUR',
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
