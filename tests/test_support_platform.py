# -*- coding: utf-8 -*-
"""QA regression tests for the IT Support Platform (support.* models in `website`).

Run (isolated DB copy only):
    ./odoo-bin -c qa.conf -d <qa_db> -u website --test-tags /website:support_qa --stop-after-init

All times below are UTC (naive) as stored by Odoo. The test calendar is
Sunday-Thursday 08:00-16:00 Asia/Riyadh (UTC+3), i.e. 05:00-13:00 UTC.
Expected SLA hours come from BRD §4.4 (SLA Policy table).
"""
import json
from datetime import datetime

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

DT = datetime.fromisoformat
REJECTED = UserError  # AccessError and ValidationError subclass UserError in 17.0


class SupportQACommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, mail_notrack=True))
        work_days = ['6', '0', '1', '2', '3']  # Sunday..Thursday
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'QA Sun-Thu 08-16 Riyadh',
            'tz': 'Asia/Riyadh',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'name': f'd{d}', 'dayofweek': d, 'hour_from': 8, 'hour_to': 16, 'day_period': 'morning'})
                for d in work_days
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar
        cls.env['support.sla.policy'].search([]).write({'calendar_id': cls.calendar.id})
        emp_groups = 'base.group_user,website.group_support_employee'
        mgr_groups = 'base.group_user,website.group_support_manager'
        cls.emp1 = new_test_user(cls.env, 'qa_t_emp1', groups=emp_groups, email='qa_t_emp1@example.test', tz='Asia/Riyadh')
        cls.emp2 = new_test_user(cls.env, 'qa_t_emp2', groups=emp_groups, email='qa_t_emp2@example.test', tz='Asia/Riyadh')
        cls.mgr1 = new_test_user(cls.env, 'qa_t_mgr1', groups=mgr_groups, email='qa_t_mgr1@example.test', tz='Asia/Riyadh')
        cls.mgr2 = new_test_user(cls.env, 'qa_t_mgr2', groups=mgr_groups, email='qa_t_mgr2@example.test', tz='Asia/Riyadh')
        cls.cat_tech = cls.env.ref('website.support_category_technical')
        cls.cat_inquiry = cls.env.ref('website.support_category_consultation')
        cls.cat_service = cls.env.ref('website.support_category_service')

    # helpers emulating what the controllers do -------------------------
    def _submit(self, when, category=None, priority='medium', user=None):
        user = user or self.emp1
        with freeze_time(when):
            # mirrors the controller: validated server-side, then created under sudo() as the same uid
            ticket = self.env['support.ticket'].with_user(user).sudo().create({
                'title': 'QA ticket',
                'description': 'QA description',
                'category_id': (category or self.cat_tech).id,
                'priority': priority,
                'status': 'new',
                'ticket_number': self.env['ir.sequence'].sudo().next_by_code('support.ticket'),
                'requester_id': user.id,
                'submitted_at': fields.Datetime.now(),
            })
            ticket.sudo()._apply_sla_policy()
        return ticket

    def _claim(self, ticket, when, mgr=None):
        mgr = mgr or self.mgr1
        with freeze_time(when):
            now = fields.Datetime.now()
            ticket.sudo().write({
                'assignee_id': mgr.id,
                'status': 'processing',
                'first_response_at': now,
                'sla_response_status': 'successful' if now <= ticket.sla_response_deadline else 'failed',
            })

    def _solve(self, ticket, when):
        with freeze_time(when):
            now = fields.Datetime.now()
            ticket.sudo().write({
                'solution': 'QA solution',
                'solution_at': now,
                'status': 'waiting_confirmation',
                'sla_resolution_status': 'successful' if now <= ticket.sla_resolution_deadline else 'failed',
            })

    def _reopen(self, ticket, when):
        with freeze_time(when):
            ticket.sudo().write({
                'status': 'processing',
                'sla_resolution_status': 'in_progress',
                'reopen_count': ticket.reopen_count + 1,
            })


