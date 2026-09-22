from odoo import models, fields


class SupportTicketHistory(models.Model):
    _name = 'support.ticket.history'
    _description = 'Support Ticket History'
    _order = 'create_date desc'

    ticket_id = fields.Many2one(
        'support.ticket',
        string='الطلب',
        required=True,
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        'res.users',
        string='المستخدم',
        required=True,
        default=lambda self: self.env.user,
    )

    action = fields.Char(
        string='الإجراء',
        required=True,
    )

    old_status = fields.Selection(
        [
            ('draft', 'مسودة'),
            ('new', 'جديد'),
            ('processing', 'قيد المعالجة'),
            ('on_hold', 'معلق مؤقتًا'),
            ('waiting_confirmation', 'بانتظار تأكيد الموظف'),
            ('closed', 'مغلق'),
        ],
        string='الحالة السابقة',
    )

    new_status = fields.Selection(
        [
            ('draft', 'مسودة'),
            ('new', 'جديد'),
            ('processing', 'قيد المعالجة'),
            ('on_hold', 'معلق مؤقتًا'),
            ('waiting_confirmation', 'بانتظار تأكيد الموظف'),
            ('closed', 'مغلق'),
        ],
        string='الحالة الجديدة',
    )

    note = fields.Text(
        string='ملاحظة',
    )
