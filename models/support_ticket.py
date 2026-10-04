from pytz import UTC
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import AccessError, ValidationError


class SupportTicket(models.Model):
    _name = 'support.ticket'
    _inherit = ['mail.thread']
    _description = 'Support Ticket'
    _order = 'create_date desc'
    _rec_name = 'ticket_number'
    _check_company_auto = True

    _ALLOWED_STATUS_TRANSITIONS = {
        'draft': {'new'},
        'new': {'processing'},
        'processing': {'on_hold', 'waiting_confirmation'},
        'on_hold': {'processing'},
        'waiting_confirmation': {'closed', 'processing'},
        'closed': set(),
    }

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    ticket_number = fields.Char(
        string='رقم الطلب',
        copy=False,
        readonly=True,
        index=True,
    )

    title = fields.Char(
        string='موضوع الطلب',
    )

    description = fields.Text(
        string='وصف المشكلة',
    )

    category_id = fields.Many2one(
        'support.category',
        string='التصنيف',
        ondelete='restrict',
        index=True,
    )

    priority = fields.Selection(
        [
            ('low', 'منخفضة'),
            ('medium', 'متوسطة'),
            ('high', 'عالية'),
        ],
        string='الأولوية',
        index=True,
    )

    status = fields.Selection(
        [
            ('draft', 'مسودة'),
            ('new', 'جديد'),
            ('processing', 'قيد المعالجة'),
            ('on_hold', 'معلق مؤقتًا'),
            ('waiting_confirmation', 'بانتظار تأكيد الموظف'),
            ('closed', 'مغلق'),
        ],
        string='الحالة',
        required=True,
        default='draft',
        tracking=True,
        index=True,
        copy=False,
    )

    requester_id = fields.Many2one(
        'res.users',
        string='صاحب الطلب',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )

    assignee_id = fields.Many2one(
        'res.users',
        string='مسؤول الدعم',
        tracking=True,
        index=True,
        copy=False,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='الإدارة',
        check_company=True,
    )

    solution = fields.Text(
        string='الحل',
        copy=False,
    )

    solution_at = fields.Datetime(
        string='تاريخ تسجيل الحل',
        copy=False,
    )

    closed_at = fields.Datetime(
        string='تاريخ الإغلاق',
        copy=False,
    )

    reopen_count = fields.Integer(
        string='عدد مرات إعادة الفتح',
        default=0,
        readonly=True,
        copy=False,
    )

    sla_pause_started_at = fields.Datetime(
        string='بداية إيقاف SLA',
        readonly=True,
        copy=False,
    )

    sla_pause_reason = fields.Selection(
        [
            ('waiting_employee', 'بانتظار الموظف'),
            ('waiting_approval', 'بانتظار موافقة'),
            ('waiting_internal', 'بانتظار جهة داخلية'),
            ('scheduled', 'بانتظار موعد مجدول'),
        ],
        string='سبب إيقاف SLA',
        readonly=True,
        copy=False,
    )

    sla_paused_hours = fields.Float(
        string='إجمالي ساعات إيقاف SLA',
        default=0.0,
        readonly=True,
        copy=False,
    )

    sla_pause_count = fields.Integer(
        string='عدد مرات إيقاف SLA',
        default=0,
        readonly=True,
        copy=False,
    )  

     
    submitted_at = fields.Datetime(
        string='تاريخ إرسال الطلب',
        readonly=True,
        copy=False,
        index=True,
    )
    
    sla_response_deadline = fields.Datetime(
        string='الموعد النهائي للاستجابة',
        readonly=True,
        copy=False,
    )

    sla_resolution_deadline = fields.Datetime(
        string='الموعد النهائي للحل',
        readonly=True,
        copy=False,
    )

    first_response_at = fields.Datetime(
        string='تاريخ الاستجابة الأولية (استلام الطلب)',
        readonly=True,
        copy=False,
    )

    sla_response_status = fields.Selection(
        [
            ('in_progress', 'قيد الانتظار'),
            ('successful', 'محقق'),
            ('failed', 'متجاوز'),
        ],
        string='حالة SLA الاستجابة',
        default='in_progress',
        readonly=True,
        copy=False,
    )

    sla_resolution_status = fields.Selection(
        [
            ('in_progress', 'قيد الانتظار'),
            ('successful', 'محقق'),
            ('failed', 'متجاوز'),
        ],
        string='حالة SLA الحل',
        default='in_progress',
        readonly=True,
        copy=False,
    )

    sla_response_alert_level = fields.Integer(
        string='مستوى تنبيه SLA الاستجابة',
        default=0,
        readonly=True,
        copy=False,
    )

    sla_resolution_alert_level = fields.Integer(
        string='مستوى تنبيه SLA الحل',
        default=0,
        readonly=True,
        copy=False,
    )

    sla_policy_id = fields.Many2one(
        'support.sla.policy',
        string='سياسة SLA',
        readonly=True,
        copy=False,
        ondelete='restrict',
        index=True,
    )

    sla_calendar_id = fields.Many2one(
        'resource.calendar',
        string='تقويم SLA المعتمد',
        readonly=True,
        copy=False,
    )

    sla_response_hours = fields.Float(
        string='ساعات SLA للاستجابة المعتمدة',
        readonly=True,
        copy=False,
    )

    sla_resolution_hours = fields.Float(
        string='ساعات SLA للحل المعتمدة',
        readonly=True,
        copy=False,
    )


    def _lock_for_update(self):
        """Lock tickets until the current transaction commits or rolls back."""
        ticket_ids = self.ids

        if ticket_ids:
            self.env.cr.execute(
                """
                    SELECT id
                      FROM support_ticket
                     WHERE id = ANY(%s)
                     ORDER BY id
                       FOR UPDATE
                """,
                [ticket_ids],
            )
            self.invalidate_recordset()

        return self

    @staticmethod
    def _normalize_text_values(values):
        normalized_values = dict(values)

        for field_name in (
            'ticket_number',
            'title',
            'description',
            'solution',
        ):
            value = normalized_values.get(field_name)
            if isinstance(value, str):
                normalized_values[field_name] = value.strip()

        return normalized_values

    # الحقول الوحيدة التي يملك المستخدم تعديلها مباشرة (ORM/JSON-RPC)،
    # وفقط على مسودته. كل ما عداها يتحكم به السيرفر عبر إجراءات الـcontroller
    # بعد التحقق من الدور والملكية والحالة (BR-04، BR-07..BR-15).
    _USER_DRAFT_FIELDS = frozenset({
        'title',
        'description',
        'category_id',
        'priority',
        'department_id',
    })

    _PROTECTED_FIELDS = _USER_DRAFT_FIELDS | frozenset({
        'company_id',
        'ticket_number',
        'status',
        'requester_id',
        'assignee_id',
        'solution',
        'solution_at',
        'closed_at',
        'reopen_count',
        'submitted_at',
        'first_response_at',
    })

    def _check_user_create_values(self, values_list):
        """Non-superuser create is limited to the requester's own draft."""
        if self.env.su:
            return

        allowed = self._USER_DRAFT_FIELDS | {'status', 'requester_id'}

        for values in values_list:
            if (
                values.get('status', 'draft') != 'draft'
                or values.get('requester_id', self.env.uid) != self.env.uid
                or set(values) - allowed
            ):
                raise AccessError(
                    'غير مصرح بإنشاء طلب بهذه البيانات مباشرة؛ '
                    'يتم إرسال الطلب عبر منصة الدعم فقط.'
                )

    def _check_user_write_values(self, values):
        """Block direct writes on server-controlled fields (BR-07..BR-15).

        Users (employees, support managers, other internal users) may only
        edit the content fields of their own draft. Workflow fields (status,
        assignee, requester, solution, SLA, dates, counters) are written by
        the platform actions under sudo() after role/ownership checks.
        """
        if self.env.su:
            return

        protected_keys = {
            key for key in values
            if key in self._PROTECTED_FIELDS or key.startswith('sla_')
        }

        for ticket in self:
            changed = {
                key for key in protected_keys
                if not (
                    key in ('status', 'requester_id')
                    and (
                        ticket[key].id
                        if key == 'requester_id'
                        else ticket[key]
                    ) == values[key]
                )
            }

            if not changed:
                continue

            if (
                ticket.status == 'draft'
                and ticket.requester_id.id == self.env.uid
                and changed <= self._USER_DRAFT_FIELDS
            ):
                continue

            raise AccessError(
                'غير مصرح بتعديل هذه البيانات مباشرة: '
                f'{", ".join(sorted(changed))}.'
            )

    @api.model_create_multi
    def create(self, values_list):
        normalized_values_list = [
            self._normalize_text_values(values)
            for values in values_list
        ]

        if any(
            values.get('status', 'draft') not in {'draft', 'new'}
            for values in normalized_values_list
        ):
            raise ValidationError(
                'يجب إنشاء الطلب بحالة مسودة أو جديد.'
            )

        self._check_user_create_values(normalized_values_list)

        return super().create(normalized_values_list)

    def write(self, values):
        values = self._normalize_text_values(values)
        self._check_user_write_values(values)
        new_status = values.get('status')

        if new_status:
            for ticket in self:
                if (
                    new_status != ticket.status
                    and new_status not in self._ALLOWED_STATUS_TRANSITIONS.get(
                        ticket.status,
                        set(),
                    )
                ):
                    raise ValidationError(
                        'انتقال حالة الطلب غير مسموح: '
                        f'{ticket.status} → {new_status}.'
                    )

        return super().write(values)

    @staticmethod
    def _as_utc(value):
        datetime_value = fields.Datetime.to_datetime(value)

        if not datetime_value.tzinfo:
            return UTC.localize(datetime_value)

        return datetime_value.astimezone(UTC)

    @staticmethod
    def _as_odoo_datetime(value):
        if value and value.tzinfo:
            value = value.astimezone(UTC).replace(tzinfo=None)

        return value

    def _get_sla_calendar(self):
        self.ensure_one()
        return (
            self.sla_calendar_id
            or self.sla_policy_id.calendar_id
            or self.company_id.resource_calendar_id
            or self.env.company.resource_calendar_id
        )

    def _apply_sla_policy(self):
        for ticket in self:
            if (
                ticket.status == 'draft'
                or not ticket.category_id
                or not ticket.priority
            ):
                continue

            policy_model = self.env['support.sla.policy'].sudo()
            policy_domain = [
                ('category_id', '=', ticket.category_id.id),
                ('priority', '=', ticket.priority),
                ('active', '=', True),
            ]
            policy_order = 'id'

            if 'company_id' in policy_model._fields:
                policy_domain.append(
                    (
                        'company_id',
                        'in',
                        [False, ticket.company_id.id],
                    )
                )
                policy_order = 'company_id asc, id'

            policy = policy_model.search(
                policy_domain,
                order=policy_order,
                limit=1,
            )

            if not policy:
                ticket.write({
                    'sla_policy_id': False,
                    'sla_calendar_id': False,
                    'sla_response_hours': 0.0,
                    'sla_resolution_hours': 0.0,
                    'sla_response_deadline': False,
                    'sla_resolution_deadline': False,
                    'sla_response_status': 'in_progress',
                    'sla_resolution_status': 'in_progress',
                    'sla_response_alert_level': 0,
                    'sla_resolution_alert_level': 0,
                })
                continue

            calendar = (
                policy.calendar_id
                or ticket.company_id.resource_calendar_id
                or self.env.company.resource_calendar_id
            )

            if not calendar:
                raise ValidationError(
                    'لا يوجد تقويم عمل صالح لتطبيق سياسة SLA.'
                )

            start_time = self._as_utc(
                ticket.submitted_at
                or ticket.create_date
                or fields.Datetime.now()
            )

            response_deadline = calendar.plan_hours(
                policy.response_hours,
                start_time,
                compute_leaves=True,
            )

            resolution_deadline = calendar.plan_hours(
                policy.resolution_hours,
                start_time,
                compute_leaves=True,
            )

            response_deadline = self._as_odoo_datetime(
                response_deadline
            )
            resolution_deadline = self._as_odoo_datetime(
                resolution_deadline
            )

            ticket.write({
                'sla_policy_id': policy.id,
                'sla_calendar_id': calendar.id,
                'sla_response_hours': policy.response_hours,
                'sla_resolution_hours': policy.resolution_hours,
                'sla_response_deadline': response_deadline,
                'sla_resolution_deadline': resolution_deadline,
                'sla_response_status': 'in_progress',
                'sla_resolution_status': 'in_progress',
                'sla_response_alert_level': 0,
                'sla_resolution_alert_level': 0,
            })

        return True
    def _check_assignee_manager(self):
        """Hold/resume are assignee-only support actions (FR-SUP-10/11).

        These methods are public, hence callable through JSON-RPC: the
        role and ownership checks must live here, not only in the controller.
        """
        self.ensure_one()

        if self.env.su:
            return

        if (
            not self.env.user.has_group('website.group_support_manager')
            or self.assignee_id != self.env.user
        ):
            raise AccessError(
                'هذا الإجراء متاح فقط لمسؤول الدعم المسند إليه الطلب.'
            )

    def pause_resolution_sla(self, reason):
        self.ensure_one()
        self._lock_for_update()
        self._check_assignee_manager()

        if self.status != 'processing':
            raise ValidationError(
                'يمكن تعليق الطلب فقط أثناء المعالجة.'
            )

        allowed_reasons = {
            'waiting_employee',
            'waiting_approval',
            'waiting_internal',
            'scheduled',
        }

        if reason not in allowed_reasons:
            raise ValidationError(
                'سبب تعليق الطلب غير صحيح.'
            )

        self.sudo().write({
            'status': 'on_hold',
            'sla_pause_started_at': fields.Datetime.now(),
            'sla_pause_reason': reason,
            'sla_pause_count': self.sla_pause_count + 1,
        })

        return True


    def resume_resolution_sla(self):
        self.ensure_one()
        self._lock_for_update()
        self._check_assignee_manager()

        if self.status != 'on_hold':
            raise ValidationError(
                'الطلب غير معلق حاليًا.'
            )

        if not self.sla_pause_started_at:
            raise ValidationError(
                'وقت بداية التعليق غير مسجل.'
            )

        resume_time = fields.Datetime.now()

        pause_start = self._as_utc(
            self.sla_pause_started_at
        )

        pause_end = self._as_utc(
            resume_time
        )

        calendar = self._get_sla_calendar()

        if not calendar:
            raise ValidationError(
                'لا يوجد تقويم عمل صالح لاستئناف SLA.'
            )

        paused_hours = max(
            calendar.get_work_hours_count(
                pause_start,
                pause_end,
                compute_leaves=True,
            ),
            0.0,
        )

        values = {
            'status': 'processing',
            'sla_pause_started_at': False,
            'sla_pause_reason': False,
            'sla_paused_hours':
                self.sla_paused_hours + paused_hours,
        }

        if (
            self.sla_resolution_deadline
            and self.sla_resolution_status == 'in_progress'
            and paused_hours > 0
        ):
            old_deadline = self._as_utc(
                self.sla_resolution_deadline
            )

            new_deadline = calendar.plan_hours(
                paused_hours,
                old_deadline,
                compute_leaves=True,
            )

            values[
                'sla_resolution_deadline'
            ] = self._as_odoo_datetime(new_deadline)

        self.sudo().write(values)

        return True
    def get_sla_metrics(
        self,
        sla_type='resolution'
    ):
        self.ensure_one()

        if sla_type not in {'response', 'resolution'}:
            raise ValidationError('نوع SLA المطلوب غير صحيح.')

        start_at = self.submitted_at
        current_time = fields.Datetime.now()

        if sla_type == 'response':
            allowed_hours = (
                self.sla_response_hours
                or self.sla_policy_id.response_hours
            )
            deadline = self.sla_response_deadline
            status = self.sla_response_status
            end_at = self.first_response_at or current_time
        else:
            allowed_hours = (
                self.sla_resolution_hours
                or self.sla_policy_id.resolution_hours
            )
            deadline = self.sla_resolution_deadline
            status = self.sla_resolution_status
            # بعد إعادة الفتح يبقى solution_at للحل السابق؛ لا يوقف العدّاد
            # إلا إذا كان الطلب فعلًا بانتظار التأكيد أو مغلقًا (FR-SYS-12/15).
            resolution_end = (
                self.solution_at
                if self.status in {'waiting_confirmation', 'closed'}
                else False
            )
            end_at = (
                resolution_end
                or (
                    self.sla_pause_started_at
                    if self.status == 'on_hold'
                    else current_time
                )
            )

        if (
            status in {'successful', 'failed'}
            and not (
                self.first_response_at
                if sla_type == 'response'
                else resolution_end
            )
        ):
            end_at = deadline

        if (
            not start_at
            or not allowed_hours
            or not deadline
            or not end_at
        ):
            return {
                'percent': 0.0,
                'remaining_hours': 0.0,
                'remaining_seconds': 0,
                'status': status or '',
                'is_working_time': False,
            }

        calendar = self._get_sla_calendar()

        if not calendar:
            return {
                'percent': 0.0,
                'remaining_hours': 0.0,
                'remaining_seconds': 0,
                'status': status or '',
                'is_working_time': False,
            }

        start_at = self._as_utc(start_at)
        end_at = self._as_utc(end_at)
        deadline = self._as_utc(deadline)

        used_hours = calendar.get_work_hours_count(
            start_at,
            end_at,
            compute_leaves=True,
        )

        if sla_type == 'resolution':
            used_hours -= self.sla_paused_hours or 0.0

        used_hours = max(used_hours, 0.0)

        is_final = status in {'successful', 'failed'}
        remaining_hours = (
            0.0
            if is_final
            else max(
                calendar.get_work_hours_count(
                    end_at,
                    deadline,
                    compute_leaves=True,
                ),
                0.0,
            )
        )

        check_end = end_at + relativedelta(
            minutes=1
        )

        is_working_time = (
            not is_final
            and self.status != 'on_hold'
            and calendar.get_work_hours_count(
                end_at,
                check_end,
                compute_leaves=True,
            ) > 0
        )

        percent = (
            used_hours
            / allowed_hours
        ) * 100

        return {
            'percent': round(max(0.0, percent), 1),
            'remaining_hours': round(remaining_hours, 2),
            'remaining_seconds': max(
                0,
                int(remaining_hours * 3600),
            ),
            'status': status or '',
            'is_working_time': is_working_time,
        }
    
    def _get_sla_alert_level(self, percent):
        if percent >= 100:
            return 100

        if percent >= 90:
            return 90

        if percent >= 75:
            return 75

        return 0

    def _send_sla_alert(
        self,
        sla_type,
        level
    ):
        self.ensure_one()

        if self.assignee_id:
            partners = self.assignee_id.partner_id

        else:
            support_group = self.env.ref(
                'website.group_support_manager',
                raise_if_not_found=False
            )

            partners = (
                support_group.users.filtered(
                    lambda user: (
                        user.active
                        and self.company_id in user.company_ids
                    )
                ).mapped('partner_id')
                if support_group
                else self.env['res.partner']
            )

        if not partners:
            return False

        if sla_type == 'response':  
            if level == 75:
                subject = (
                    'تنبيه SLA الاستجابة'
                )
                body = (
                    f'اقترب موعد الاستجابة '
                    f'للطلب {self.ticket_number}.'
                )

            elif level == 90:
                subject = (
                    'تحذير SLA الاستجابة'
                )
                body = (
                    f'تبقى وقت محدود قبل '
                    f'تجاوز SLA الاستجابة '
                    f'للطلب {self.ticket_number}.'
                )

            else:
                subject = (
                    'تجاوز SLA الاستجابة'
                )
                body = (
                    f'تم تجاوز SLA الاستجابة '
                    f'للطلب {self.ticket_number}.'
                )

        else:

            if level == 75:
                subject = (
                    'تنبيه SLA الحل'
                )
                body = (
                    f'اقترب موعد الحل '
                    f'للطلب {self.ticket_number}.'
                )

            elif level == 90:
                subject = (
                    'تحذير SLA الحل'
                )
                body = (
                    f'تبقى وقت محدود قبل '
                    f'تجاوز SLA الحل '
                    f'للطلب {self.ticket_number}.'
                )

            else:
                subject = (
                    'تجاوز SLA الحل'
                )
                body = (
                    f'تم تجاوز SLA الحل '
                    f'للطلب {self.ticket_number}.'
                )
        message = self.message_post(
            subject=subject,
            body=body,
            partner_ids=partners.ids,
            message_type='notification',
        )

        notifications = self.env[
            'mail.notification'
        ].sudo().search(
            [
                (
                    'mail_message_id',
                    '=',
                    message.id
                ),
                (
                    'res_partner_id',
                    'in',
                    partners.ids
                ),
            ]
        )

        if notifications:
            notifications.write({
                'is_read': False,
            })

        return True
    @api.model
    def _cron_update_sla_statuses(self):
        # المهمة تكتب حقول SLA المحمية؛ تعمل دائمًا بصلاحية النظام.
        self = self.sudo()
        now = fields.Datetime.now()

        tickets = self.search([
            ('status', '!=', 'draft'),
            ('sla_policy_id', '!=', False),
            '|',
            '&',
            ('sla_response_status', '=', 'in_progress'),
            ('first_response_at', '=', False),
            '&',
            ('sla_resolution_status', '=', 'in_progress'),
            ('status', 'in', ['new', 'processing']),
        ])

        for ticket in tickets:
            ticket._lock_for_update()

            # -------------------------
            # SLA الاستجابة
            # -------------------------
            if (
                ticket.sla_response_status
                == 'in_progress'
                and not ticket.first_response_at
            ):

                response_metrics = (
                    ticket.get_sla_metrics(
                        'response'
                    )
                )

                response_level = (
                    ticket._get_sla_alert_level(
                        response_metrics[
                            'percent'
                        ]
                    )
                )

                if (
                    response_level
                    > ticket.sla_response_alert_level
                ):
                    sent = ticket._send_sla_alert(
                        'response',
                        response_level
                    )
                    if sent:
                        ticket.write({
                            'sla_response_alert_level': response_level,
                        })

                if (
                    ticket.sla_response_deadline
                    and now
                    > ticket.sla_response_deadline
                ):

                    sent = False

                    if ticket.sla_response_alert_level < 100:
                        sent = ticket._send_sla_alert(
                            'response',
                            100
                        )

                    values = {
                        'sla_response_status':
                            'failed',
                    }

                    if sent:
                        values[
                            'sla_response_alert_level'
                        ] = 100

                    ticket.write(values)
            # SLA الحل

            if (
                ticket.sla_resolution_status
                == 'in_progress'
                and ticket.status
                in ['new', 'processing']
            ):

                resolution_metrics = (
                    ticket.get_sla_metrics(
                        'resolution'
                    )
                )

                resolution_level = (
                    ticket._get_sla_alert_level(
                        resolution_metrics[
                            'percent'
                        ]
                    )
                )

                if (
                    resolution_level
                    > ticket.sla_resolution_alert_level
                ):
                    sent = ticket._send_sla_alert(
                        'resolution',
                        resolution_level
                    )

                    if sent:
                        ticket.write({
                            'sla_resolution_alert_level':
                                resolution_level,
                        })
                if (
                    ticket.sla_resolution_deadline
                    and now
                    > ticket.sla_resolution_deadline
                ):

                    sent = False

                    if ticket.sla_resolution_alert_level < 100:
                        sent = ticket._send_sla_alert(
                            'resolution',
                            100
                        )

                    values = {
                        'sla_resolution_status':
                            'failed',
                    }

                    if sent:
                        values[
                            'sla_resolution_alert_level'
                        ] = 100

                    ticket.write(values)

        return True

    @api.constrains(
        'status',
        'ticket_number',
        'title',
        'description',
        'category_id',
        'priority',
        'submitted_at',
        'assignee_id',
        'first_response_at',
        'solution',
        'solution_at',
        'closed_at',
    )
    def _check_submitted_ticket_fields(self):

        for ticket in self:

            if ticket.status == 'draft':
                continue

            if not (ticket.ticket_number or '').strip():
                raise ValidationError(
                    'رقم الطلب مطلوب بعد الإرسال.'
                )

            if not (ticket.title or '').strip():
                raise ValidationError(
                    'موضوع الطلب مطلوب.'
                )

            if not (ticket.description or '').strip():
                raise ValidationError(
                    'وصف المشكلة مطلوب.'
                )

            if not ticket.category_id:
                raise ValidationError(
                    'تصنيف الطلب مطلوب.'
                )

            if not ticket.priority:
                raise ValidationError(
                    'الأولوية مطلوبة.'
                )

            if not ticket.submitted_at:
                raise ValidationError(
                    'تاريخ إرسال الطلب مطلوب.'
                )

            if (
                ticket.status
                in {
                    'processing',
                    'on_hold',
                    'waiting_confirmation',
                    'closed',
                }
                and not ticket.assignee_id
            ):
                raise ValidationError(
                    'يجب إسناد الطلب قبل تغيير حالته.'
                )

            if (
                ticket.status
                in {
                    'processing',
                    'on_hold',
                    'waiting_confirmation',
                    'closed',
                }
                and not ticket.first_response_at
            ):
                raise ValidationError(
                    'تاريخ الاستجابة الأولية مطلوب بعد استلام الطلب.'
                )

            if ticket.status in {'waiting_confirmation', 'closed'}:
                if not (ticket.solution or '').strip():
                    raise ValidationError(
                        'نص الحل مطلوب في الحالة الحالية.'
                    )

                if not ticket.solution_at:
                    raise ValidationError(
                        'تاريخ تقديم الحل مطلوب في الحالة الحالية.'
                    )

            if ticket.status == 'closed' and not ticket.closed_at:
                raise ValidationError(
                    'تاريخ الإغلاق مطلوب للطلب المغلق.'
                )

    @api.constrains('title', 'description', 'solution')
    def _check_text_lengths(self):
        for ticket in self:
            if len(ticket.title or '') > 200:
                raise ValidationError(
                    'موضوع الطلب يجب ألا يتجاوز 200 حرف.'
                )

            if len(ticket.description or '') > 10000:
                raise ValidationError(
                    'وصف المشكلة يجب ألا يتجاوز 10000 حرف.'
                )

            if len(ticket.solution or '') > 10000:
                raise ValidationError(
                    'نص الحل يجب ألا يتجاوز 10000 حرف.'
                )

    @api.constrains(
        'reopen_count',
        'sla_paused_hours',
        'sla_pause_count',
        'sla_response_alert_level',
        'sla_resolution_alert_level',
    )
    def _check_sla_values(self):
        valid_alert_levels = {0, 75, 90, 100}

        for ticket in self:
            if (
                ticket.reopen_count < 0
                or ticket.sla_paused_hours < 0
                or ticket.sla_pause_count < 0
            ):
                raise ValidationError(
                    'قيم عدادات SLA وإعادة الفتح لا يمكن أن تكون سالبة.'
                )

            if (
                ticket.sla_response_alert_level not in valid_alert_levels
                or ticket.sla_resolution_alert_level
                not in valid_alert_levels
            ):
                raise ValidationError(
                    'مستوى تنبيه SLA غير صحيح.'
                )


    @api.constrains(
        'category_id',
        'priority'
    )
    def _check_inquiry_priority(self):

        inquiry = self.env.ref(
            'website.support_category_consultation',
            raise_if_not_found=False,
        )

        for ticket in self:

            is_inquiry = (
                ticket.category_id == inquiry
                if inquiry
                else ticket.category_id.name == 'استفسار'
            )

            if (
                ticket.category_id
                and is_inquiry
                and ticket.priority == 'high'
            ):

                raise ValidationError(
                    'لا يمكن اختيار أولوية عالية لطلب من نوع استفسار.'
                )


    _sql_constraints = [
        (
            'support_ticket_number_unique',
            'unique(ticket_number)',
            'رقم الطلب يجب أن يكون فريدًا.',
        ),
        (
            'support_ticket_reopen_count_nonnegative',
            'CHECK(reopen_count >= 0)',
            'عدد مرات إعادة الفتح لا يمكن أن يكون سالبًا.',
        ),
        (
            'support_ticket_pause_values_nonnegative',
            'CHECK(sla_paused_hours >= 0 AND sla_pause_count >= 0)',
            'قيم إيقاف SLA لا يمكن أن تكون سالبة.',
        ),
    ]    
