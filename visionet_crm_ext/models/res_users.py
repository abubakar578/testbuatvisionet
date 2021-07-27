from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'


    team_member_ids = fields.Many2many('res.users', 'res_users_2_rel', 'sales_person', string='Members', compute='_get_member')
    total_target = fields.Monetary(string='Total', store=True, compute='_total_target')
    visionet_target_ids = fields.One2many('visionet.target', 'user_id', string="Visionet Target(s)")
    is_last_member =  fields.Boolean(string="Is last member?", compute='_get_member')
    invoice_term_line_ids = fields.One2many('fal.invoice.term.line', 'rel_user_id', string="Invoice Term Line(s)")

    @api.depends('visionet_target_ids.target')
    def _total_target(self):
        for target in self:
            total_target = 0.0
            for line in target.visionet_target_ids:
                total_target += line.target
            target.update({
                'total_target': total_target,
            })

    def _get_member(self):
        for user in self:
            team_obj = self.env['crm.team']
            users = []
            # Di sini, kita ingin lihat, apakah user ini merupakan team leader?
            # Kalau team leader, ta usah lah dia tengok kanan kiri
            # Tapi search saya ini, harus SUDO dong.... Oke!
            admin = self.env.ref('base.user_admin')
            team = team_obj.with_user(admin).search([('user_id', '=', user.id)], limit=1)
            if team:
                user.is_last_member = False
                teams = team_obj.search([('id', 'child_of', team.id)])
                team_members = [member.id for member_team in teams for member in member_team.member_ids]
                team_members += [member_team.user_id.id for member_team in teams]
                user.team_member_ids = [(6, 0, team_members)]
            # Di sini, kita tahu bahwa dia paling rendah
            # Wajiblah kita tengok kanan kiri dia
            else:
                user.is_last_member = True
                team = team_obj.with_user(admin).search([('member_ids', '=', user.id)], limit=1)
                user.team_member_ids = [(6, 0, team.member_ids.ids)]

    def action_query(self):
        for user in self:
            for target in user.visionet_target_ids:
                target.push_to_googlebq()
