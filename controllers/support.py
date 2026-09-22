import base64
from urllib.parse import quote
from odoo import http, fields
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError
from datetime import timedelta


class SupportController(http.Controller):

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
            'note': note or '',
        })

    def _validate_attachment(self, attachment_file):
        if (
            not attachment_file
            or not attachment_file.filename
        ):
            return True, b''
        
        max_file_size = 10 * 1024 * 1024

        allowed_mimetypes = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/png',
            'image/jpeg',
            'video/mp4',
            'video/quicktime',
        }

        file_content = attachment_file.read()

        if len(file_content) > max_file_size:
            return (
                False,
                'حجم الملف يجب ألا يتجاوز 10 ميجابايت.'
            )

        if (
            attachment_file.mimetype
            not in allowed_mimetypes
        ):
            return (
                False,
                'نوع الملف غير مسموح.'
            )

        return True, file_content

    def _is_support_employee(self):
        return request.env.user.has_group(
            'website.group_support_employee'
        )

    def _is_support_manager(self):
        return request.env.user.has_group(
            'website.group_support_manager'
        )

    def _is_support_user(self):
        return (
            self._is_support_employee()
            or self._is_support_manager()
        )   

    @http.route(
        '/support',
        type='http',
        auth='user',
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
        website=True
    )
    def support_employee(self, **kwargs):
        user = request.env.user

        if not user.has_group(
            'website.group_support_employee'
        ):
            return request.not_found()

        # TODO:
        # سجل الموظف المرتبط بالمستخدم الحالي
        # employee = request.env[
        #     'hr.employee'
        # ].sudo().search(
        #     [
        #         (
        #             'user_id',
        #             '=',
        #             user.id
        #         )
        #     ],
        #     limit=1
        # )
        #
        # إدارة صاحب الطلب
        # department_name = (
        #     employee.department_id.name
        #     if employee
        #     and employee.department_id
        #     else ''
        # )

        # مؤقتًا على جهاز التطوير
        department_name = 'المالية'

        return request.render(
            'website.employee',
            {
                'current_user_name': user.name,
                'current_department': department_name,
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
            }
        )
    @http.route(
        '/support/ticket/hold',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=False
    )
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


            self._add_ticket_history(
             ticket=ticket,
             action='hold',
             old_status='processing',
             new_status='on_hold',
             note='تم تعليق الطلب مؤقتًا'
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
        csrf=False
    )
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
        csrf=False
    )
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
        csrf=False
    )
    def mark_support_notifications_read(self, **kwargs):
        data = request.httprequest.get_json(
            silent=True
        ) or {}

        notification_id = data.get(
            'notification_id'
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
                ('id', '=', int(notification_id))
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
        csrf=False
    )

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
        category = request.env['support.category'].search(
            [('name', '=', category_name)],
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
        

        priority_map = {
          'منخفضة': 'low',
          'متوسطة': 'medium',
          'عالية': 'high',
}
    
        
        # TODO: 
        #  إدارة صاحب الطلب من سجل الموظف
        # employee = request.env[
        #     'hr.employee'
        # ].sudo().search(
        #     [
        #         (
        #             'user_id',
        #             '=',
        #             request.env.user.id
        #         )
        #     ],
        #     limit=1
        # )
        #
        # department_id = (
        #     employee.department_id.id
        #     if employee
        #     and employee.department_id
        #     else False
        # )


                            
        ticket = request.env['support.ticket'].create({
            'ticket_number': ticket_number,
            'title': title,
            'description': description,
            'category_id': category.id,
            'priority': priority_map.get(
                priority_value,
                'medium'
            ),
            'status': 'new',
            'requester_id': request.env.user.id,
        # TODO:    
        # 'department_id': department_id,
        })

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
            message = ticket.message_post(
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
                    'name': attachment_file.filename,
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
        ].sudo().browse(
            attachment.res_id
        )

        if not ticket.exists():
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

        filename = quote(
            attachment.name or 'attachment'
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
                    f'attachment; filename="{filename}"'
                ),
            ]
        )
    @http.route(
    '/support/draft/save',
    type='http',
    auth='user',
    methods=['POST'],
    website=True,
    csrf=False
   )
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

        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        category_name = (data.get('category') or '').strip()
        priority_value = (data.get('priority') or '').strip()

        category = False


        if category_name:
            category = request.env['support.category'].search(
            [('name', '=', category_name)],
            limit=1
        )
        attachment_file = request.httprequest.files.get(
            'attachment' 
        )
        file_content = b''
        

        priority_map = {
        'منخفضة': 'low',
        'متوسطة': 'medium',
        'عالية': 'high',
        }

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


        # TODO: عند نقل المشروع إلى بيئة المؤسسة
        # جلب إدارة صاحب الطلب من سجل الموظف
        # employee = request.env[
        #     'hr.employee'
        # ].sudo().search(
        #     [
        #         (
        #             'user_id',
        #             '=',
        #             request.env.user.id
        #         )
        #     ],
        #     limit=1
        # )
        #
        # department_id = (
        #     employee.department_id.id
        #     if employee
        #     and employee.department_id
        #     else False
        # )

        values = {
            'title': title or False,
            'description': description or False,
            'category_id': (
                category.id
                if category
                else False
            ),
            'priority': (
                priority_map.get(priority_value)
                if priority_value
                else False
            ),
            'status': 'draft',
            'requester_id': request.env.user.id,

            # TODO: فعّليه عند نقل المشروع للمؤسسة
            # 'department_id': department_id,
        }

        # تعديل مسودة موجودة
        if draft_id:
            draft = request.env['support.ticket'].search(
                [
                    ('id', '=', int(draft_id)),
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
            draft = request.env['support.ticket'].create(
                   values
           )
        if (
            attachment_file
            and attachment_file.filename
            and file_content                    
        ):
            request.env[
                'ir.attachment'
            ].sudo().create({ 
                'name': attachment_file.filename,
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
         csrf=False
    )
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
        draft = request.env[
            'support.ticket'            
        ].sudo().search(
            [
                ('id', '=', int(draft_id)),
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

        draft.write({
            'ticket_number': ticket_number,
            'status': 'new',
            'submitted_at': fields.Datetime.now(),
        })
        draft._apply_sla_policy()

        # إشعار جميع مسؤولي الدعم بعد إرسال المسودة
        support_group = request.env.ref(
            'website.group_support_manager'
        )

        support_partners = support_group.users.mapped(
            'partner_id'
        )
        if support_partners:
            message = draft.message_post(
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
        csrf=False
    )
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
        draft = request.env[
            'support.ticket'
        ].search(            
            [
                ('id', '=', int(draft_id)),
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

        for ticket in tickets:
            rating_record = request.env['support.rating'].search(
                [('ticket_id', '=', ticket.id)],
                limit=1
            )

            history_records = request.env['support.ticket.history'].search(
                [('ticket_id', '=', ticket.id)],
                order='create_date asc'
            )

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
            attachment_record = request.env['ir.attachment'].sudo().search(
               [
                           ('res_model', '=', 'support.ticket'),
                           ('res_id', '=', ticket.id),
               ],
               order='id desc',
               limit=1
           )
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
        csrf=False
    )
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

        ticket.write({
            'assignee_id': request.env.user.id,
            'status': 'processing',
            'first_response_at': first_response_at,
            'sla_response_status': sla_response_status,
        })

        requester_partner = (
            ticket.requester_id.partner_id
        )

        message = ticket.message_post(
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

        self._add_ticket_history(
        ticket=ticket,
        action='processing',
        old_status='processing',
        new_status='processing',
        note='قيد المعالجة'
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

        for ticket in tickets:

            rating_record = request.env['support.rating'].search(
                [('ticket_id', '=', ticket.id)],
                limit=1
            )

            history_records = request.env['support.ticket.history'].search(
                [('ticket_id', '=', ticket.id)],
                order='create_date asc'
            )

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

            attachment_record = request.env['ir.attachment'].sudo().search(
               [
                           ('res_model', '=', 'support.ticket'),
                           ('res_id', '=', ticket.id),
               ],
               order='id desc',
               limit=1
            ) 

            response_sla = ticket.get_sla_metrics(
                'response'
            )

            resolution_sla = ticket.get_sla_metrics(
                'resolution'
            )

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
                    else 'المالية'
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
       '/support/ticket/solution',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=False
    )
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

        ticket.write({
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

        message = ticket.message_post(
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
        csrf=False
    )
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
            ticket.write({
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

                message = ticket.message_post(
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
            ticket.write({
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

                message = ticket.message_post(
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
        csrf=False
    )
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

        rating = request.env['support.rating'].create({
            'ticket_id': ticket.id,
            'rating': str(rating_value),
            'comment': comment,
            'rated_by': request.env.user.id,
        })

        self._add_ticket_history(
            ticket=ticket,
            action='rating',
            old_status='closed',
            new_status='closed',
            note=f'تم تقييم الخدمة بـ {rating_value} من 5'
        )

        if ticket.assignee_id:
            partner = ticket.assignee_id.partner_id

            message = ticket.message_post(
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
        csrf=False
    )
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
        ].sudo().search(
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
        csrf=False
    )
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
        ].sudo().search(
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
                'name':
                    attachment_file.filename,

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
            'body': body or 'تم إرسال مرفق في المحادثة.',
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

        # إرسال حدث تحديث المحادثة
        request.env[
            'bus.bus'
        ].sudo()._sendone(
            f'support_ticket_{ticket.ticket_number}',
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