from odoo import models, fields


class SupportRating(models.Model):
    _name = 'support.rating'
    _description = 'Support Rating'
    _order = 'create_date desc'

    ticket_id = fields.Many2one(
        'support.ticket',
        string='الطلب',
        required=True,
        ondelete='cascade',
    )

    rating = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
        ],
        string='التقييم',
        required=True,
    )

    comment = fields.Text(
        string='ملاحظة التقييم',
    )

    rated_by = fields.Many2one(
        'res.users',
        string='تم التقييم بواسطة',
        required=True,
        default=lambda self: self.env.user,
    )

    _sql_constraints = [
        (
            'support_rating_ticket_unique',
            'unique(ticket_id)',
            'لا يمكن إضافة أكثر من تقييم لنفس الطلب.',
        )
    ]