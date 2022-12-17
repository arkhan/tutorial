import re

from odoo import _, api, fields, models
from odoo.addons.res_partner_check_vat.models.utils import normalize
from odoo.exceptions import ValidationError
from stdnum.ec import ci


class ResPartnerChild(models.Model):
    """Partner Children"""

    _name = "res.partner.child"
    _description = __doc__

    partner_id = fields.Many2one("res.partner", string=_("Parent"))
    seq = fields.Integer()
    name = fields.Char(_("Name"), required=True)
    lastname = fields.Char(_("Lastname"))
    birthday = fields.Date(_("Birthday"))
    appoiment = fields.Datetime(_("Appoiment"), default=fields.Datetime.today())
    age = fields.Float(_("Age"), compute="_get_age", store=True)
    age_txt = fields.Char("Age TEXT", compute="_get_age", store=True)
    note = fields.Html(_("Note"))
    active = fields.Boolean(default=True)

    @api.depends("birthday")
    def _get_age(self):
        for row in self:
            age = 0
            age_txt = ""
            if row.birthday:
                birthday = row.birthday
                if isinstance(birthday, str):
                    birthday = fields.Date.from_string(birthday)
                query = "SELECT AGE(CURRENT_DATE, '{date}')::TEXT AS age_txt;".format(
                    date=birthday
                )
                self.env.cr.execute(query)
                query_res = self.env.cr.dictfetchone()
                if query_res:
                    age_txt = query_res.get("age_txt", "")
                age = fields.Date.today().year - birthday.year
            row.age = age
            row.age_txt = age_txt
        return True

    @api.model
    def create(self, vals):
        if "name" in vals:
            vals.update({"name": normalize(vals["name"])})
        return super(ResPartnerChild, self).create(vals)

    @api.multi
    def write(self, vals):
        if "name" in vals:
            vals.update({"name": normalize(vals["name"])})
        return super(ResPartnerChild, self).write(vals)


class ResPartner(models.Model):
    _inherit = "res.partner"

    type_vat = fields.Selection(
        [("ruc", _("RUC")), ("dni", _("Cédula")), ("pasaporte", _("Pasaporte"))],
        string=_("Type VAT"),
        default="dni",
    )
    relative_count = fields.Integer(compute="_count_relatives")
    relative_ids = fields.One2many(
        "res.partner.child", "partner_id", string=_("Partner relatives")
    )

    def action_view_relatives(self):
        action = self.env.ref("res_partner_check_vat.res_partner_child_action").read()[
            0
        ]
        action["domain"] = [("partner_id", "in", self.ids)]
        return action

    @api.depends("relative_ids")
    def _count_relatives(self):
        for row in self:
            row.relative_count = len(row.relative_ids)
        return True

    # Validación en linea mediante @api.onchange
    # @api.onchange("type_vat", "vat")
    # def _onchage_vat(self):
    #     res = {"warning": {}}
    #     title = ""
    #     msg = ""
    #     if self.vat and self.type_vat == "dni":
    #         if len(self.vat) != 10:
    #             title = "Error de longitud!"
    #             msg = "¡El numero de cedula debe tener 10 caracteres!"
    #     if title and msg:
    #         res["warning"].update(
    #             {
    #                 "title": title,
    #                 "message": msg,
    #                 "type": "notification",
    #             },
    #         )
    #     return res

    @api.constrains("company_id", "type_vat", "vat")
    def _check_vat_unique(self):
        for row in self:
            if not row.vat:
                return False
            if row.type_vat == "dni":
                if len(row.vat) != 10 or not ci.is_valid(row.vat):
                    raise ValidationError(_("¡El numero de cedula no es valido!"))
            if row.type_vat == "ruc" and len(row.vat) != 13:
                raise ValidationError(_("¡RUC no valido!"))
            partner_ids = self.search(
                [
                    ("id", "!=", row.id),
                    ("vat", "=", row.vat),
                    ("company_id", "=", row.company_id.id),
                ]
            )
            if partner_ids:
                raise ValidationError(
                    _(
                        "Se encontro otros contactos con el mismo numero de identificación: \n{}".format(
                            "\n".join(map(str, partner_ids.mapped("name")))
                        )
                    )
                )

    @api.model
    def get_all_relatives(self, partner):
        res = []
        if partner:
            query = """
            SELECT rp.name,
                   rp.birthday,
                   age(CURRENT_DATE, rp.birthday)::TEXT AS age
              FROM res_partner_child rp WHERE partner_id = {partner};
            """.format(
                partner=partner.id
            )
            self.env.cr.execute(query)
            res = self.env.cr.dictfetchall()
        return res

    def button_complete_data(self):
        if self.type_vat == "ruc":
            vat = self.vat
            partner_data = self.env["res.partner.sri"].get_sri_data(vat)
            vals = {}
            if vat in partner_data:
                vals.update({"name": partner_data[vat].get("Razon Social")})
            if vals:
                self.write(vals)
        return True
