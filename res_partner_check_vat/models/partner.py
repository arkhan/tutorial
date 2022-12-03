from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from stdnum.ec import ci


class ResPartnerChild(models.Model):
    """Partner Children"""

    _name = "res.partner.child"
    _description = __doc__

    partner_id = fields.Many2one("res.partner", string=_("Parent"))
    name = fields.Char(_("Name"), required=True)
    lastname = fields.Char(_("Lastname"))
    birthday = fields.Date(_("Birthday"))


class ResPartner(models.Model):
    _inherit = "res.partner"

    type_vat = fields.Selection(
        [("ruc", _("RUC")), ("dni", _("Cédula")), ("pasaporte", _("Pasaporte"))],
        string=_("Type VAT"),
        default="dni",
    )
    relative_ids = fields.One2many(
        "res.partner.child", "partner_id", string=_("Partner relatives")
    )

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
            if row.type_vat == "dni":
                if len(row.vat) != 10:
                    raise ValidationError(
                        _("¡El numero de cedula debe tener 10 caracteres!")
                    )
                if not ci.is_valid(row.vat):
                    raise ValidationError(_("¡El numero de cedula no es valido!"))
