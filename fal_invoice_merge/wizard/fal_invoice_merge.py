# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FalInvoiceMerge(models.TransientModel):
    _name = 'fal.invoice.merge.wizard'
    _description = 'Invoice Merge Wizard'

    inv_action = fields.Selection([
        ('nothing', 'Do Nothing'),
        ('cancel', 'Cancel Invoices'),
        ('remove', 'Remove Invoices'),
    ], default='cancel', string='Invoice Action')
    invoice_date = fields.Date('Invoice Date')

    @api.model
    def default_get(self, fields):
        res = super(FalInvoiceMerge, self).default_get(fields)
        active_ids = self._context.get('active_ids')

        if len(active_ids) < 2:
            raise UserError(
                _('Please select multiple invoices to merge in the list '
                  'view.'))

        invoice_ids = self.env['account.move'].browse(active_ids)

        for inv in invoice_ids:
            if inv['state'] != 'draft':
                raise UserError(
                    _('At least one of the selected invoices is %s!') %
                    inv['state'])
            if inv['company_id'] != invoice_ids[0]['company_id']:
                raise UserError(
                    _('Not all invoices are at the same company!'))
            if inv['partner_id'] != invoice_ids[0]['partner_id']:
                raise UserError(
                    _('Not all invoices are for the same partner!'))
            if inv['currency_id'] != invoice_ids[0]['currency_id']:
                raise UserError(
                    _('Not all invoices are at the same currency!'))
        return res

    def action_merge_invoice(self):
        inv_list = []
        move_obj = self.env['account.move']
        active_ids = self._context.get('active_ids')
        invoice_ids = move_obj.browse(active_ids)
        inv_type = invoice_ids[0].move_type
        partner_id = invoice_ids[0].partner_id

        fields_obj = self.env['ir.model.fields']
        model_obj = self.env['ir.model']
        move_line = model_obj.search([('model', '=', 'account.move.line')])
        move_move = model_obj.search([('model', '=', 'account.move')])
        sale_line_ids = fields_obj.search([('model_id', '=', move_line.id), ('name', '=', 'sale_line_ids')])
        purchase_line_id = fields_obj.search([('model_id', '=', move_line.id), ('name', '=', 'purchase_line_id')])
        fal_title = fields_obj.search([('model_id', '=', move_move.id), ('name', '=', 'fal_title')])

        vals = {
            'partner_id': partner_id.id,
            'move_type': inv_type,
            'invoice_date': self.invoice_date,
            'currency_id': invoice_ids[0].currency_id.id,
        }

        join_title = ','
        title = []
        if fal_title:
            for inv in invoice_ids:
                if inv.fal_title and inv.fal_title not in title:
                    title.append(inv.fal_title)
            vals.update({'fal_title': join_title.join(title)})

        inv = move_obj.with_context({
            'default_move_type': inv_type,
            'check_move_validity': False,
            'trigger_onchange': True,
        }).with_company(invoice_ids[0].company_id.id).create(vals)

        # Cannot Remove inside the For Loop. So we need to hold all the Id's first
        inv_to_unlink = []
        if inv:
            inv_list.append(inv.id)
            line_vals = {'move_id': inv.id}
            count = 0
            # Merge origin
            origin = ','
            inv_origin = []
            for invoice in invoice_ids:
                if invoice.invoice_origin and invoice.invoice_origin not in inv_origin:
                    inv_origin.append(invoice.invoice_origin)
                count += 1
                if invoice.invoice_line_ids:
                    for line in invoice.invoice_line_ids:
                        # add condition if sale or purchase module not installed
                        if sale_line_ids:
                            line_vals.update({'sale_line_ids': [(6, 0, line.sale_line_ids.ids)]})
                        if purchase_line_id:
                            line_vals.update({'purchase_line_id': line.purchase_line_id.id})
                        line.with_context(check_move_validity=False).copy(default=line_vals)
                if self.inv_action == 'cancel':
                    invoice.sudo().button_cancel()
                    inv_list.append(invoice.id)
                elif self.inv_action == 'remove':
                    # remove line if remove the invoice, (cannot delete the invoice when merge invoice milestone)
                    if sale_line_ids:
                        invoice.invoice_line_ids.write({'sale_line_ids': False})
                    if purchase_line_id:
                        invoice.invoice_line_ids.write({'purchase_line_id': False})
                    inv_to_unlink.append(invoice.id)
            self.env['account.move'].sudo().browse(inv_to_unlink).unlink()
            inv.invoice_origin = origin.join(inv_origin)
            inv._onchange_partner_id()
            inv._onchange_invoice_line_ids()
            inv._move_autocomplete_invoice_lines_values()

        if inv_list:
            view = self.env.ref('account.view_invoice_tree')
            if inv_type in ['out_invoice', 'out_refund']:
                view = self.env.ref('account.view_invoice_tree')
            elif inv_type in ['in_invoice', 'in_refund']:
                view = self.env.ref('account.view_invoice_tree')

            action_name = 'Customer Invoices'
            if inv_type == 'out_invoice':
                action_name = 'Customer Invoices'
            elif inv_type == 'out_refund':
                action_name = 'Customer Credit Notes'
            elif inv_type == 'in_invoice':
                action_name = 'Vendor Bills'
            elif inv_type == 'in_refund':
                action_name = 'Vendor Credit Notes'

            return {
                'name': action_name,
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'views': [(view.id, 'tree'), (False, 'form')],
                'view_id': view.id,
                'domain': [('id', 'in', inv_list)]
            }
