from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fal_active_milestone_cron = fields.Boolean(
        string='Run milestone by scheduled actions', default=True
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        fal_active_milestone_cron = ICPSudo.get_param(
            'fal_invoice_milestone.fal_active_milestone_cron')
        res.update(
            fal_active_milestone_cron=fal_active_milestone_cron,
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param(
            "fal_invoice_milestone.fal_active_milestone_cron",
            self.fal_active_milestone_cron)
        return res
