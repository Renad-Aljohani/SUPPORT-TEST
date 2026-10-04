import base64
import functools
import logging
from collections import defaultdict
from pathlib import Path

from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError, OperationalError

from odoo import http, fields
from odoo.http import content_disposition, request
from odoo.tools import html2plaintext, html_escape
from odoo.tools.mimetypes import guess_mimetype
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from werkzeug.exceptions import HTTPException


GROUP_SUPPORT_EMPLOYEE = 'website.group_support_employee'
GROUP_SUPPORT_MANAGER = 'website.group_support_manager'

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024

ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf': {'.pdf'},
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
        '.docx',
    },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
        '.xlsx',
    },
    'image/png': {'.png'},
    'image/jpeg': {'.jpg', '.jpeg'},
    'video/mp4': {'.mp4'},
    'video/quicktime': {'.mov'},
}


_logger = logging.getLogger(__name__)


def _json_errors(endpoint):
    """Keep the JSON contract {success, message} for every failure (API doc §5).

    Business-rule errors raised by the ORM (ValidationError/UserError/
    AccessError) used to escape as an HTML error page. The transaction is
    rolled back first so no partial record survives a failed request.
    """
    @functools.wraps(endpoint)
    def wrapper(self, *args, **kwargs):
        try:
            return endpoint(self, *args, **kwargs)
        except (HTTPException, OperationalError):
            # OperationalError covers PostgreSQL serialization/lock failures:
            # Odoo retries the whole request natively (service.model.retrying),
            # e.g. two managers claiming the same ticket -> one 200, one 409.
            raise
        except (AccessError, MissingError) as error:
            request.env.cr.rollback()
            return request.make_json_response(
                {'success': False, 'message': str(error.args[0] if error.args else error)},
                status=403 if isinstance(error, AccessError) else 404,
            )
        except UserError as error:
            request.env.cr.rollback()
            return request.make_json_response(
                {'success': False, 'message': str(error.args[0] if error.args else error)},
                status=400,
            )
        except Exception:
            request.env.cr.rollback()
            _logger.exception('Support platform request failed: %s', request.httprequest.path)
            return request.make_json_response(
                {'success': False, 'message': 'حدث خطأ غير متوقع، يرجى المحاولة لاحقًا.'},
                status=500,
            )

    return wrapper


