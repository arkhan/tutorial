"""Part of odoo. See LICENSE file for full copyright and licensing details."""
import functools
import logging

from odoo import http
from odoo.addons.restful.common import (extract_arguments, invalid_response,
                                        valid_response)
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request


_logger = logging.getLogger(__name__)

expires_in = "restful.access_token_expires_in"

_routes = ["/api/<model>", "/api/<model>/<id>", "/api/<model>/<id>/<action>"]


def validate_token(func):
    """."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        header_token = request.httprequest.headers.get("Authorization")
        access_token = ""
        if header_token:
            access_token = header_token
        if not access_token:
            return invalid_response(
                "access_token_not_found", "missing access token in request header", 401
            )
        access_token_data = (
            request.env["api.access_token"]
            .sudo()
            .search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if (
            access_token_data.find_one_or_create_token(
                user_id=access_token_data.user_id.id
            )
            != access_token
        ):
            return invalid_response(
                "access_token", "token seems to have expired or invalid", 401
            )

        request.session.uid = access_token_data.user_id.id
        request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["api.access_token"]
        self._expires_in = request.env.ref(expires_in).sudo().value

    @http.route(
        "/api/auth/token", methods=["POST"], type="json", auth="none", csrf=False
    )
    def token(self, **post):
        """The token URL to be used for getting the access_token:

        Args:
            **post must contain login and password.
        Returns:

            returns https response code 404 if failed error message in the body in json format
            and status code 202 if successful with the access_token.
        Example:
           import requests

           headers = {'content-type': 'text/plain', 'charset':'utf-8'}

           data = {
               'login': 'admin',
               'password': 'admin',
               'db': 'galago.ng'
            }
           base_url = 'http://odoo.ng'
           eq = requests.post(
               '{}/api/auth/token'.format(base_url), data=data, headers=headers)
           content = json.loads(req.content.decode('utf-8'))
           headers.update(access-token=content.get('access_token'))
        """
        _token = request.env["api.access_token"]
        db = request.jsonrequest.get("db") or request.session.db
        login = request.jsonrequest.get("login")
        password = request.jsonrequest.get("password")
        never_expire = request.jsonrequest.get("never_expire", False)
        if not all([login, password]):
            # Empty 'db' or 'username' or 'password:
            return invalid_response(
                "missing error",
                "either of the following are missing [login, password]",
            )
        # Login in odoo database:
        try:
            request.session.authenticate(db, login, password)
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response(error, info)

        # Login in odoo database:
        try:
            request.session.authenticate(db, login, password)
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, 403)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        access_token = _token.find_one_or_create_token(
            user_id=uid, create=True, never_expire=never_expire
        )
        # Successful response:
        return valid_response(
            {
                "uid": uid,
                "partner_id": uid and request.env.user.partner_id.id or None,
                "user_context": uid and request.session.get_context() or {},
                "company_id": uid and request.env.user.company_id.id or None,
                "company_ids": uid and request.env.user.company_ids.ids or None,
                "access_token": access_token,
                "never_expire": never_expire,
                "expires_in": self._expires_in,
            }
        )

    @http.route(
        "/api/auth/token", methods=["DELETE"], type="http", auth="none", csrf=False
    )
    def delete(self, **post):
        """."""
        _token = request.env["api.access_token"]
        _user = request.env["res.users"]
        login = _user.search([("login", "=", post.get("login"))])
        if not login:
            info = "No user login was provided in request!"
            error = "no_user"
            _logger.error(info)
            return invalid_response(error, info)

        header_token = request.httprequest.headers.get("Authorization")
        try:
            access_token = str(header_token).split()[1]
        except Exception:
            access_token = ""

        access_token = _token.search(
            [
                ("token", "=", access_token),
                (
                    "user_id",
                    "=",
                    login.id,
                ),
            ]
        )
        if not access_token:
            info = "No access token was provided in request!"
            error = "Access token is missing in the request header"
            _logger.error(info)
            return invalid_response(400, error, info)
        for token in access_token:
            token.sudo().unlink()
        # Successful response:
        return valid_response(
            [{"desc": "access token successfully deleted", "delete": True}]
        )


class APIController(http.Controller):
    """."""

    def __init__(self):
        self._model = "ir.model"

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["GET"], csrf=False)
    def get(self, model=None, id=None, **payload):
        try:
            model = (
                request.env[self._model].sudo().search([("model", "=", model)], limit=1)
            )
            if model:
                domain, fields, offset, limit, order = extract_arguments(payload)
                data = request.env[model.model].search_read(
                    domain=domain,
                    fields=fields,
                    offset=offset,
                    limit=limit,
                    order=order,
                )
                if id:
                    domain = [("id", "=", int(id))]
                    data = request.env[model.model].search_read(
                        domain=domain,
                        fields=fields,
                        offset=offset,
                        limit=limit,
                        order=order,
                    )
                if data:
                    return valid_response(data, request="http")
                else:
                    return valid_response(data, request="http")
            return invalid_response(
                "invalid object model",
                "The model %s is not available in the registry." % model,
            )
        except AccessError as e:
            return invalid_response(
                "Access error", "Error: %s" % e.name, request="http"
            )

    @validate_token
    @http.route(_routes, type="json", auth="none", methods=["POST"], csrf=False)
    def post(self, model=None, id=None, **payload):
        """Create a new record.
        Basic sage:
        import requests

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'charset': 'utf-8',
            'access-token': 'access_token'
        }
        data = {
            'name': 'Babatope Ajepe',
            'country_id': 105,
            'child_ids': [
                {
                    'name': 'Contact',
                    'type': 'contact'
                },
                {
                    'name': 'Invoice',
                   'type': 'invoice'
                }
            ],
            'category_id': [{'id': 9}, {'id': 10}]
        }
        req = requests.post('%s/api/res.partner/' %
                            base_url, headers=headers, data=data)

        """
        import ast

        payload = request.jsonrequest
        model = request.env[self._model].search([("model", "=", model)], limit=1)
        values = {}
        if model:
            try:
                # changing IDs from string to int.
                for k, v in payload.items():

                    if "__api__" in k:
                        values[k[7:]] = ast.literal_eval(v)
                    else:
                        values[k] = v

                resource = request.env[model.model].create(values)
            except Exception as e:
                request.env.cr.rollback()
                return invalid_response("params", e)
            else:
                data = resource.read()
                if resource:
                    return valid_response(data)
                else:
                    return valid_response(data)
        return invalid_response(
            "invalid object model",
            "The model %s is not available in the registry." % ioc_name,
        )

    @validate_token
    @http.route(_routes, type="json", auth="none", methods=["PUT"], csrf=False)
    def put(self, model=None, id=None, **payload):
        """."""
        payload = request.jsonrequest
        try:
            _id = int(id)
        except Exception:
            return invalid_response(
                "invalid object id", "invalid literal %s for id with base " % id
            )
        _model = (
            request.env[self._model].sudo().search([("model", "=", model)], limit=1)
        )
        if not _model:
            return invalid_response(
                "invalid object model",
                "The model %s is not available in the registry." % model,
                404,
            )
        try:
            request.env[_model.model].sudo().browse(_id).write(payload)
        except Exception as e:
            request.env.cr.rollback()
            return invalid_response("exception", e.name)
        else:
            return valid_response(
                "update %s record with id %s successfully!" % (_model.model, _id)
            )

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["DELETE"], csrf=False)
    def delete(self, model=None, id=None, **payload):
        """."""
        try:
            _id = int(id)
        except Exception:
            return invalid_response(
                "invalid object id",
                "invalid literal %s for id with base " % id,
                request="http",
            )
        try:
            record = request.env[model].sudo().search([("id", "=", _id)])
            if record:
                record.unlink()
            else:
                return invalid_response(
                    "missing_record",
                    "record object with id %s could not be found" % _id,
                    404,
                    request="http",
                )
        except Exception as e:
            request.env.cr.rollback()
            return invalid_response("exception", e.name, 503, request="http")
        else:
            return valid_response(
                "record %s has been successfully deleted" % record.id, request="http"
            )

    @validate_token
    @http.route(_routes, type="http", auth="none", methods=["PATCH"], csrf=False)
    def patch(self, model=None, id=None, action=None, **payload):
        """."""
        try:
            _id = int(id)
        except Exception:
            return invalid_response(
                "invalid object id",
                "invalid literal %s for id with base " % id,
                request="http",
            )
        try:
            record = request.env[model].sudo().search([("id", "=", _id)])
            _callable = action in [
                method for method in dir(record) if callable(getattr(record, method))
            ]
            if record and _callable:
                # action is a dynamic variable.
                getattr(record, action)()
            else:
                return invalid_response(
                    "missing_record",
                    "record object with id %s could not be found or %s object has no method %s"
                    % (_id, model, action),
                    404,
                    request="http",
                )
        except Exception as e:
            return invalid_response("exception", e, 503, request="http")
        else:
            return valid_response(
                "record %s has been successfully patched" % record.id, request="http"
            )
