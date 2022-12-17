import ast
import datetime
import json
import logging

import werkzeug


_logger = logging.getLogger(__name__)


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def valid_response(data, status=200, request="json"):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {"count": len(data), "data": data}
    res = {}
    if request == "json":
        res = {
            "status": status,
            "content_type": "application/json; charset=utf-8",
            "response": data,
        }
    elif request == "http":
        res = werkzeug.wrappers.Response(
            status=status,
            content_type="application/json; charset=utf-8",
            response=json.dumps(data, default=default),
        )
    return res


def invalid_response(typ, message=None, status=400, request="json"):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    data = {
        "type": typ,
        "message": message and str(message) or "wrong arguments (missing validation)",
    }
    res = {}
    if request == "json":
        res = {
            "status": status,
            "content_type": "application/json; charset=utf-8",
            "response": data,
        }
    elif request == "http":
        res = werkzeug.wrappers.Response(
            status=status,
            content_type="application/json; charset=utf-8",
            response=json.dumps(
                {
                    "type": typ,
                    "message": str(message)
                    if str(message)
                    else "wrong arguments (missing validation)",
                },
                default=datetime.datetime.isoformat,
            ),
        )
    return res


def extract_arguments(payloads, offset=0, limit=0, order=None):
    """Parse additional data  sent along request."""
    fields, domain = [], []

    if payloads.get("domain", None):
        domain = ast.literal_eval(payloads.get("domain"))
    if payloads.get("fields"):
        fields = ast.literal_eval(payloads.get("fields"))
    if payloads.get("offset"):
        offset = int(payloads.get("offset"))
    if payloads.get("limit"):
        limit = int(payloads.get("limit"))
    if payloads.get("order"):
        order = payloads.get("order")
    filters = [domain, fields, offset, limit, order]

    return filters
