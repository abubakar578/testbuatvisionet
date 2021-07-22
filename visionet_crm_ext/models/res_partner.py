from odoo import models, fields, api


class Partner(models.Model):
    _inherit = 'res.partner'

    is_lippo_group = fields.Boolean('Is Lippo Group')
    is_employee = fields.Boolean('Is Employee', default=False, compute='_compute_employe', store=True)

    @api.depends('user_ids')
    def _compute_employe(self):
        for partner in self:
            if partner.user_ids is not False:
                partner.is_employee = True
