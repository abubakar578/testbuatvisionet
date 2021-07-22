# -*- coding: utf-8 -*-

from odoo import models, fields, api
import openerp.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fal_attachment = fields.Binary(string='Reference Attachment', filestore=True)
    fal_attachment_name = fields.Char(string='Attachment name')
    fal_partner_contact_person_id = fields.Many2one('res.partner', 'Contact Person')

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.company_id.fal_company_late_payment_statement:
            res['fal_use_late_payment_statement'] = True
        if self.client_order_ref:
            res['fal_client_order_ref'] = self.client_order_ref
        return res

    # sale archive
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide\
        the Sale Order without removing it.")

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).\
            onchange_partner_id()
        partner = self.partner_id
        self.fal_partner_contact_person_id = partner.child_ids and \
            partner.child_ids[0].id or False
        return res

    @api.depends('partner_id')
    def _get_parent_company(self):
        for sale_order in self:
            sale_order.fal_parent_company = sale_order.partner_id.parent_id or False


    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity', compute_sudo=True,
        related='partner_id.commercial_partner_id', store=True, readonly=True,
        help="The commercial entity that will be used on Journal Entries for this invoice")
    fal_parent_company = fields.Many2one(
        'res.partner',
        compute='_get_parent_company',
        string='Parent Company',
        help='The Parent Company for group',
        readonly=True,
        store=True
    )
