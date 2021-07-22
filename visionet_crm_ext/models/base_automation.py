import datetime
import logging
import traceback
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hour': lambda interval: relativedelta(hours=interval),
    'day': lambda interval: relativedelta(days=interval),
    'month': lambda interval: relativedelta(months=interval),
    False: lambda interval: relativedelta(0),
}

DATE_RANGE_FACTOR = {
    'minutes': 1,
    'hour': 60,
    'day': 24 * 60,
    'month': 30 * 24 * 60,
    False: 0,
}


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    def _process(self, records, domain_post=None):
        """ Process action ``self`` on the ``records`` that have not been done yet. """
        # filter out the records on which self has already been done
        action_done = self._context['__action_done']
        records_done = action_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        # mark the remaining records as done (to avoid recursive processing)
        action_done = dict(action_done)
        action_done[self] = records_done + records
        self = self.with_context(__action_done=action_done)
        records = records.with_context(__action_done=action_done)

        # modify records
        values = {}
        if 'date_action_last' in records._fields:
            values['date_action_last'] = fields.Datetime.now()
        if values:
            admin = self.env.ref('base.user_admin')
            records.with_user(admin).write(values)

        # execute server actions
        if self.action_server_id:
            for record in records:
                # we process the action if any watched field has been modified
                if self._check_trigger_fields(record):
                    ctx = {
                        'active_model': record._name,
                        'active_ids': record.ids,
                        'active_id': record.id,
                        'domain_post': domain_post,
                    }
                    try:
                        self.action_server_id.sudo().with_context(**ctx).run()
                    except Exception as e:
                        self._add_postmortem_action(e)
                        raise e
