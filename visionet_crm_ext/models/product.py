
from odoo import models, api, fields, _

class DepartmentProduct(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template Product Form'

    department = fields.Many2one('crm.team', string="Department")
