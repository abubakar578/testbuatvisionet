# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime,date

class SaleOrder(models.Model):
	_inherit="sale.order"

	def action_confirm(self):
		res = super(SaleOrder, self).action_confirm()
		for order in self:
			salestarget_id =self.env['saletarget.saletarget'].search([
					('sales_person_id','=', order.user_id.id),
					('state','in', ['open']),
					],order="id",limit=1)
			if salestarget_id:
				if order.date_order.date() >= salestarget_id.start_date and order.date_order.date() <= salestarget_id.end_date:
					for order_line in order.order_line:
						for sale_line in salestarget_id.target_line_ids:
							if order_line.product_id == sale_line.product_id:
								achieve_quantity = sale_line.achieve_quantity + order_line.product_uom_qty
								sale_line.write({'achieve_quantity': achieve_quantity})
					salestarget_id.update({
						'target_achieve':'Sale Order Confirm',
						'partner_id': order.partner_id.id
					})
		return res