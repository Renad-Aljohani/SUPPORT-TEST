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
            ticket = self.env['support.ticket'].with_user(user).create({
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
