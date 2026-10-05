from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    @api.constrains('ticket_id', 'rated_by')
    def _check_rating_rules(self):
        """BR-14: only the requester rates, and only after closure."""
        for rating in self:
            ticket = rating.ticket_id.sudo()

            if ticket.status != 'closed':
                raise ValidationError(
                    'لا يمكن تقييم الطلب قبل إغلاقه.'
                )

            if rating.rated_by != ticket.requester_id:
                raise ValidationError(
                    'التقييم متاح لصاحب الطلب فقط.'
                )

    _sql_constraints = [
        (
            'support_rating_ticket_unique',
            'unique(ticket_id)',
            'لا يمكن إضافة أكثر من تقييم لنفس الطلب.',
        )
    ]