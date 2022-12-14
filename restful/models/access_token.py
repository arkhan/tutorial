import hashlib
import logging
import os
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


_logger = logging.getLogger(__name__)

expires_in = "restful.access_token_expires_in"


def nonce(length=40, prefix="access_token"):
    rbytes = os.urandom(length)
    return "{}_{}".format(prefix, str(hashlib.sha1(rbytes).hexdigest()))


class APIAccessToken(models.Model):
    _name = "api.access_token"
    _description = "API Access Token"

    token = fields.Char("Access Token", required=True)
    user_id = fields.Many2one("res.users", string="User", required=True)
    expires = fields.Datetime(string="Expires", required=True)
    scope = fields.Char(string="Scope")
    never_expire = fields.Boolean(string="Never Expire")

    @api.multi
    def find_one_or_create_token(self, user_id=None, create=False, never_expire=False):
        if not user_id:
            user_id = self.env.user.id

        access_token = (
            self.env["api.access_token"]
            .sudo()
            .search([("user_id", "=", user_id)], order="id DESC", limit=1)
        )
        if access_token:
            access_token = access_token[0]
            if access_token.has_expired():
                access_token = None
        if not access_token and create:
            expires = datetime.now() + timedelta(
                seconds=int(self.env.ref(expires_in).sudo().value)
            )
            vals = {
                "user_id": user_id,
                "scope": "userinfo",
                "expires": expires.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                "never_expire": never_expire,
                "token": nonce(),
            }
            access_token = self.env["api.access_token"].sudo().create(vals)
        if not access_token:
            return None
        return access_token.token

    @api.multi
    def is_valid(self, scopes=None):
        """
        Checks if the access token is valid.

        :param scopes: An iterable containing the scopes to check or None
        """
        self.ensure_one()
        return not self.has_expired() and self._allow_scopes(scopes)

    @api.multi
    def has_expired(self):
        self.ensure_one()
        expired = False
        if (
            not self.never_expire
            and self.expires
            and datetime.now() > fields.Datetime.from_string(self.expires)
        ):
            expired = True
        return expired

    @api.multi
    def _allow_scopes(self, scopes):
        self.ensure_one()
        if not scopes:
            return True

        provided_scopes = set(self.scope.split())
        resource_scopes = set(scopes)

        return resource_scopes.issubset(provided_scopes)


class Users(models.Model):
    _inherit = "res.users"
    token_ids = fields.One2many("api.access_token", "user_id", string="Access Tokens")
