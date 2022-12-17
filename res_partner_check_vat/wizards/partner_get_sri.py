#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import html_to_json
from bs4 import BeautifulSoup
from odoo import _, api, fields, models
from odoo.addons.res_partner_check_vat.models.utils import normalize
from odoo.exceptions import ValidationError
from requests import get


_logger = logging.getLogger(__name__)

BASE_URL = "https://srienlinea.sri.gob.ec/facturacion-internet/consultas/publico/ruc-datos2.jspa?ruc="


class PartnerSRIData(models.TransientModel):
    """Partner SRI Data"""

    _name = "res.partner.sri"
    _description = __doc__

    partner_id = fields.Many2one("res.partner", string=_("Partner"))

    @api.model
    def get_sri_data(self, ruc):
        data = get(BASE_URL + ruc)
        bs = BeautifulSoup(data.text, "html.parser")
        json_data = html_to_json.convert(
            str(bs.html.body.find("table", {"class", "formulario"}))
        )
        ruc_data = {}

        if "table" in json_data:
            ruc_data = {ruc: {}}
            for frm in json_data.get("table"):
                for line in frm.get("tr"):
                    if "th" in line:
                        value = line.get("td")[0].get("_value")
                        if (
                            "_value" not in line.get("td")[0]
                            and "a" in line.get("td")[0]
                        ):
                            value = line.get("td")[0].get("a", False)[0].get("_value")
                        ruc_data[ruc].update(
                            {normalize(line.get("th")[0].get("_value")): value}
                        )
        return ruc_data

    def button_complete_data(self):
        if self.partner_id and self.partner_id.type_vat == "ruc":
            vat = self.partner_id.vat
            partner_data = self.get_sri_data(vat)
            vals = {}
            if vat in partner_data:
                vals.update({"name": partner_data[vat].get("Razon Social")})
            if vals:
                self.partner_id.write(vals)
        else:
            raise ValidationError("El contacto no tiene un ruc Valido")
        return True
