from odoo import models, fields, _, api


class ResPartnerChild(models.Model):
    """Partner Children"""

    _name = "res.partner.child"
    _description = __doc__

    partner_id = fields.Many2one('res.partner', string=_("Parent"))
    name = fields.Char(_("Name"), required=True)
    birthday = fields.Date(_('Birthday'), required=True)
#    age = fields.Float(_('Age'), compute="_get_age")

#    @api.multi
#    def _get_age(self):
#        for row in self:
#            if row.birthday:
#                row.age = fields.Date.today().year - row.birthday.year
#        return True