class SupportController(http.Controller):

    @staticmethod
    def _positive_int(value):
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            return None

        return parsed_value if parsed_value > 0 else None

    @staticmethod
    def _attachment_filename(attachment_file):
        filename = (
            attachment_file.filename
            or 'attachment'
        ).strip()
        return filename.replace('\\', '/').rsplit('/', 1)[-1]

    @staticmethod
    def _lock_ticket(ticket):
        ticket._lock_for_update()

    def _add_ticket_history(
        self,
        ticket,
        action,
        old_status=None,
        new_status=None,
        note=None
    ):
        request.env['support.ticket.history'].sudo().create({
            'ticket_id': ticket.id,
            'user_id': request.env.user.id,
            'action': action,
            'old_status': old_status,
            'new_status': new_status,
            'note': (note or '').strip(),
        })

    def _validate_attachment(self, attachment_file):
        if (
            not attachment_file
            or not attachment_file.filename
        ):
            return True, b''
        
        filename = (
            attachment_file.filename
            or ''
        ).strip()

        if (
            not filename
            or len(filename) > 255
            or any(
                character in filename
                for character in ('\r', '\n', '\x00')
            )
        ):
            return False, 'اسم الملف غير صحيح.'

        claimed_mimetype = (
            attachment_file.mimetype
            or ''
        ).split(';', 1)[0].strip().lower()

        allowed_extensions = ALLOWED_ATTACHMENT_TYPES.get(
            claimed_mimetype
        )

        if not allowed_extensions:
            return False, 'نوع الملف غير مسموح.'

        safe_filename = self._attachment_filename(
            attachment_file
        )
        extension = Path(safe_filename).suffix.lower()

        if extension not in allowed_extensions:
            return False, 'امتداد الملف لا يتوافق مع نوعه.'

        file_content = attachment_file.read(
            MAX_ATTACHMENT_SIZE + 1
        )

        if len(file_content) > MAX_ATTACHMENT_SIZE:
            return (
                False,
                'حجم الملف يجب ألا يتجاوز 10 ميجابايت.'
            )

        if not file_content:
            return False, 'الملف فارغ.'

        detected_mimetype = guess_mimetype(
            file_content,
            default='application/octet-stream',
        )

        # MP4 وMOV يستخدمان حاوية ISO Base Media نفسها.
        if (
            len(file_content) >= 12
            and file_content[4:8] == b'ftyp'
        ):
            detected_mimetype = (
                'video/quicktime'
                if file_content[8:12] == b'qt  '
                else 'video/mp4'
            )

        if detected_mimetype != claimed_mimetype:
            return False, 'محتوى الملف لا يتوافق مع نوعه.'

        return True, file_content

    def _is_support_employee(self):
        return request.env.user.has_group(
            GROUP_SUPPORT_EMPLOYEE
        )

    def _is_support_manager(self):
        return request.env.user.has_group(
            GROUP_SUPPORT_MANAGER
        )

    def _is_support_user(self):
        return (
            self._is_support_employee()
            or self._is_support_manager()
        )

    def _get_current_employee(self):
        return request.env['hr.employee'].sudo().search(
            [
                ('user_id', '=', request.env.user.id),
                (
                    'company_id',
                    'in',
                    [False, request.env.company.id],
                ),
            ],
            limit=1,
        )

    def _ticket_related_data(self, tickets):
        rating_by_ticket = {}
        history_by_ticket = defaultdict(list)
        attachment_by_ticket = {}

        if not tickets:
            return (
                rating_by_ticket,
                history_by_ticket,
                attachment_by_ticket,
            )

        ratings = request.env['support.rating'].search(
            [('ticket_id', 'in', tickets.ids)]
        )
        for rating in ratings:
            rating_by_ticket.setdefault(
                rating.ticket_id.id,
                rating,
            )

        histories = request.env['support.ticket.history'].search(
            [('ticket_id', 'in', tickets.ids)],
            order='create_date asc, id asc',
        )
        for history in histories:
            history_by_ticket[history.ticket_id.id].append(history)

        attachments = request.env['ir.attachment'].sudo().search(
            [
                ('res_model', '=', 'support.ticket'),
                ('res_id', 'in', tickets.ids),
            ],
            order='id desc',
        )
        for attachment in attachments:
            attachment_by_ticket.setdefault(
                attachment.res_id,
                attachment,
            )

        return (
            rating_by_ticket,
            history_by_ticket,
            attachment_by_ticket,
        )

    @http.route(
        '/support/csrf',
        type='http',
        auth='user',
        methods=['GET'],
        website=False,
    )
    @_json_errors
    def support_csrf(self, **kwargs):
        if not self._is_support_user():
            return request.not_found()

        response = request.make_json_response({
            'csrf_token': request.csrf_token(),
        })
        response.headers['Cache-Control'] = 'no-store'
        return response

    @http.route(
        '/support',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    def support_home(self, **kwargs):
        user = request.env.user

        if user.has_group(
            'website.group_support_manager'
        ):
            return request.redirect(
                '/support/manager'
            )

        if user.has_group(
            'website.group_support_employee'
        ):
            return request.redirect(
                '/support/employee'
            )

        return request.not_found()


    @http.route(
        '/support/employee',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    def support_employee(self, **kwargs):
        user = request.env.user

        if not user.has_group(
            'website.group_support_employee'
        ):
            return request.not_found()

        employee = self._get_current_employee()
        department_name = (
            employee.department_id.name
            if employee and employee.department_id
            else ''
        )

        return request.render(
            'website.employee',
            {
                'current_user_name': user.name,
                'current_department': department_name,
                'csrf_token': request.csrf_token(),
            }
        )

    @http.route(
        '/support/manager',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    def support_manager(self, **kwargs):
        if not self._is_support_manager():
            return request.not_found()

        return request.render(
            'website.support',
            {
                'current_support_name': request.env.user.name,
                 'current_support_id': request.env.user.id,
                'csrf_token': request.csrf_token(),
            }
        )
    @http.route(
        '/support/ticket/hold',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def hold_support_ticket(self, **kwargs):
        if not request.env.user.has_group(
            'website.group_support_manager'
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك بتنفيذ هذا الإجراء.',
                },
                status=403
            )

        data = request.httprequest.get_json(
            silent=True
        ) or {}

        ticket_number = (
            data.get('ticket_number') or ''
        ).strip()

        reason = (
            data.get('reason') or ''
        ).strip()

        if not ticket_number:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'رقم الطلب غير موجود.',
                },
                status=400
            )

        if not reason:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'سبب تعليق الطلب مطلوب.',
                },
                status=400
            )

        if len(reason) > 1000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'سبب التعليق يتجاوز الحد المسموح.',
                },
                status=400,
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                )
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير موجود.',
                },
                status=404
            )

        self._lock_ticket(ticket)

        if ticket.assignee_id != request.env.user:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'لا يمكنك تعليق طلب غير مسند إليك.',
                },
                status=403
            )

        try:
            ticket.pause_resolution_sla(
                reason
            )


            reason_label = dict(
                ticket._fields['sla_pause_reason'].selection
            ).get(reason, reason)

            self._add_ticket_history(
                ticket=ticket,
                action='hold',
                old_status='processing',
                new_status='on_hold',
                note=f'تم تعليق الطلب مؤقتًا — السبب: {reason_label}',
            )
            
        except ValidationError as error:
            return request.make_json_response(
                {
                    'success': False,
                    'message': str(error),
                },
                status=400
            )

        return request.make_json_response({
            'success': True,
            'message': 'تم تعليق الطلب مؤقتًا.',
        })


    @http.route(
        '/support/ticket/resume',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def resume_support_ticket(self, **kwargs):
        if not request.env.user.has_group(
            'website.group_support_manager'
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك بتنفيذ هذا الإجراء.',
                },
                status=403
            )

        data = request.httprequest.get_json(
            silent=True
        ) or {}

        ticket_number = (
            data.get('ticket_number') or ''
        ).strip()

        if not ticket_number:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'رقم الطلب غير موجود.',
                },
                status=400
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                )
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير موجود.',
                },
                status=404
            )

        self._lock_ticket(ticket)

        if ticket.assignee_id != request.env.user:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'لا يمكنك استئناف طلب غير مسند إليك.',
                },
                status=403
            )
        try:
            ticket.resume_resolution_sla()

            self._add_ticket_history(
                ticket=ticket,
                action='resume',
                old_status='on_hold',
                new_status='processing',
                note='تم استئناف معالجة الطلب'
            )

        except ValidationError as error:
            return request.make_json_response(
                {
                    'success': False,
                    'message': str(error),
                },
                status=400
            )
            
        return request.make_json_response({
            'success': True,
            'message': 'تم استئناف معالجة الطلب.',
        })

    @http.route(
        '/support/notifications',
        type='http',
        auth='user',
        methods=['GET'],
        website=True,
    )
    @_json_errors
    def get_support_notifications(self, **kwargs):
        partner = request.env.user.partner_id

        notifications = request.env[
            'mail.notification'
        ].sudo().search(
            [
                ('res_partner_id', '=', partner.id),
                (
                    'mail_message_id.model',
                    '=',
                    'support.ticket'
                ),
            ],
            order='id desc',
            limit=50
        )

        result = []

        for notification in notifications:
            message = notification.mail_message_id
            subject = message.subject or ''

            sla_level = 0

            if subject.startswith('تنبيه SLA'):
                sla_level = 75

            elif subject.startswith('تحذير SLA'):
                sla_level = 90

            elif subject.startswith('تجاوز SLA'):
                sla_level = 100

            ticket = request.env[
                'support.ticket'
            ].sudo().browse(
                message.res_id
            )

            result.append({
                'id': notification.id,
                'message_id': message.id,
                'title': (
                    message.subject
                    or 'تحديث على طلب الدعم'
                ),
                'message': html2plaintext(
                    message.body or ''
                ).strip(),
                'ticket_id': ticket.id,
                'ticket_number': (
                    ticket.ticket_number
                    if ticket.exists()
                    else ''
                ),
                'is_read': notification.is_read,
                'sla_level': sla_level,
                'created_at': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                         message.date
                         ).isoformat()
                    if message.date
                    else ''
                ),
            })

        return request.make_json_response({
            'success': True,
            'notifications': result,
        })


    @http.route(
        '/support/notifications/read',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def mark_support_notifications_read(self, **kwargs):
        data = request.httprequest.get_json(
            silent=True
        ) or {}

        notification_id = data.get(
            'notification_id'
        )

        if notification_id is not None:
            notification_id = self._positive_int(
                notification_id
            )

            if not notification_id:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': 'رقم الإشعار غير صحيح.',
                    },
                    status=400,
                )

        partner = request.env.user.partner_id

        domain = [
            ('res_partner_id', '=', partner.id),
            (
                'mail_message_id.model',
                '=',
                'support.ticket'
            ),
        ]

        if notification_id:
            domain.append(
                ('id', '=', notification_id)
            )

        notifications = request.env[
            'mail.notification'
        ].sudo().search(domain)

        notifications.write({
            'is_read': True,
        })

        return request.make_json_response({
            'success': True,
        })
   

    @http.route(
        '/support/ticket/create',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )

    @_json_errors
    def create_support_ticket(self, **kwargs):
        if not self._is_support_employee():
             return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )

        json_data = request.httprequest.get_json(
            silent=True
        )

        if isinstance(json_data, dict):
            data = json_data
        else:
            data = request.httprequest.form.to_dict()

        title = (
            data.get('title') or ''
        ).strip()

        description = (
            data.get('description') or ''
        ).strip()

        category_name = (
            data.get('category') or ''
        ).strip()

        priority_value = (
            data.get('priority') or ''
        ).strip()

        if (
            not title
            or not description
            or not category_name
            or not priority_value
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'بيانات الطلب غير مكتملة.',
                },
                status=400
            )

        if len(title) > 200 or len(description) > 10000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'عنوان الطلب أو وصفه يتجاوز الحد المسموح.',
                },
                status=400,
            )
        category = request.env['support.category'].search(
            [
                ('name', '=', category_name),
                ('active', '=', True),
            ],
            limit=1
        )

        if not category:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'تصنيف الطلب غير موجود.',
                },
                status=400
            )                                                                
        # فحص المرفق قبل إنشاء الطلب
        attachment_file = request.httprequest.files.get(
            'attachment'
        )

        file_content = b''

        if (
            attachment_file
            and attachment_file.filename
        ):
            is_valid, result = self._validate_attachment(
                attachment_file
            )

            if not is_valid:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': result,
                    },
                    status=400
                )

            file_content = result

        allowed_priorities = {
            'low',
            'medium',
            'high',
        }

        if priority_value not in allowed_priorities:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'أولوية الطلب غير صحيحة.',
                },
                status=400,
            )

        priority = priority_value

        # الرقم المرجعي يُستهلك فقط بعد نجاح كل التحققات (لا فجوات بسبب طلبات مرفوضة).
        ticket_number = (
            request.env['ir.sequence']
            .sudo()
            .next_by_code('support.ticket')
        )

        if not ticket_number:
            return request.make_json_response(
                {

                    'success': False,
                    'message': 'تعذر إنشاء رقم الطلب.',
                },
                status=500
            )

        employee = self._get_current_employee()
        ticket_values = {
            'ticket_number': ticket_number,
            'title': title,
            'description': description,
            'category_id': category.id,
            'priority': priority,
            'status': 'new',
            'requester_id': request.env.user.id,
            'submitted_at': fields.Datetime.now(),
        }

        if employee and employee.department_id:
            ticket_values['department_id'] = employee.department_id.id

        ticket = request.env['support.ticket'].sudo().create(ticket_values)
        ticket.sudo()._apply_sla_policy()

        
        self._add_ticket_history(
            ticket=ticket,
            action='create',
            old_status=None,
            new_status='new',
            note='تم إنشاء الطلب'
        )
        # إشعار جميع مسؤولي الدعم بوجود طلب جديد
        support_group = request.env.ref(
            'website.group_support_manager'
        )

        support_partners = support_group.users.mapped(
            'partner_id'
        )

        if support_partners:
            message = ticket.sudo().message_post(
                subject='طلب دعم جديد',
                body=(
                    f'تم إنشاء طلب دعم جديد '
                    f'برقم {ticket.ticket_number}.'
                ),
                partner_ids=support_partners.ids,
                message_type='notification',
            )

            request.env[
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
                        support_partners.ids
                    ),
                ]
            ).write({
                'is_read': False,
            })    

        attachment = False

        if (
            attachment_file
            and attachment_file.filename
            and file_content
        ):
            attachment = (
                request.env['ir.attachment']
                .sudo()
                .create({
                    'name': self._attachment_filename(
                        attachment_file
                    ),
                    'type': 'binary',
                    'datas': base64.b64encode(
                        file_content
                    ),
                    'mimetype': (
                        attachment_file.mimetype
                        or 'application/octet-stream'
                    ),
                    'res_model': 'support.ticket',
                    'res_id': ticket.id,
                })
            )        

        return request.make_json_response({
            'success': True,
            'ticket_id': ticket.id,
            'ticket_number': ticket.ticket_number,
            'attachment_id': (
                attachment.id
                if attachment
                else False
            ),
        })  
    
    @http.route(
        '/support/attachment/<int:attachment_id>',
        type='http',
        auth='user',
        methods=['GET'],
        website=False
    )
    def open_support_attachment(self, attachment_id, **kwargs):
        attachment = request.env[
            'ir.attachment'
        ].sudo().browse(
            attachment_id
        )

        if not attachment.exists():
            return request.not_found()

        # لازم يكون المرفق تابع لتذكرة دعم
        if attachment.res_model != 'support.ticket':
            return request.not_found()

        ticket = request.env[
            'support.ticket'
        ].search(
            [('id', '=', attachment.res_id)],
            limit=1,
        )

        if not ticket:
            return request.not_found()

        user = request.env.user

        is_requester = (
            ticket.requester_id.id
            == user.id
        )

        is_support = user.has_group(
            'website.group_support_manager'
        )

        # فقط صاحب الطلب أو مسؤول الدعم
        if not (
            is_requester
            or is_support
        ):
            return request.not_found()

        # مسؤول الدعم ما يشوف مرفقات المسودات
        if (
            is_support
            and ticket.status == 'draft'
        ):
            return request.not_found()

        file_content = base64.b64decode(
            attachment.datas
        )

        return request.make_response(
            file_content,
            headers=[
                (
                    'Content-Type',
                    attachment.mimetype
                    or 'application/octet-stream'
                ),
                (
                    'Content-Disposition',
                    content_disposition(
                        attachment.name or 'attachment'
                    )
                ),
                ('Cache-Control', 'private, no-store'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Content-Security-Policy', "default-src 'none'"),
            ]
        )
    @http.route(
    '/support/draft/save',
    type='http',
    auth='user',
    methods=['POST'],
    website=True,
   )
    @_json_errors
    def save_support_draft(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )
        data = request.httprequest.form.to_dict()
       
        draft_id = data.get('draft_id')

        if draft_id:
            draft_id = self._positive_int(draft_id)

            if not draft_id:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': 'رقم المسودة غير صحيح.',
                    },
                    status=400,
                )

        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        category_name = (data.get('category') or '').strip()
        priority_value = (data.get('priority') or '').strip()

        if len(title) > 200 or len(description) > 10000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'عنوان المسودة أو وصفها يتجاوز الحد المسموح.',
                },
                status=400,
            )

        category = False


        if category_name:
            category = request.env['support.category'].search(
                [
                    ('name', '=', category_name),
                    ('active', '=', True),
                ],
                limit=1,
            )

            if not category:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': 'تصنيف الطلب غير موجود.',
                    },
                    status=400,
                )
        attachment_file = request.httprequest.files.get(
            'attachment' 
        )
        file_content = b''
        

        allowed_priorities = {
             'low',
             'medium',
              'high'
        }

        if priority_value and priority_value not in allowed_priorities:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'أولوية الطلب غير صحيحة.',
                },
                status=400,
            )

        if (
            attachment_file
            and attachment_file.filename
        ):
            is_valid, result = self._validate_attachment(
                attachment_file
            )

            if not is_valid:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': result,
                    },
                    status=400
                )

            file_content = result


        employee = self._get_current_employee()

        values = {
            'title': title or False,
            'description': description or False,
            'category_id': (
                category.id
                if category
                else False
            ),
             'priority': priority_value or False,
            'status': 'draft',
            'requester_id': request.env.user.id,
        }

        if employee and employee.department_id:
            values['department_id'] = employee.department_id.id

        # تعديل مسودة موجودة
        if draft_id:
            draft = request.env['support.ticket'].search(
                [
                    ('id', '=', draft_id),
                    (
                        'requester_id',
                        '=',
                        request.env.user.id
                    ),
                    ('status', '=', 'draft'),
                ],
                limit=1
            )

            if not draft:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': 'المسودة غير موجودة.',
                    },
                    status=404
                )

            draft.write(values)

        # إنشاء مسودة جديدة
        else:
            draft = request.env['support.ticket'].create(values)

        if (
            attachment_file
            and attachment_file.filename
            and file_content                    
        ):
            request.env['ir.attachment'].sudo().search(
                [
                    ('res_model', '=', 'support.ticket'),
                    ('res_id', '=', draft.id),
                ]
            ).unlink()

            request.env[
                'ir.attachment'
            ].sudo().create({ 
                'name': self._attachment_filename(
                    attachment_file
                ),
                'type': 'binary',
                'datas': base64.b64encode(
                    file_content
                ), 
                'mimetype': (
                    attachment_file.mimetype
                    or 'application/octet-stream'
                ),
                'res_model': 'support.ticket',
                'res_id': draft.id,
            })                      

        return request.make_json_response({
           'success': True,
           'draft_id': draft.id,
           'message': 'تم حفظ المسودة بنجاح',
        }) 
    @http.route(
        '/support/draft/submit',
        type='http',
        auth='user', 
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def submit_support_draft(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )

        data = request.httprequest.get_json(
            silent=True  
        ) or {} 

        draft_id = data.get(
            'draft_id'
        )
        if not draft_id:
            return request.make_json_response( 
                { 
                    'success': False,
                    'message': 'رقم المسودة غير موجود.',  
                },
                status=400
            )

        draft_id = self._positive_int(draft_id)

        if not draft_id:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'رقم المسودة غير صحيح.',
                },
                status=400,
            )
        draft = request.env[
            'support.ticket'            
        ].search(
            [
                ('id', '=', draft_id),
                (
                    'requester_id',                                    
                    '=',
                    request.env.user.id
                ),
                ('status', '=', 'draft'),
            ],
            limit=1            
        )
        if not draft:
            return request.make_json_response(
                {    
                    'success': False,
                    'message': 'المسودة غير موجودة.'
                },
                status=404
            )  

        self._lock_ticket(draft)

        if draft.status != 'draft':
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'تم إرسال هذه المسودة مسبقًا.',
                },
                status=409,
            )

        if (  
             not draft.title           
            or not draft.description
            or not draft.category_id            
            or not draft.priority
        ):
            return request.make_json_response(   
                {   
                    'success': False, 
                    'message': 'أكمل بيانات المسودة قبل إرسالها.',
                 },
                status=400
            )  
        ticket_number = (  
            request.env['ir.sequence'] 
            .sudo() 
            .next_by_code(  
                'support.ticket' 
            )
        )
        if not ticket_number:
            return request.make_json_response(  
                {                        
                    'success': False,
                    'message': 'تعذر إنشاء رقم الطلب.',
                },

                status=500
            )

        draft.sudo().write({
            'ticket_number': ticket_number,
            'status': 'new',
            'submitted_at': fields.Datetime.now(),
        })
        draft.sudo()._apply_sla_policy()

        # إشعار جميع مسؤولي الدعم بعد إرسال المسودة
        support_group = request.env.ref(
            'website.group_support_manager'
        )

        support_partners = support_group.users.mapped(
            'partner_id'
        )
        if support_partners:
            message = draft.sudo().message_post(
                subject='طلب دعم جديد',
                body=(
                    f'تم إنشاء طلب دعم جديد '
                    f'برقم {draft.ticket_number}.'
                ),
                partner_ids=support_partners.ids,
                message_type='notification',
            )

            request.env[
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
                        support_partners.ids
                    ),
                ]
            ).write({
                'is_read': False,
            })

        self._add_ticket_history(
            ticket=draft,
            action='create',
            old_status='draft',
            new_status='new',
            note='تم إنشاء الطلب'
        )

        return request.make_json_response({
            'success': True,
            'ticket_number': draft.ticket_number,
            'message': 'تم إرسال المسودة بنجاح',
        })      

    @http.route(
        '/support/draft/delete',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def delete_support_draft(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )
        data = request.httprequest.get_json(            
            silent=True
        ) or {}
        draft_id = data.get(
            'draft_id'
         )
        if not draft_id:  
            return request.make_json_response(                  
                {
                    'success': False,   
                    'message': 'رقم المسودة غير موجود.',
                },
                status=400
            )  

        draft_id = self._positive_int(draft_id)

        if not draft_id:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'رقم المسودة غير صحيح.',
                },
                status=400,
            )
        draft = request.env[
            'support.ticket'
        ].search(            
            [
                ('id', '=', draft_id),
                (                
                    'requester_id',
                     '=', 
                     request.env.user.id  
                ),  
                ('status', '=', 'draft'), 
            ],
            limit=1
        )
        if not draft:
            return request.make_json_response(
                {
                    'success': False, 
                    'message': 'المسودة غير موجودة.',                                       
                 }, 
                status=404
            )

        self._lock_ticket(draft)

        if draft.status != 'draft':
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'لا يمكن حذف مسودة تم إرسالها.',
                },
                status=409,
            )

        draft.sudo().unlink()

        return request.make_json_response(
            {
                'success': True, 
                'message': 'تم حذف المسودة بنجاح',
            }  
        )  
    @http.route(
        '/support/draft/<int:draft_id>',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    @_json_errors
    def get_support_draft(self, draft_id, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )
        draft = request.env[
            'support.ticket'
        ].search(
            [
                ('id', '=', draft_id),
                (  
                    'requester_id',                    
                    '=',
                    request.env.user.id  
                ),
                ('status', '=', 'draft'),
            ],  
            limit=1   
        )  
        if not draft:        
            return request.make_json_response(
                { 
                    'success': False,
                    'message': 'المسودة غير موجودة.', 
                },                                                                         
                status=404
            )
        priority_map = {
            'low': 'منخفضة', 
            'medium': 'متوسطة',
            'high': 'عالية', 
        }
        return request.make_json_response(
            { 
                'success': True,                                                                                                                           
                'draft': {
                    'draft_id': draft.id, 
                    'title': draft.title or '',
                    'description': draft.description or '', 
                    'type': (
                        draft.category_id.name
                        if draft.category_id
                        else ''                                                                      
                    ),
                    'priority': priority_map.get(
                        draft.priority,
                        ''                                               
                    ),
                } 
            } 
        )                                            

    @http.route(
        '/support/tickets',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    @_json_errors
    def get_employee_tickets(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )
        user = request.env.user
        
        tickets = request.env['support.ticket'].search(
            [('requester_id', '=', user.id)],
            order='create_date desc'
        )

        status_map = {
            'draft': 'مسودة',
            'new': 'جديد',
            'processing': 'قيد المعالجة',
            'on_hold': 'معلق مؤقتًا',
            'waiting_confirmation': 'بانتظار تأكيد الموظف',
            'closed': 'مغلق',
        }

        priority_map = {
            'low': 'منخفضة',
            'medium': 'متوسطة',
            'high': 'عالية',
        }

        data = []

        (
            ratings_by_ticket,
            histories_by_ticket,
            attachments_by_ticket,
        ) = self._ticket_related_data(tickets)

        for ticket in tickets:
            rating_record = ratings_by_ticket.get(ticket.id)
            history_records = histories_by_ticket.get(ticket.id, [])
            attachment_record = attachments_by_ticket.get(ticket.id)

            timeline = []

            for history in history_records:
                timeline.append({
                    'title': history.note or history.action,
                    'meta': (
                        fields.Datetime.context_timestamp(
                            request.env.user,
                            history.create_date
                        ).isoformat()
                        if history.create_date
                        else ''
                    )
                })
            data.append({
                'id': (
                   ticket.ticket_number
                   if ticket.ticket_number
                   else f'DRAFT-{ticket.id}' 
                ), 
                'draft_id': (
                    ticket.id
                    if ticket.status == 'draft'
                    else False
               ),

                'title': ticket.title,
                'type': (
                    ticket.category_id.name
                    if ticket.category_id
                    else ''
                     ),

                'priority': priority_map.get(
                    ticket.priority,
                    ticket.priority
                ),
                'status': status_map.get(
                    ticket.status,
                    ticket.status
                ),

                'sla_pause_reason': (
                    ticket.sla_pause_reason or ''
                ),
                'requester': ticket.requester_id.name,
                'department': (
                    ticket.department_id.name
                    if ticket.department_id
                    else ''
                ),
                'assignee': (
                    ticket.assignee_id.name
                    if ticket.assignee_id
                    else ''
                ),
                'assignee_id': (
                 ticket.assignee_id.id
                 if ticket.assignee_id
                 else False
                 ),
                'createdAt': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.create_date
                    ).isoformat()
                    if ticket.create_date
                    else ''
                ),
                'savedAt': (
                     fields.Datetime.context_timestamp(  
                            request.env.user,
                            ticket.write_date
                             ).isoformat()
                              if ticket.write_date
                              else ''
                              ),

                'description': ticket.description or '',
                'solution': ticket.solution or '',
                'solutionAt': (
                    fields.Datetime.context_timestamp(
                     request.env.user,
                     ticket.solution_at
                    ).isoformat()
                    if ticket.solution_at
                    else ''
                ),
                'attachment': (
                  {
                'id': attachment_record.id,
                'name': attachment_record.name,
                'mimetype': attachment_record.mimetype or '',
                }
                if attachment_record
                else None
                 ),
                'rating': (
                    {
                        'value': int(rating_record.rating),
                        'comment': rating_record.comment or '',
                        'rated_by': rating_record.rated_by.name,
                    }
                    if rating_record
                    else None
                ),
                'messages': [],
                'timeline': timeline,
            })
    

        return request.make_json_response({
            'success': True,
            'tickets': data,
        })   
    
             

    @http.route(
        '/support/ticket/claim',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def claim_support_ticket(self, **kwargs):
        if not request.env.user.has_group(
            'website.group_support_manager'
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'غير مصرح لك بتنفيذ هذا الإجراء.',
                },
                status=403
            )

        data = request.httprequest.get_json(
            silent=True
        ) or {}

        ticket_number = (
            data.get('ticket_number') or ''
        ).strip()

        if not ticket_number:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'رقم الطلب غير موجود.',
                },
                status=400
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                )
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير موجود.',
                },
                status=404
            )

        # يمنع مسؤولين من استلام التذكرة نفسها في اللحظة نفسها.
        self._lock_ticket(ticket)

        if ticket.status != 'new' or ticket.assignee_id:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب ليس جديدًا أو سبق إسناده.',
                },
                status=409
            )

        first_response_at = fields.Datetime.now()

        sla_response_status = 'in_progress'

        if ticket.sla_response_deadline:
            sla_response_status = (
                'successful'
                if first_response_at <= ticket.sla_response_deadline
                else 'failed'
            )

        ticket.sudo().write({
            'assignee_id': request.env.user.id,
            'status': 'processing',
            'first_response_at': first_response_at,
            'sla_response_status': sla_response_status,
        })

        # إذا تم استلام الطلب بعد تجاوز SLA الاستجابة
        if (
            sla_response_status == 'failed'
            and ticket.sla_response_alert_level < 100
        ):
            sent = ticket.sudo()._send_sla_alert(
                'response',
                100
            )

            if sent:
                ticket.sudo().write({
                    'sla_response_alert_level': 100,
                })


        # إذا كان SLA الحل متجاوزًا قبل استلام الطلب
        if (
            ticket.sla_resolution_status == 'failed'
            and ticket.sla_resolution_alert_level < 100
        ):
            sent = ticket.sudo()._send_sla_alert(
                'resolution',
                100
            )

            if sent:
                ticket.sudo().write({
                    'sla_resolution_alert_level': 100,
                })


        requester_partner = (
            ticket.requester_id.partner_id
        )       

        message = ticket.sudo().message_post(
            subject='تم استلام طلبك',
            body=(
                f'تم استلام الطلب '
                f'{ticket.ticket_number} '
                f'بواسطة '
                f'{request.env.user.name}.'
            ),
            partner_ids=[
                requester_partner.id
            ],
            message_type='notification',
        )
        notification = request.env[
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
                    '=',
                    requester_partner.id
                ),
            ],
            limit=1
        )

        if notification:
            notification.write({
                'is_read': False,
            })

        else:
            request.env[
                'mail.notification'
            ].sudo().create({
                'mail_message_id':
                    message.id,

                'res_partner_id':
                    requester_partner.id,

                'notification_type':
                    'inbox',

                'is_read':
                    False,
            })

        self._add_ticket_history(
            ticket=ticket,
            action='claim',
            old_status='new',
            new_status='processing',
            note='تم استلام الطلب'
        )

        return request.make_json_response({
            'success': True,
            'ticket_number':
                ticket.ticket_number,
            'assignee':
                request.env.user.name,
            'status':
                'processing',
        })
       
    @http.route(
        '/support/manager/tickets',
        type='http',
        auth='user',
        methods=['GET'],
        website=True
    )
    @_json_errors
    def get_manager_tickets(self, **kwargs):       
        if not request.env.user.has_group('website.group_support_manager'):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )

        tickets = request.env['support.ticket'].search(
            [
                  ('status', '!=', 'draft')
            ],
            order='create_date desc'
        )

        status_map = {
            'draft': 'مسودة',
            'new': 'جديد',
            'processing': 'قيد المعالجة',
            'on_hold': 'معلق مؤقتًا',
            'waiting_confirmation': 'بانتظار تأكيد الموظف',
            'closed': 'مغلق',
        }

        priority_map = {
            'low': 'منخفضة',
            'medium': 'متوسطة',
            'high': 'عالية',
        }
        

        data = []

        (
            ratings_by_ticket,
            histories_by_ticket,
            attachments_by_ticket,
        ) = self._ticket_related_data(tickets)

        # مقاييس SLA لكل الطلبات بجلب فترات العمل مرة واحدة لكل تقويم (بدل N+1).
        sla_metrics = tickets._get_sla_metrics_batch()

        for ticket in tickets:

            rating_record = ratings_by_ticket.get(ticket.id)
            history_records = histories_by_ticket.get(ticket.id, [])
            attachment_record = attachments_by_ticket.get(ticket.id)

            timeline = []

            for history in history_records:
                timeline.append({
                    'title': history.note or history.action,
                    'meta': (
                        fields.Datetime.context_timestamp(
                            request.env.user,
                            history.create_date
                        ).isoformat()
                        if history.create_date
                        else ''
                    )
                })

            response_sla = sla_metrics[ticket.id]['response']
            resolution_sla = sla_metrics[ticket.id]['resolution']

            data.append({
                'id': ticket.ticket_number,
                'title': ticket.title,
                'type': ticket.category_id.name,
                'priority': priority_map.get(
                    ticket.priority,
                    ticket.priority
                ),
                'status': status_map.get(
                    ticket.status,
                    ticket.status
                ),
                'requester': ticket.requester_id.name,
                'department': (
                    ticket.department_id.name
                    if ticket.department_id
                    else ''
                ),
                'assignee': (
                    ticket.assignee_id.name
                    if ticket.assignee_id
                    else ''
                    ),
                    'assignee_id': (
                    ticket.assignee_id.id
                    if ticket.assignee_id
                    else False
                ),
                'createdAt': (
                     fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.create_date
                        ).isoformat()
                    if ticket.create_date
                    else ''
                ),

                'description': ticket.description or '',
                'solution': ticket.solution or '',
                'solutionAt': (
                   fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.solution_at
                        ).isoformat()
                    if ticket.solution_at
                    else ''
                ),
                'sla_response_deadline': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.sla_response_deadline
                    ).isoformat()
                    if ticket.sla_response_deadline
                    else ''
                ),

                'sla_resolution_deadline': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.sla_resolution_deadline
                    ).isoformat()
                    if ticket.sla_resolution_deadline
                    else ''
                ),

                'sla_response_status': (
                    ticket.sla_response_status or ''
                ),

                'sla_resolution_status': (
                    ticket.sla_resolution_status or ''
                ),

                'sla_is_working_time': (
                    resolution_sla[
                    'is_working_time'
               ]
               ),

                'sla_response_percent': (
                    response_sla[
                    'percent'
                ]
                ),

               'sla_response_remaining_hours': (
                   response_sla[
                   'remaining_hours'
               ]
               ),

                'sla_resolution_percent': (
                  resolution_sla[
                  'percent'
              ]
              ),

                'sla_resolution_remaining_hours': (
                     resolution_sla[
                     'remaining_hours'
              ]
              ),
              'sla_resolution_remaining_seconds': (
                     resolution_sla[
                    'remaining_seconds'
               ]
               ),

                'first_response_at': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.first_response_at
                    ).isoformat()
                    if ticket.first_response_at
                    else ''
                ),  

                    'sla_pause_reason': (
                    ticket.sla_pause_reason or ''
                ),

                'sla_pause_started_at': (
                    fields.Datetime.context_timestamp(
                        request.env.user,
                        ticket.sla_pause_started_at
                    ).isoformat()
                    if ticket.sla_pause_started_at
                    else ''
                ),

                'sla_paused_hours': (
                    ticket.sla_paused_hours or 0.0
                ),

                'sla_pause_count': (
                    ticket.sla_pause_count or 0
                ),              
                
                'attachment': (
                {
               'id': attachment_record.id,
                'name': attachment_record.name,
                'mimetype': attachment_record.mimetype or '',
                }
                 if attachment_record
                 else None
                ),

                'rating': (
                    {
                        'value': int(rating_record.rating),
                        'comment': rating_record.comment or '',
                         'rated_by': rating_record.rated_by.name,

                    }
                    if rating_record
                    else None
                ),
                'messages': [],
                'timeline': timeline,
                        
                    })
             

        return request.make_json_response({
            'success': True,
            'tickets': data,
        })
    @http.route(
        '/support/analytics',
        type='http',
        auth='user',
        methods=['GET'],
        website=True,
    )
    @_json_errors
    def get_support_analytics(self, **kwargs):

        if not self._is_support_manager():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )

        today = fields.Date.context_today(
            request.env.user
        )

        period_start_date = (
            today.replace(day=1)
            - relativedelta(months=5)
        )
        period_start = fields.Datetime.to_datetime(
            period_start_date
        )

        tickets = request.env[
            'support.ticket'
        ].search(
            [
                ('status', '!=', 'draft'),
                ('submitted_at', '>=', period_start),
            ],
            order='submitted_at asc'
        )

        # -------------------------------------------------
        # تجهيز آخر 6 أشهر
        # -------------------------------------------------

        months = []

        for offset in range(5, -1, -1):

            year = today.year
            month = today.month - offset

            while month <= 0:
                month += 12
                year -= 1

            key = (
                f'{year}-'
                f'{str(month).zfill(2)}'
            )

            months.append({
                'key': key,
                'compliant': 0,
                'breached': 0,
                'response_hours': [],
                'resolution_hours': [],
            })

        months_map = {
            item['key']: item
            for item in months
        }

        # -------------------------------------------------
        # KPIs العامة
        # -------------------------------------------------

        total_sla = 0
        compliant_sla = 0
        breached_tickets = 0

        response_hours = []
        resolution_hours = []

        compliant_tickets = 0
        failed_tickets = 0

        response_sla_total = 0
        response_sla_compliant = 0
        resolution_sla_total = 0
        resolution_sla_compliant = 0

        open_tickets = 0
        resolved_tickets = 0
        reopened_tickets = 0

        # -------------------------------------------------
        # تحليل الطلبات
        # -------------------------------------------------

        work_hours_by_calendar = tickets._get_sla_work_hours_map()

        for ticket in tickets:

            calendar = (
                ticket.sla_calendar_id
                or ticket.sla_policy_id.calendar_id
                or ticket.company_id.resource_calendar_id
                or request.env.company.resource_calendar_id
            )
            work_hours = work_hours_by_calendar.get(calendar)

            # الشهر الذي ينتمي إليه الطلب
            submitted_local = (
                fields.Datetime.context_timestamp(
                    request.env.user,
                    ticket.submitted_at
                )
                if ticket.submitted_at
                else None
            )

            month_key = (
                submitted_local.strftime('%Y-%m')
                if submitted_local
                else None
            )

            month_bucket = (
                months_map.get(month_key)
                if month_key
                else None
            )

            # ---------------------------------------------
            # حالة SLA للطلب
            # ---------------------------------------------

            ticket_breached = (
                ticket.sla_response_status == 'failed'
                or ticket.sla_resolution_status == 'failed'
            )

            response_finished = (
                ticket.sla_response_status
                in ['successful', 'failed']
            )
            resolution_finished = (
                ticket.sla_resolution_status
                in ['successful', 'failed']
            )
            ticket_evaluated = (
                ticket_breached
                or (
                    response_finished
                    and resolution_finished
                )
            )

            if response_finished:
                response_sla_total += 1
                if ticket.sla_response_status == 'successful':
                    response_sla_compliant += 1

            if resolution_finished:
                resolution_sla_total += 1
                if ticket.sla_resolution_status == 'successful':
                    resolution_sla_compliant += 1

            if ticket.status != 'closed':
                open_tickets += 1

            if ticket.solution_at:
                resolved_tickets += 1

            if ticket.reopen_count:
                reopened_tickets += 1

            if ticket_evaluated:
                total_sla += 1

                if ticket_breached:
                    breached_tickets += 1
                    failed_tickets += 1

                    if month_bucket:
                        month_bucket['breached'] += 1
                else:
                    compliant_sla += 1
                    compliant_tickets += 1

                    if month_bucket:
                        month_bucket['compliant'] += 1

            # ---------------------------------------------
            # زمن الاستجابة
            # ---------------------------------------------

            if (
                calendar
                and ticket.submitted_at
                and ticket.first_response_at
            ):

                start = (
                    fields.Datetime.to_datetime(
                        ticket.submitted_at
                    )
                )

                end = (
                    fields.Datetime.to_datetime(
                        ticket.first_response_at
                    )
                )

                response_time = (
                    work_hours(start, end)
                    if work_hours
                    else calendar.get_work_hours_count(
                        start, end, compute_leaves=True,
                    )
                )

                response_time = max(
                    response_time,
                    0.0
                )

                response_hours.append(
                    response_time
                )

                if month_bucket:
                    month_bucket[
                        'response_hours'
                    ].append(
                        response_time
                    )

            # ---------------------------------------------
            # زمن الحل
            # ---------------------------------------------

            if (
                calendar
                and ticket.submitted_at
                and ticket.solution_at
            ):

                start = (
                    fields.Datetime.to_datetime(
                        ticket.submitted_at
                    )
                )

                end = (
                    fields.Datetime.to_datetime(
                        ticket.solution_at
                    )
                )

                resolution_time = (
                    work_hours(start, end)
                    if work_hours
                    else calendar.get_work_hours_count(
                        start, end, compute_leaves=True,
                    )
                )

                resolution_time = max(
                    resolution_time
                    - (
                        ticket.sla_paused_hours
                        or 0.0
                    ),
                    0.0
                )

                resolution_hours.append(
                    resolution_time
                )

                if month_bucket:
                    month_bucket[
                        'resolution_hours'
                    ].append(
                        resolution_time
                    )

        # -------------------------------------------------
        # مؤشرات عامة
        # -------------------------------------------------

        sla_compliance = (
            round(
                (
                    compliant_sla
                    / total_sla
                ) * 100,
                1
            )
            if total_sla
            else None
        )

        response_sla_compliance = (
            round(
                (
                    response_sla_compliant
                    / response_sla_total
                ) * 100,
                1,
            )
            if response_sla_total
            else None
        )

        resolution_sla_compliance = (
            round(
                (
                    resolution_sla_compliant
                    / resolution_sla_total
                ) * 100,
                1,
            )
            if resolution_sla_total
            else None
        )

        reopen_rate = (
            round(
                (reopened_tickets / resolved_tickets) * 100,
                1,
            )
            if resolved_tickets
            else None
        )

        ratings = request.env['support.rating'].search(
            [('ticket_id', 'in', tickets.ids)]
        )
        rating_values = [
            int(rating.rating)
            for rating in ratings
            if rating.rating
        ]
        average_rating = (
            round(
                sum(rating_values) / len(rating_values),
                2,
            )
            if rating_values
            else None
        )

        average_response = (
            round(
                sum(response_hours)
                / len(response_hours),
                2
            )
            if response_hours
            else None
        )

        average_resolution = (
            round(
                sum(resolution_hours)
                / len(resolution_hours),
                2
            )
            if resolution_hours
            else None
        )

        # -------------------------------------------------
        # بيانات الرسومات
        # -------------------------------------------------

        trend_labels = []
        trend_values = []

        response_labels = []
        response_values = []

        resolution_labels = []
        resolution_values = []

        for month in months:

            label = month['key']

            completed = (
                month['compliant']
                + month['breached']
            )

            compliance_value = (
                round(
                    (
                        month['compliant']
                        / completed
                    ) * 100,
                    1
                )
                if completed
                else None  # شهر بلا طلبات مُقيّمة: لا بيانات، وليس 0%
            )

            response_value = (
                round(
                    sum(
                        month['response_hours']
                    )
                    / len(
                        month['response_hours']
                    ),
                    2
                )
                if month[
                    'response_hours'
                ]
                else None
            )

            resolution_value = (
                round(
                    sum(
                        month[
                            'resolution_hours'
                        ]
                    )
                    / len(
                        month[
                            'resolution_hours'
                        ]
                    ),
                    2
                )
                if month[
                    'resolution_hours'
                ]
                else None
            )

            trend_labels.append(
                label
            )

            trend_values.append(
                compliance_value
            )

            response_labels.append(
                label
            )

            response_values.append(
                response_value
            )

            resolution_labels.append(
                label
            )

            resolution_values.append(
                resolution_value
            )

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return request.make_json_response(
            {
                'success': True,

                'kpis': {
                    'sla_compliance':
                        sla_compliance,

                    'response_sla_compliance':
                        response_sla_compliance,

                    'resolution_sla_compliance':
                        resolution_sla_compliance,

                    'average_response_hours':
                        average_response,

                    'average_resolution_hours':
                        average_resolution,

                    'breached_tickets':
                        breached_tickets,

                    'total_tickets': len(tickets),
                    'evaluated_tickets': total_sla,
                    'open_tickets': open_tickets,
                    'reopen_rate': reopen_rate,
                    'average_rating': average_rating,
                    'rated_tickets': len(rating_values),
                    'period_months': 6,
                },

                'charts': {

                    'compliance': {
                        'compliant':
                            compliant_tickets,

                        'breached':
                            failed_tickets,
                    },

                    'trend': {
                        'labels':
                            trend_labels,

                        'values':
                            trend_values,
                    },

                    'response_time': {
                        'labels':
                            response_labels,

                        'values':
                            response_values,

                        'average_hours':
                            average_response,
                    },

                    'resolution_time': {
                        'labels':
                            resolution_labels,

                        'values':
                            resolution_values,

                        'average_hours':
                            average_resolution,
                    },
                },
            }
        )   

    @http.route(
       '/support/ticket/solution',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def submit_ticket_solution(self, **kwargs):
        if not request.env.user.has_group('website.group_support_manager'):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك بتنفيذ هذا الإجراء.',
                },
                status=403
            )

        data = request.httprequest.get_json(silent=True) or {}

        ticket_number = (data.get('ticket_number') or '').strip()
        solution = (data.get('solution') or '').strip()

        if not ticket_number or not solution:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'بيانات الحل غير مكتملة.',
                },
                status=400
            )

        if len(solution) > 10000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'نص الحل يتجاوز الحد المسموح.',
                },
                status=400,
            )

        ticket = request.env['support.ticket'].search(
            [('ticket_number', '=', ticket_number)],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير موجود.',
                },
                status=404
            )

        self._lock_ticket(ticket)

        if ticket.assignee_id != request.env.user:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير مسند لك.',
                },
                status=403
            )

        if ticket.status != 'processing':
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'لا يمكن إرسال الحل في الحالة الحالية.',
                },
                status=400
            )
        solution_at = fields.Datetime.now()

        sla_resolution_status = 'in_progress'

        if ticket.sla_resolution_deadline:
            sla_resolution_status = (
                'successful'
                if solution_at <= ticket.sla_resolution_deadline
                else 'failed'
            )

        ticket.sudo().write({
            'solution': solution,
            'solution_at': solution_at,
            'status': 'waiting_confirmation',
            'sla_resolution_status': sla_resolution_status,
        })

        self._add_ticket_history(
            ticket=ticket,
            action='solution',
            old_status='processing',
            new_status='waiting_confirmation',
            note='تم إرسال الحل'
        )

        message = ticket.sudo().message_post(
            subject='تم إرسال حل للطلب',
            body=(
                f'تم إرسال حل للطلب '
                f'{ticket.ticket_number}. '
                f'يرجى مراجعة الحل وتأكيده.'
            ),
            partner_ids=[
                ticket.requester_id.partner_id.id
            ],
            message_type='notification',
        )

        request.env[
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
                    '=',
                    ticket.requester_id.partner_id.id
                ),
            ]
        ).write({
            'is_read': False,
        })
        return request.make_json_response({
            'success': True,
            'ticket_number': ticket.ticket_number,
            'solution': ticket.solution,
            'status': 'waiting_confirmation',
        })

    @http.route(
        '/support/ticket/employee-action',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def employee_ticket_action(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )   
        data = request.httprequest.get_json(
            silent=True
        ) or {}

        ticket_number = (
            data.get('ticket_number') or ''
        ).strip()

        action = (
            data.get('action') or ''
        ).strip()

        if not ticket_number or action not in [
            'confirm',
            'reopen'
        ]:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'بيانات الإجراء غير صحيحة.',
                },
                status=400
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                ),
                (
                    'requester_id',
                    '=',
                    request.env.user.id
                ),
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'الطلب غير موجود أو لا يخص المستخدم الحالي.',
                },
                status=404
            )

        self._lock_ticket(ticket)

        if ticket.status != 'waiting_confirmation':
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'الطلب ليس بانتظار تأكيد الموظف.',
                },
                status=400
            )

        # تأكيد الحل وإغلاق الطلب
        if action == 'confirm':
            ticket.sudo().write({
            'status': 'closed',
            'closed_at': fields.Datetime.now(),
  
            })

            self._add_ticket_history(
                ticket=ticket,
                action='close',
                old_status='waiting_confirmation',
                new_status='closed',
                note='تم تأكيد الحل وإغلاق الطلب'
            )

            if ticket.assignee_id:
                partner = ticket.assignee_id.partner_id

                message = ticket.sudo().message_post(
                    subject='تم إغلاق الطلب',
                    body=(
                        f'تم تأكيد الحل وإغلاق الطلب '
                        f'{ticket.ticket_number}.'
                    ),
                    partner_ids=[
                        partner.id
                    ],
                    message_type='notification',
                )

                request.env[
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
                            '=',
                            partner.id
                        ),
                    ]
                ).write({
                    'is_read': False,
                })

            return request.make_json_response({
                'success': True,
                'status': 'closed',
                'message': 'تم تأكيد الحل وإغلاق الطلب.',
            })
        # المشكلة مستمرة وإعادة الطلب للمعالجة
        if action == 'reopen':
            ticket.sudo().write({
                'status': 'processing',
                'sla_resolution_status': 'in_progress',
                'reopen_count': ticket.reopen_count + 1,
            })

            self._add_ticket_history(
                ticket=ticket,
                action='reopen',
                old_status='waiting_confirmation',
                new_status='processing',
                note=(
                    'المشكلة مستمرة وتمت إعادة '
                    'الطلب للمعالجة'
                )
            )

            if ticket.assignee_id:
                partner = ticket.assignee_id.partner_id

                message = ticket.sudo().message_post(
                    subject='تمت إعادة فتح الطلب',
                    body=(
                        f'تمت إعادة فتح الطلب '
                        f'{ticket.ticket_number} '
                        f'لأن المشكلة ما زالت مستمرة.'
                    ),
                    partner_ids=[
                        partner.id
                    ],
                    message_type='notification',
                )

                request.env[
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
                            '=',
                            partner.id
                        ),
                    ]
                ).write({
                    'is_read': False,
                })
            return request.make_json_response({
                'success': True,
                'status': 'processing',
                'message':
                    'تمت إعادة الطلب للمعالجة.',
            })
    @http.route(
        '/support/ticket/rating',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def submit_ticket_rating(self, **kwargs):
        if not self._is_support_employee():
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك.',
                },
                status=403
            )
        data = request.httprequest.get_json(silent=True) or {}

        ticket_number = (data.get('ticket_number') or '').strip()
        rating_value = data.get('rating')
        comment = (data.get('comment') or '').strip()

        if len(comment) > 2000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'ملاحظة التقييم تتجاوز الحد المسموح.',
                },
                status=400,
            )

        if not ticket_number:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'رقم الطلب غير موجود.',
                },
                status=400
            )

        try:
            rating_value = int(rating_value)
        except (TypeError, ValueError):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'قيمة التقييم غير صحيحة.',
                },
                status=400
            )

        if rating_value < 1 or rating_value > 5:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'التقييم يجب أن يكون من 1 إلى 5.',
                },
                status=400
            )

        ticket = request.env['support.ticket'].search(
            [
                ('ticket_number', '=', ticket_number),
                ('requester_id', '=', request.env.user.id),
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير موجود أو لا يخص المستخدم الحالي.',
                },
                status=404
            )

        if ticket.status != 'closed':
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'لا يمكن تقييم الطلب قبل إغلاقه.',
                },
                status=400
            )

        existing_rating = request.env['support.rating'].search(
            [('ticket_id', '=', ticket.id)],
            limit=1
        )

        if existing_rating:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'تم تقييم هذا الطلب مسبقًا.',
                },
                status=400
            )

        try:
            with request.env.cr.savepoint():
                rating = request.env['support.rating'].create({
                    'ticket_id': ticket.id,
                    'rating': str(rating_value),
                    'comment': comment,
                    'rated_by': request.env.user.id,
                })
        except IntegrityError:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'تم تقييم هذا الطلب مسبقًا.',
                },
                status=409,
            )

        self._add_ticket_history(
            ticket=ticket,
            action='rating',
            old_status='closed',
            new_status='closed',
            note=f'تم تقييم الخدمة بـ {rating_value} من 5'
        )

        if ticket.assignee_id:
            partner = ticket.assignee_id.partner_id

            message = ticket.sudo().message_post(
                subject='تم تقييم الخدمة',
                body=(
                    f'تم تقييم الطلب '
                    f'{ticket.ticket_number} '
                    f'بـ {rating_value} من 5.'
                ),
                partner_ids=[
                    partner.id
                ],
                message_type='notification',
            )

            request.env[
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
                        '=',
                        partner.id
                    ),
                ]
            ).write({
                'is_read': False,
            })

        return request.make_json_response({
            'success': True,
            'rating': rating.rating,
            'comment': rating.comment or '',
            'message': 'تم إرسال التقييم بنجاح.',
        })

    @http.route(
        '/support/ticket/messages',
        type='http',
        auth='user',
        methods=['GET'],
        website=True,
    )
    @_json_errors
    def get_ticket_messages(self, **kwargs):

        ticket_number = (
            request.params.get(
                'ticket_number'
            ) or ''
        ).strip()

        if not ticket_number:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'رقم الطلب غير موجود.',
                },
                status=400
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                )
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'الطلب غير موجود.',
                },
                status=404
            )

        is_requester = (
            ticket.requester_id.id
            == request.env.user.id
        )

        is_support = (
            request.env.user.has_group(
                'website.group_support_manager'
            )
        )

        if not (
            is_requester
            or is_support
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'غير مصرح لك بعرض المحادثة.',
                },
                status=403
            )

        messages = request.env[
            'mail.message'
        ].sudo().search(
            [
                (
                    'model',
                    '=',
                    'support.ticket'
                ),
                (
                    'res_id',
                    '=',
                    ticket.id
                ),
                (
                    'message_type',
                    '=',
                    'comment'
                ),
            ],
            order='id asc'
        )

        result = []

        for message in messages:

            attachments = []

            for attachment in (
                message.attachment_ids
            ):
                attachments.append({
                    'id':
                        attachment.id,

                    'name':
                        attachment.name,

                    'mimetype':
                        attachment.mimetype or '',

                    'url':
                        (
                            '/support/attachment/'
                            f'{attachment.id}'
                        ),
                })

            result.append({
                'id':
                    message.id,

                'text':
                    html2plaintext(
                        message.body or ''
                    ).strip(),

                'author':
                    message.author_id.name or '',

                'author_id':
                    message.author_id.id,

                'mine':
                    (
                        message.author_id.id
                        ==
                        request.env.user.partner_id.id
                    ),

                'created_at':
                    (
                        fields.Datetime.context_timestamp(
                            request.env.user,
                            message.create_date
                        ).isoformat(
                        
                        )
                        if message.create_date
                        else ''
                    ),

                'attachments':
                    attachments,
            })

        return request.make_json_response({
            'success': True,
            'messages': result,
        })
    @http.route(
        '/support/ticket/message/send',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    @_json_errors
    def send_ticket_message(self, **post):

        ticket_number = (
            request.params.get(
                'ticket_number'
            ) or ''
        ).strip()

        body = (
            request.params.get(
                'message'
            ) or ''
        ).strip()

        if len(body) > 5000:
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'نص الرسالة يتجاوز الحد المسموح.',
                },
                status=400,
            )

        attachment_file = (
            request.httprequest.files.get(
                'attachment'
            )
        )

        if (
            not ticket_number
            or (
                not body
                and not attachment_file
            )
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'بيانات الرسالة غير مكتملة.',
                },
                status=400
            )

        ticket = request.env[
            'support.ticket'
        ].search(
            [
                (
                    'ticket_number',
                    '=',
                    ticket_number
                )
            ],
            limit=1
        )

        if not ticket:
            return request.make_json_response(
                {
                    'success': False,
                    'message':
                        'الطلب غير موجود.',
                },
                status=404
            )

        is_requester = (
            ticket.requester_id.id
            == request.env.user.id
        )

        is_support = (
            request.env.user.has_group(
                'website.group_support_manager'
            )
        )

        if not (
            is_requester
            or is_support
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'غير مصرح لك بإرسال رسالة.',
                },
                status=403
            )

        if ticket.status == 'closed':
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'لا يمكن إرسال رسالة على طلب مغلق.',
                },
                status=400,
            )

        if (
            is_support
            and ticket.assignee_id != request.env.user
        ):
            return request.make_json_response(
                {
                    'success': False,
                    'message': 'الطلب غير مسند لك.',
                },
                status=403
            )

        attachment_ids = []

        if (
            attachment_file
            and attachment_file.filename
        ):
            is_valid, result = self._validate_attachment(
                attachment_file
            )

            if not is_valid:
                return request.make_json_response(
                    {
                        'success': False,
                        'message': result,
                    },
                    status=400
                )

            file_content = result

            attachment = request.env[
                'ir.attachment'
            ].sudo().create({
                'name': self._attachment_filename(
                    attachment_file
                ),

                'datas':
                    base64.b64encode(
                        file_content
                    ),

                'res_model':
                    'support.ticket',

                'res_id':
                    ticket.id,

                'mimetype':
                    attachment_file.mimetype,
            })

            attachment_ids.append(
                attachment.id
            )

      # إنشاء الرسالة سواء كانت نصًا أو مرفقًا
        message = request.env[
            'mail.message'
        ].sudo().create({
            'model': 'support.ticket',
            'res_id': ticket.id,
            'author_id': request.env.user.partner_id.id,
            'subject': (
                f'رسالة جديدة على الطلب {ticket.ticket_number}'
            ),
            'body': html_escape(
                body or 'تم إرسال مرفق في المحادثة.'
            ),
            'message_type': 'comment',
            'attachment_ids': [
                (6, 0, attachment_ids)
            ],
        })

        # تحديد مستلم الإشعار
        recipient_partner = (
            ticket.assignee_id.partner_id
            if is_requester
            else ticket.requester_id.partner_id
        )

        # إشعار الطرف الآخر فقط
        if (
            recipient_partner
            and recipient_partner.id
            != request.env.user.partner_id.id
        ):
            request.env[
                'mail.notification'
            ].sudo().create({
                'mail_message_id': message.id,
                'res_partner_id': recipient_partner.id,
                'notification_type': 'inbox',
                'is_read': False,
            })

            # قناة الشريك الخاصة تمنع الاشتراك في قناة تذكرة قابلة للتخمين.
            request.env[
                'bus.bus'
            ].sudo()._sendone(
                recipient_partner,
                'support_chat_message',
                {
                    'ticket_number': ticket.ticket_number,
                    'message_id': message.id,
                    'author_id': request.env.user.partner_id.id,
                }
            )

        return request.make_json_response({
            'success': True,
            'message': 'تم إرسال الرسالة بنجاح',
            'message_id': message.id,
        })
