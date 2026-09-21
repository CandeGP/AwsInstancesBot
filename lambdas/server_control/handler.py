"""API Gateway (REST, Lambda proxy) entry point that controls the game server.

Routes:
    GET    /server                                             -> current status
    POST   /server/start                                       -> start the instance
    POST   /server/stop                                        -> stop the instance
    PUT    /config/notifications                               -> set the Discord webhook
"""

import base64
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

import config_service
import ec2_service

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ec2 = None
_ssm = None

ROUTES = {
    ("GET", "/server"): ec2_service.get_status,
    ("POST", "/server/start"): ec2_service.start_server,
    ("POST", "/server/stop"): ec2_service.stop_server,
}
CONFIG_ROUTE = ("PUT", "/config/notifications")


def _client():
    # Clients are created lazily so importing the module (tests, cold start) opens no connections.
    global _ec2
    if _ec2 is None:
        _ec2 = boto3.client("ec2")
    return _ec2


def _ssm_client():
    global _ssm
    if _ssm is None:
        _ssm = boto3.client("ssm")
    return _ssm


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _body(event):
    body = event.get("body")
    if body and event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return body


def _dispatch(method, resource, event):
    route = (method, resource)

    if route == CONFIG_ROUTE:
        # The body holds a secret: it is deliberately never logged.
        return config_service.set_notification_webhook(
            _ssm_client(), os.environ["WEBHOOK_PARAM_NAME"], _body(event)
        )

    action = ROUTES.get(route)
    if action is None:
        raise ec2_service.ServerError(404, "Ruta no encontrada.")
    return action(_client(), os.environ["INSTANCE_ID"])


def lambda_handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")
    logger.info("%s %s", method, resource)

    try:
        return _response(200, _dispatch(method, resource, event))
    except ec2_service.ServerError as error:
        return _response(error.status_code, {"message": error.message})
    except ClientError:
        # Details go to CloudWatch; callers only get a generic message.
        logger.exception("AWS call failed")
        return _response(502, {"message": "Error al comunicarse con AWS."})
