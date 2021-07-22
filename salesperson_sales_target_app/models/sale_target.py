# -*- coding: utf-8 -*-
from __future__ import division
from odoo import models, fields, api, _
from datetime import datetime,date
from odoo.exceptions import UserError

class SaleTarget(models.Model):
	_name="saletarget.saletarget"
	_description= "Sales Target"

	name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
	sales_person_id = fields.Many2one('res.users',string="Salesperson")
	start_date = fields.Date(string="Start Date")
	end_date = fields.Date(string="End Date")
	target_achieve = fields.Selection([('Sale Order Confirm','Sale Order Confirm'),
								('Delivery Order Done','Delivery Order Done'),
								('Invoice Created','Invoice Created'),
								('Invoice Paid','Invoice Paid')],string="Target Achieve")
	target = fields.Integer(string="Target")
	difference = fields.Integer(string="Difference",compute="_get_difference",store=True, readonly=True)
	achieve = fields.Integer(string="Achieve", compute="_compute_sales_target", store=True, readonly=True)
	achieve_percentage = fields.Integer(string="Achieve Percentage",compute="_get_achieve_percentage", readonly=True)
	responsible_salesperson_id = fields.Many2one('res.users',string="Responsible Salesperson")
	target_line_ids = fields.One2many('targetline.targetline','reverse_id')
	state = fields.Selection([
			('draft','Draft'),
			('open', 'Open'),
			('closed', 'Closed'),
			('cancelled', 'Cancelled'),
		], string='Status', readonly=True, default='draft')
	partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('saletarget.sequence') or _('New')
		result = super(SaleTarget, self).create(vals)
		return result

	def unlink(self):
		if self.state != 'draft':
			raise UserError(_('You can only delete an sales target in draft state.'))
		return super(SaleTarget, self).unlink()

	def confirm(self):
		count=0
		for i in self:
			if i.target <= 0:
				raise UserError("Target Must be Grater then 0.")
		for j in self.target_line_ids:
			count+=j.target_quantity
			if count > i.target:
				raise UserError("Target Quantity Must be same as Target or Less.")
		return self.write({'state':'open'})

	def close(self):
		return self.write({'state':'closed'})

	def cancel(self):
		return self.write({'state':'cancelled'})


	@api.depends('target_line_ids','target_line_ids.achieve_quantity')
	def _compute_sales_target(self):
		for record in self:
			record.achieve = sum([line.achieve_quantity for line in record.target_line_ids])

	@api.depends('achieve','target')
	def _get_achieve_percentage(self):
		for record in self:
			try:
				record.achieve_percentage=record.achieve * 100/record.target
			except ZeroDivisionError:
				return record.achieve_percentage

	@api.depends('achieve','target')                   
	def _get_difference(self):
		self.difference=self.target - self.achieve

	def send_mail(self):
		template_id = self.env['ir.model.data'].get_object_reference('salesperson_sales_target_app','sales_person_send_mail')[1]
		email_template_obj = self.env['mail.template'].browse(template_id)
		if template_id:
			values = email_template_obj.generate_email(self.id, fields=None)
			values['email_from'] = self.env.user.email
			values['email_to'] = self.sales_person_id.partner_id.email
			values['author_id'] = self.env.user.partner_id.id
			mail_mail_obj = self.env['mail.mail']
			msg_id = mail_mail_obj.sudo().create(values)
			if msg_id:
				msg_id.sudo().send()


class TargetLine(models.Model):
	_name="targetline.targetline"
	_description= "Sales Target Line"

	name = fields.Char(string="Name")
	reverse_id = fields.Many2one('saletarget.saletarget')
	product_id = fields.Many2one('product.product', string="Product", required=True)
	target_quantity = fields.Integer(string="Target Quantity", required=True)
	achieve_quantity = fields.Integer(string="Achieve Quantity", readonly=True)
	achieve_perc = fields.Integer(string="Achieve Percentage",compute="_get_percentage",store=True)
	   
	@api.depends('target_quantity','achieve_quantity')                   
	def _get_percentage(self):
		for temp in self:
			try:
				temp.achieve_perc=temp.achieve_quantity * 100/temp.target_quantity
			except ZeroDivisionError:
				return temp.achieve_perc

