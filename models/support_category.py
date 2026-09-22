from odoo import models, fields


class SupportCategory(models.Model):
    _name = 'support.category'
    _description = 'Support Category'

    name = fields.Char(
        string='اسم التصنيف',
        required=True,
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
    )

    _sql_constraints = [
        (
            'support_category_name_unique',
            'unique(name)',
            'اسم التصنيف يجب أن يكون فريدًا.',
        )
    ]