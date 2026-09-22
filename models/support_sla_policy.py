from odoo import models, fields


class SupportSlaPolicy(models.Model):
    _name = 'support.sla.policy'
    _description = 'Support SLA Policy'
    _order = 'priority'

    name = fields.Char(
        string='اسم السياسة',
        required=True,
    )

    category_id = fields.Many2one(
        'support.category',
        string='نوع الطلب',
        required=True,
        ondelete='restrict',
    )

    priority = fields.Selection(
        [
            ('low', 'منخفضة'),
            ('medium', 'متوسطة'),
            ('high', 'عالية'),
        ],
        string='الأولوية',
        required=True,
    )

    response_hours = fields.Float(
        string='ساعات الاستجابة',
        required=True,
    )

    resolution_hours = fields.Float(
        string='ساعات الحل',
        required=True,
    )

    calendar_id = fields.Many2one(
        'resource.calendar',
        string='ساعات العمل',
        required=True,
        default=lambda self: self.env.company.resource_calendar_id,
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
    )

    _sql_constraints = [
        (
            'support_sla_category_priority_unique',
            'unique(category_id, priority)',
            'يوجد بالفعل SLA لهذا النوع والأولوية.',
        )
    ]