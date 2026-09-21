"""API Gateway (REST, Lambda proxy) entry point that controls the game server.

Routes:
    GET  /server        -> current status
    POST /server/start  -> start the instance
    POST /server/stop   -> stop the instance
"""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

import ec2_service

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ec2 = None

ROUTES = {
    ("GET", "/server"): ec2_service.get_status,
    ("POST", "/server/start"): ec2_service.start_server,
    ("POST", "/server/stop"): ec2_service.stop_server,
}


def _client():
    # Created lazily so importing the module (tests, cold start) opens no connections.
    global _ec2
    if _ec2 is None:
        _ec2 = boto3.client("ec2")
    return _ec2


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")
    action = ROUTES.get((method, resource))
    if action is None:
        return _response(404, {"message": "Ruta no encontrada."})

    instance_id = os.environ["INSTANCE_ID"]
    logger.info("%s %s instance=%s", method, resource, instance_id)

    try:
        return _response(200, action(_client(), instance_id))
    except ec2_service.ServerError as error:
        return _response(error.status_code, {"message": error.message})
    except ClientError:
        # Details go to CloudWatch; callers only get a generic message.
        logger.exception("AWS call failed")
        return _response(502, {"message": "Error al comunicarse con AWS."})