@tagged('post_install', '-at_install', 'support_qa')
class TestSupportSLA(SupportQACommon):

    def test_00_dates_are_expected_weekdays(self):
        self.assertEqual(DT('2026-10-04').weekday(), 6)  # Sunday
        self.assertEqual(DT('2026-10-08').weekday(), 3)  # Thursday

    def test_01_deadline_same_and_next_day(self):
        # Sunday 09:00 local, technical/medium = 2h response, 8h resolution
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')
        self.assertEqual(t.sla_response_hours, 2)
        self.assertEqual(t.sla_resolution_hours, 8)
        self.assertEqual(t.sla_response_deadline, DT('2026-10-04 08:00:00'))     # Sun 11:00 local
        self.assertEqual(t.sla_resolution_deadline, DT('2026-10-05 06:00:00'))   # Mon 09:00 local

    def test_02_deadline_skips_weekend(self):
        # Thursday 15:00 local, inquiry/medium = 1h / 4h
        t = self._submit('2026-10-08 12:00:00', self.cat_inquiry, 'medium')
        self.assertEqual(t.sla_response_deadline, DT('2026-10-08 13:00:00'))     # Thu 16:00 local
        self.assertEqual(t.sla_resolution_deadline, DT('2026-10-11 08:00:00'))   # Sun 11:00 local

    def test_03_submitted_outside_working_hours(self):
        # Friday 10:00 local (weekend) -> clock starts Sunday 08:00; technical/high = 1h / 4h
        t = self._submit('2026-10-09 07:00:00', self.cat_tech, 'high')
        self.assertEqual(t.sla_response_deadline, DT('2026-10-11 06:00:00'))     # Sun 09:00 local
        self.assertEqual(t.sla_resolution_deadline, DT('2026-10-11 09:00:00'))   # Sun 12:00 local

    def test_04_public_holiday_is_skipped(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'QA holiday', 'calendar_id': self.calendar.id, 'time_type': 'leave',
            'date_from': DT('2026-10-11 05:00:00'), 'date_to': DT('2026-10-11 13:00:00'),
        })
        t = self._submit('2026-10-08 12:00:00', self.cat_inquiry, 'medium')
        self.assertEqual(t.sla_resolution_deadline, DT('2026-10-12 08:00:00'))   # Mon 11:00 local

    def test_05_policy_matrix_matches_brd(self):
        expected = {
            ('support_category_consultation', 'medium'): (1, 4), ('support_category_consultation', 'low'): (2, 8),
            ('support_category_technical', 'high'): (1, 4), ('support_category_technical', 'medium'): (2, 8),
            ('support_category_technical', 'low'): (4, 16), ('support_category_service', 'high'): (2, 8),
            ('support_category_service', 'medium'): (4, 16), ('support_category_service', 'low'): (8, 24),
            ('support_category_requirements', 'high'): (4, 16), ('support_category_requirements', 'medium'): (8, 24),
            ('support_category_requirements', 'low'): (8, 40),
        }
        for (xmlid, prio), (resp, res) in expected.items():
            pol = self.env['support.sla.policy'].search([('category_id', '=', self.env.ref(f'website.{xmlid}').id), ('priority', '=', prio)])
            self.assertEqual(len(pol), 1, (xmlid, prio))
            self.assertEqual((pol.response_hours, pol.resolution_hours), (resp, res), (xmlid, prio))

    def test_06_inquiry_high_priority_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit('2026-10-04 06:00:00', self.cat_inquiry, 'high')

    def test_06b_inquiry_rule_survives_category_rename(self):
        """DEF-11: the inquiry/high rule must not depend on the display name."""
        self.cat_inquiry.name = 'استفسار عام'
        with self.assertRaises(ValidationError):
            self._submit('2026-10-04 06:00:00', self.cat_inquiry, 'high')

    def test_07_draft_has_no_sla(self):
        t = self.env['support.ticket'].with_user(self.emp1).create({'title': 'draft', 'status': 'draft'})
        t.sudo()._apply_sla_policy()
        self.assertFalse(t.sla_policy_id)
        self.assertFalse(t.sla_resolution_deadline)

    def test_08_pause_resume_extends_resolution_deadline(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')  # resolution Mon 09:00 local
        self._claim(t, '2026-10-04 06:30:00')
        with freeze_time('2026-10-04 07:00:00'):   # Sun 10:00 local
            t.with_user(self.mgr1).pause_resolution_sla('waiting_employee')
        self.assertEqual(t.status, 'on_hold')
        with freeze_time('2026-10-04 10:00:00'):   # Sun 13:00 local -> 3 working hours paused
            t.with_user(self.mgr1).resume_resolution_sla()
        self.assertEqual(t.status, 'processing')
        self.assertAlmostEqual(t.sla_paused_hours, 3.0, places=2)
        self.assertEqual(t.sla_resolution_deadline, DT('2026-10-05 09:00:00'))  # Mon 12:00 local

    def test_09_pause_overnight_counts_only_working_hours(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')
        self._claim(t, '2026-10-04 06:30:00')
        with freeze_time('2026-10-04 12:00:00'):   # Sun 15:00 local
            t.with_user(self.mgr1).pause_resolution_sla('waiting_internal')
        with freeze_time('2026-10-05 06:00:00'):   # Mon 09:00 local
            t.with_user(self.mgr1).resume_resolution_sla()
        self.assertAlmostEqual(t.sla_paused_hours, 2.0, places=2)

    def test_10_reopen_resumes_resolution_clock(self):
        """FR-SYS-12/15: after reopen the resolution SLA must keep counting."""
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')  # 8h resolution
        self._claim(t, '2026-10-04 06:10:00')
        self._solve(t, '2026-10-04 07:00:00')    # 1h used
        self._reopen(t, '2026-10-04 07:30:00')
        with freeze_time('2026-10-04 12:00:00'):  # 6 working hours after submission
            metrics = t.get_sla_metrics('resolution')
        self.assertGreaterEqual(metrics['percent'], 70.0,
                                'SLA percentage frozen at the previous solution time after reopen')

    def test_11_cron_raises_alert_levels_and_breach(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')  # response deadline 08:00 UTC
        with freeze_time('2026-10-04 07:35:00'):  # 79% of 2h
            self.env['support.ticket']._cron_update_sla_statuses()
        self.assertEqual(t.sla_response_alert_level, 75)
        with freeze_time('2026-10-04 07:50:00'):  # 91%
            self.env['support.ticket']._cron_update_sla_statuses()
        self.assertEqual(t.sla_response_alert_level, 90)
        with freeze_time('2026-10-04 08:05:00'):
            self.env['support.ticket']._cron_update_sla_statuses()
        self.assertEqual(t.sla_response_status, 'failed')
        self.assertEqual(t.sla_response_alert_level, 100)

    def test_13_module_declares_hr_dependency(self):
        website = self.env['ir.module.module'].search([('name', '=', 'website')])
        self.assertIn('hr', website.dependencies_id.mapped('name'),
                      'support.ticket uses hr.department / hr.employee but website does not depend on hr')

    def test_14_working_day_boundaries(self):
        # Sunday 16:00 local (end of day), technical/high 1h -> Monday 09:00 local
        t = self._submit('2026-10-04 13:00:00', self.cat_tech, 'high')
        self.assertEqual(t.sla_response_deadline, DT('2026-10-05 06:00:00'))
        # Sunday 07:30 local (before opening) -> clock starts 08:00, 1h -> 09:00 local
        t2 = self._submit('2026-10-04 04:30:00', self.cat_tech, 'high')
        self.assertEqual(t2.sla_response_deadline, DT('2026-10-04 06:00:00'))

    def test_15_late_claim_breaches_response(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')   # response deadline 08:00 UTC
        self._claim(t, '2026-10-04 08:30:00')
        self.assertEqual(t.sla_response_status, 'failed')

    def test_16_late_solution_breaches_resolution(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_inquiry, 'medium')  # 4h -> 10:00 UTC
        self._claim(t, '2026-10-04 06:30:00')
        self._solve(t, '2026-10-04 10:30:00')
        self.assertEqual(t.sla_resolution_status, 'failed')

    def test_17_cron_resolution_alerts(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_inquiry, 'medium')  # resolution 4h -> 10:00 UTC
        self._claim(t, '2026-10-04 06:10:00')
        for when, level in [('2026-10-04 09:05:00', 75), ('2026-10-04 09:40:00', 90), ('2026-10-04 10:05:00', 100)]:
            with freeze_time(when):
                self.env['support.ticket']._cron_update_sla_statuses()
            self.assertEqual(t.sla_resolution_alert_level, level, when)
        self.assertEqual(t.sla_resolution_status, 'failed')
        alerts = self.env['mail.message'].sudo().search([('model', '=', 'support.ticket'), ('res_id', '=', t.id), ('subject', 'ilike', 'SLA الحل')])
        self.assertEqual(len(alerts), 3)
        self.assertIn(self.mgr1.partner_id, alerts.mapped('partner_ids'), 'alerts go to the assignee')

    def test_18_no_breach_while_on_hold(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_inquiry, 'medium')  # resolution 10:00 UTC
        self._claim(t, '2026-10-04 06:10:00')
        with freeze_time('2026-10-04 07:00:00'):
            t.with_user(self.mgr1).pause_resolution_sla('scheduled')
        with freeze_time('2026-10-05 12:00:00'):   # far beyond the original deadline
            self.env['support.ticket']._cron_update_sla_statuses()
        self.assertEqual(t.sla_resolution_status, 'in_progress')

    def test_19_paused_hours_excluded_from_percent(self):
        t = self._submit('2026-10-04 06:00:00', self.cat_tech, 'medium')  # 8h
        self._claim(t, '2026-10-04 06:10:00')
        with freeze_time('2026-10-04 07:00:00'):
            t.with_user(self.mgr1).pause_resolution_sla('waiting_employee')
        with freeze_time('2026-10-04 09:00:00'):
            t.with_user(self.mgr1).resume_resolution_sla()
        with freeze_time('2026-10-04 10:00:00'):   # 4h elapsed - 2h paused = 2h used -> 25%
            metrics = t.get_sla_metrics('resolution')
        self.assertAlmostEqual(metrics['percent'], 25.0, delta=0.5)

    def _metrics_for(self, tickets):
        """Batch helper when available, otherwise the per-ticket path the controller used before."""
        batch = getattr(tickets, '_get_sla_metrics_batch', None)
        if batch:
            return batch()
        return {t.id: {k: t.get_sla_metrics(k) for k in ('response', 'resolution')} for t in tickets}

    def _varied_tickets(self, count):
        tickets = self.env['support.ticket']
        for i in range(count):
            day = 4 + (i % 4)                       # Sun..Wed
            t = self._submit(f'2026-10-0{day} 06:00:00', self.cat_tech, ['low', 'medium', 'high'][i % 3])
            kind = i % 5
            if kind >= 1:
                self._claim(t, f'2026-10-0{day} 06:30:00')
            if kind == 2:
                with freeze_time(f'2026-10-0{day} 07:00:00'):
                    t.with_user(self.mgr1).pause_resolution_sla('waiting_internal')
            if kind in (3, 4):
                self._solve(t, f'2026-10-0{day} 09:00:00')
            if kind == 4:
                self._reopen(t, f'2026-10-0{day} 10:00:00')
            tickets |= t
        return tickets

    def test_20_batch_metrics_equal_individual(self):
        """PERF-01 fix must not change any SLA number."""
        tickets = self._varied_tickets(15)
        with freeze_time('2026-10-08 11:00:00'):
            batch = self._metrics_for(tickets)
            for t in tickets:
                for kind in ('response', 'resolution'):
                    self.assertEqual(batch[t.id][kind], t.get_sla_metrics(kind), (t.ticket_number, kind))

    def test_21_sla_metrics_queries_do_not_grow_per_ticket(self):
        """PERF-01: no N+1 - SQL count for 25 tickets ~ count for 5 tickets."""
        few = self._varied_tickets(5)
        many = few | self._varied_tickets(20)
        with freeze_time('2026-10-08 11:00:00'):
            self.env.invalidate_all()
            before = self.cr.sql_log_count
            self._metrics_for(few)
            q_few = self.cr.sql_log_count - before
            self.env.invalidate_all()
            before = self.cr.sql_log_count
            self._metrics_for(many)
            q_many = self.cr.sql_log_count - before
        self.assertLess(q_many - q_few, 15, f'queries grew from {q_few} to {q_many} for 20 extra tickets')

    def test_12_sla_cron_is_scheduled(self):
        """FR-SYS-18/19: breach detection and near-breach alerts must run automatically."""
        crons = self.env['ir.cron'].sudo().with_context(active_test=False).search([
            ('model_id.model', '=', 'support.ticket'),
        ])
        self.assertTrue(any('_cron_update_sla_statuses' in (c.code or '') and c.active for c in crons),
                        'No active ir.cron calls support.ticket._cron_update_sla_statuses')


@tagged('post_install', '-at_install', 'support_qa')
class TestSupportSecurity(SupportQACommon):

    def test_01_employee_isolation(self):
        t = self._submit('2026-10-04 06:00:00')
        self.assertFalse(self.env['support.ticket'].with_user(self.emp2).search([('id', '=', t.id)]))
        with self.assertRaises(AccessError):
            t.with_user(self.emp2).read(['title'])

    def test_02_manager_cannot_see_drafts(self):
        d = self.env['support.ticket'].with_user(self.emp1).create({'title': 'draft', 'status': 'draft'})
        self.assertFalse(self.env['support.ticket'].with_user(self.mgr1).search([('id', '=', d.id)]))

    def test_03_invalid_transition_rejected_even_for_sudo(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(ValidationError):
            t.sudo().write({'status': 'closed'})

    def test_04_employee_cannot_self_claim(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.emp1).write({'assignee_id': self.emp1.id, 'status': 'processing',
                                         'first_response_at': fields.Datetime.now()})

    def test_05_employee_cannot_change_requester(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.emp1).write({'requester_id': self.emp2.id})

    def test_06_employee_cannot_tamper_sla_fields(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.emp1).write({'sla_response_status': 'successful'})

    def test_07_employee_cannot_hold_ticket(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.emp1).pause_resolution_sla('waiting_employee')

    def test_08_manager_cannot_close_for_employee(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00')
        self._solve(t, '2026-10-04 07:00:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.mgr1).write({'status': 'closed', 'closed_at': fields.Datetime.now()})

    def test_09_other_manager_cannot_overwrite_solution(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.mgr2).write({'assignee_id': self.mgr2.id, 'solution': 'hijack'})

    def test_10_employee_cannot_edit_submitted_content(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(REJECTED):
            t.with_user(self.emp1).write({'description': 'changed after submission'})

    def test_11_rating_only_for_closed_own_ticket(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(REJECTED):
            self.env['support.rating'].with_user(self.emp1).create({'ticket_id': t.id, 'rating': '1'})

    def test_11b_rating_rated_by_cannot_be_spoofed(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00')
        self._solve(t, '2026-10-04 07:00:00')
        t.sudo().write({'status': 'closed', 'closed_at': fields.Datetime.now()})
        with self.assertRaises(REJECTED):
            self.env['support.rating'].with_user(self.emp1).create({'ticket_id': t.id, 'rating': '5', 'rated_by': self.mgr1.id})

    def test_11c_employee_cannot_rpc_create_submitted_ticket(self):
        with self.assertRaises(REJECTED):
            self.env['support.ticket'].with_user(self.emp1).create({
                'title': 'x', 'description': 'y', 'category_id': self.cat_tech.id, 'priority': 'low',
                'status': 'new', 'ticket_number': 'REQ-FAKE', 'submitted_at': fields.Datetime.now()})

    def test_11d_employee_can_still_edit_own_draft(self):
        d = self.env['support.ticket'].with_user(self.emp1).create({'title': 'draft', 'status': 'draft', 'requester_id': self.emp1.id})
        d.with_user(self.emp1).write({'title': 'draft 2', 'description': 'desc', 'priority': 'low', 'status': 'draft', 'requester_id': self.emp1.id})
        self.assertEqual(d.title, 'draft 2')

    def test_11e_other_manager_cannot_hold(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00', mgr=self.mgr1)
        with self.assertRaises(REJECTED):
            t.with_user(self.mgr2).pause_resolution_sla('waiting_employee')

    def test_11f_access_layers_are_native(self):
        """DEF-01/02 defence in depth: ACL + ir.rule, not only Python checks."""
        Ticket = self.env['support.ticket']
        self.assertFalse(Ticket.with_user(self.mgr1).check_access_rights('write', raise_exception=False),
                         'support managers must not have direct write ACL on tickets')
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(AccessError):
            t.with_user(self.emp1).check_access_rule('write')
        d = Ticket.with_user(self.emp1).create({'title': 'draft', 'status': 'draft'})
        d.with_user(self.emp1).check_access_rule('write')   # own draft stays writable

    def test_12_rating_unique(self):
        t = self._submit('2026-10-04 06:00:00')
        self._claim(t, '2026-10-04 06:30:00')
        self._solve(t, '2026-10-04 07:00:00')
        t.sudo().write({'status': 'closed', 'closed_at': fields.Datetime.now()})
        self.env['support.rating'].with_user(self.emp1).create({'ticket_id': t.id, 'rating': '5'})
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['support.rating'].with_user(self.emp1).create({'ticket_id': t.id, 'rating': '4'})

    def test_13_history_not_writable_by_users(self):
        t = self._submit('2026-10-04 06:00:00')
        with self.assertRaises(AccessError):
            self.env['support.ticket.history'].with_user(self.emp1).create({'ticket_id': t.id, 'action': 'forged'})

    def test_14_category_in_use_cannot_be_deleted(self):
        self._submit('2026-10-04 06:00:00')
        with self.assertRaises(Exception), self.cr.savepoint():
            self.cat_tech.unlink()


@tagged('post_install', '-at_install', 'support_qa')
class TestSupportHttp(HttpCase):

    def setUp(self):
        super().setUp()
        groups = 'base.group_user,website.group_support_employee'
        self.emp = new_test_user(self.env, 'qa_h_emp', groups=groups, email='qa_h_emp@example.test', password='qa_h_emp_pwd_1')
        self.emp_noemail = new_test_user(self.env, 'qa_h_noemail', groups=groups, password='qa_h_noemail_pwd_1')
        self.emp_noemail.email = False
        new_test_user(self.env, 'qa_h_mgr', groups='base.group_user,website.group_support_manager', email='qa_h_mgr@example.test')

    def _create(self, login, password, **values):
        self.authenticate(login, password)
        token = json.loads(self.url_open('/support/csrf').text)['csrf_token']
        data = {'title': 'HTTP QA', 'description': 'desc', 'category': 'مشكلة تقنية', 'priority': 'medium', 'csrf_token': token}
        data.update(values)
        return self.url_open('/support/ticket/create', data=data)

    def test_01_create_returns_json_and_persists(self):
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['success'])
        t = self.env['support.ticket'].sudo().browse(body['ticket_id'])
        self.assertEqual(t.status, 'new')
        self.assertEqual(t.ticket_number, body['ticket_number'])

    def test_02_business_rule_error_keeps_json_contract(self):
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1', category='استفسار', priority='high')
        self.assertEqual(r.status_code, 400)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        self.assertFalse(r.json()['success'])

    def test_03_employee_without_email_can_create(self):
        r = self._create('qa_h_noemail', 'qa_h_noemail_pwd_1')
        self.assertEqual(r.status_code, 200, r.text[:200])

    def _json(self, login, password, path, payload):
        self.authenticate(login, password)
        token = json.loads(self.url_open('/support/csrf').text)['csrf_token']
        return self.url_open(f'{path}?csrf_token={token}', data=json.dumps(payload),
                             headers={'Content-Type': 'application/json'})

    def test_04_full_lifecycle_via_endpoints(self):
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1')
        number = r.json()['ticket_number']
        mgr = ('qa_h_mgr', 'qa_h_mgr')
        emp = ('qa_h_emp', 'qa_h_emp_pwd_1')
        steps = [
            (mgr, '/support/ticket/claim', {'ticket_number': number}, 'processing'),
            (mgr, '/support/ticket/hold', {'ticket_number': number, 'reason': 'waiting_employee'}, 'on_hold'),
            (mgr, '/support/ticket/resume', {'ticket_number': number}, 'processing'),
            (mgr, '/support/ticket/solution', {'ticket_number': number, 'solution': 'حل'}, 'waiting_confirmation'),
            (emp, '/support/ticket/employee-action', {'ticket_number': number, 'action': 'reopen'}, 'processing'),
            (mgr, '/support/ticket/solution', {'ticket_number': number, 'solution': 'حل نهائي'}, 'waiting_confirmation'),
            (emp, '/support/ticket/employee-action', {'ticket_number': number, 'action': 'confirm'}, 'closed'),
        ]
        ticket = self.env['support.ticket'].sudo().search([('ticket_number', '=', number)])
        for (login, pwd), path, payload, expected in steps:
            res = self._json(login, pwd, path, payload)
            self.assertEqual(res.status_code, 200, f'{path}: {res.text[:200]}')
            ticket.invalidate_recordset()
            self.assertEqual(ticket.status, expected, path)
        res = self._json(*emp, '/support/ticket/rating', {'ticket_number': number, 'rating': 5})
        self.assertEqual(res.status_code, 200, res.text[:200])
        self.assertEqual(ticket.reopen_count, 1)
        self.assertEqual(
            self.env['support.ticket.history'].sudo().search([('ticket_id', '=', ticket.id)], order='id').mapped('action'),
            ['create', 'claim', 'hold', 'resume', 'solution', 'reopen', 'solution', 'close', 'rating'])

    def test_05_failed_request_rolls_back_and_returns_json(self):
        """DEF-07: a business-rule error must not leave a partial ticket and must keep the JSON contract."""
        title = 'QA rollback probe 7f3a'
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1', title=title, category='استفسار', priority='high')
        self.assertEqual(r.status_code, 400)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        self.assertFalse(self.env['support.ticket'].sudo().search([('title', '=', title)]))

    def test_06_session_expired_json_route_redirects_to_login(self):
        """DEF-08 (server side): anonymous calls get the Odoo login redirect, never data."""
        self.authenticate(None, None)
        r = self.url_open('/support/manager/tickets', allow_redirects=False)
        self.assertIn(r.status_code, (302, 303))
        self.assertIn('/web/login', r.headers.get('Location', ''))
        self.assertNotIn('"tickets"', r.text)  # no JSON payload, only the login redirect

    def test_07_frontend_handles_session_expiry(self):
        """DEF-08 (client side): both fetch wrappers detect the login redirect."""
        from odoo.tools.misc import file_open
        for path in ('website/static/src/js/employee.js', 'website/static/src/js/support.js'):
            with file_open(path) as f:
                self.assertIn('redirectIfSessionExpired', f.read(), path)

    def test_08_hold_reason_kept_in_history(self):
        """DEF-10 / FR-SUP-10: the hold reason stays traceable after resume."""
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1')
        number = r.json()['ticket_number']
        mgr = ('qa_h_mgr', 'qa_h_mgr')
        for path, payload in [('/support/ticket/claim', {'ticket_number': number}),
                              ('/support/ticket/hold', {'ticket_number': number, 'reason': 'waiting_approval'}),
                              ('/support/ticket/resume', {'ticket_number': number})]:
            self.assertEqual(self._json(*mgr, path, payload).status_code, 200, path)
        hold = self.env['support.ticket.history'].sudo().search(
            [('ticket_id.ticket_number', '=', number), ('action', '=', 'hold')])
        self.assertIn('بانتظار موافقة', hold.note)

    def test_09_rejected_request_does_not_consume_ticket_number(self):
        """DEF-12: validation failures must not burn reference numbers."""
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'support.ticket')], limit=1)
        before = seq.number_next_actual
        r = self._create('qa_h_emp', 'qa_h_emp_pwd_1', priority='urgent')
        self.assertEqual(r.status_code, 400)
        seq.invalidate_recordset()
        self.assertEqual(seq.number_next_actual, before)

    def test_10_no_debug_print_of_form_data(self):
        """DEF-09: submitted form data must not be printed to the server output."""
        from odoo.tools.misc import file_open
        with file_open('website/controllers/support.py') as f:
            self.assertNotIn('print(', f.read())

    def test_11_analytics_match_database(self):
        """FR-SYS-20: dashboard KPIs equal an independent ORM computation; no ratings -> None."""
        from dateutil.relativedelta import relativedelta
        self.authenticate('qa_h_mgr', 'qa_h_mgr')
        kpis = self.url_open('/support/analytics').json()['kpis']
        mgr = self.env['res.users'].search([('login', '=', 'qa_h_mgr')])
        today = fields.Date.context_today(mgr)
        start = fields.Datetime.to_datetime(today.replace(day=1) - relativedelta(months=5))
        tickets = self.env['support.ticket'].sudo().search([('status', '!=', 'draft'), ('submitted_at', '>=', start)])
        ratings = self.env['support.rating'].sudo().search([('ticket_id', 'in', tickets.ids)])
        self.assertEqual(kpis['total_tickets'], len(tickets))
        self.assertEqual(kpis['open_tickets'], len(tickets.filtered(lambda t: t.status != 'closed')))
        self.assertEqual(kpis['breached_tickets'], len(tickets.filtered(
            lambda t: 'failed' in (t.sla_response_status, t.sla_resolution_status))))
        expected_avg = round(sum(int(r.rating) for r in ratings) / len(ratings), 2) if ratings else None
        self.assertEqual(kpis['average_rating'], expected_avg)
        self.assertEqual(kpis['rated_tickets'], len(ratings))
        ratings.unlink()
        kpis = self.url_open('/support/analytics').json()['kpis']
        self.assertIsNone(kpis['average_rating'])
        self.assertEqual(kpis['rated_tickets'], 0)

    def test_12_empty_months_are_null_not_zero(self):
        """UI-07 / FR-SYS-20: a month without data must not be reported as 0% compliance or 0 h."""
        from dateutil.relativedelta import relativedelta
        self.authenticate('qa_h_mgr', 'qa_h_mgr')
        charts = self.url_open('/support/analytics').json()['charts']
        mgr = self.env['res.users'].search([('login', '=', 'qa_h_mgr')])
        Ticket = self.env['support.ticket'].sudo()
        checked = 0
        for label, trend, resp in zip(charts['trend']['labels'], charts['trend']['values'], charts['response_time']['values']):
            year, month = map(int, label.split('-'))
            start = fields.Datetime.to_datetime(f'{year}-{month:02d}-01') - relativedelta(hours=3)
            end = start + relativedelta(months=1)
            if not Ticket.search_count([('status', '!=', 'draft'), ('submitted_at', '>=', start), ('submitted_at', '<', end)]):
                self.assertIsNone(trend, f'{label}: no tickets but compliance={trend}')
                self.assertIsNone(resp, f'{label}: no tickets but response={resp}')
                checked += 1
        if not checked:
            self.skipTest('every month in the window has tickets - nothing to verify')

    def test_13_frontend_rtl_and_rating_markup(self):
        """UI-01 (bidi isolation of name/date) and UI-02 (rating scale + accessible label)."""
        from odoo.tools.misc import file_open
        for path in ('website/static/src/js/employee.js', 'website/static/src/js/support.js'):
            with file_open(path) as f:
                self.assertIn('<small class="solution-meta"><bdi>', f.read(), path)
        with file_open('website/static/src/js/employee.js') as f:
            self.assertIn('aria-label="التقييم', f.read())


@tagged('post_install', '-at_install', 'support_qa')
class TestSupportControllerContract(TransactionCase):

    def test_01_concurrency_errors_reach_odoo_retry(self):
        """DEF-07b: the JSON error wrapper must let PostgreSQL concurrency errors
        propagate so Odoo's native retry (service.model.retrying) can resolve them."""
        import psycopg2
        from psycopg2 import errorcodes
        from odoo.addons.website.controllers import support as support_ctrl
        wrapper = getattr(support_ctrl, '_json_errors', None)
        if wrapper is None:
            self.skipTest('no JSON error wrapper in this version (not applicable)')

        class SerializationFailure(psycopg2.extensions.TransactionRollbackError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        def endpoint(_self):
            raise SerializationFailure('could not serialize access due to concurrent update')

        with self.assertRaises(psycopg2.OperationalError):
            wrapper(endpoint)(None)
