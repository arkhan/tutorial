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
    birthday_txt = fields.Char("Birthday TEXT")
    appoiment = fields.Datetime(_("Appoiment"), default=fields.Datetime.today())
    age = fields.Float(_("Age"), compute="_get_age", store=True)
    note = fields.Html(_("Note"))
    active = fields.Boolean(default=True)

    @api.depends("birthday", "birthday_txt")
    def _get_age(self):
        for row in self:
            age = 0
            if row.birthday or row.birthday_txt:
                birthday = row.birthday or row.birthday_txt
                if isinstance(birthday, str):
                    birthday = fields.Date.from_string(birthday)
                age = fields.Date.today().year - birthday.year
            row.age = age
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
