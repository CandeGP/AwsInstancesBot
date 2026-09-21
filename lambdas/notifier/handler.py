"""EventBridge target that turns EC2 / CloudWatch events into Discord notifications.

Handles:
    - EC2 Instance State-change Notification (running, stopped, terminated)
    - CloudWatch Alarm State Change (instance status check alarm)
"""

import logging

import boto3
from botocore.exceptions import ClientError

import messages
import webhook

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ec2 = None


def _client():
    # Created lazily so importing the module opens no connections.
    global _ec2
    if _ec2 is None:
        _ec2 = boto3.client("ec2")
    return _ec2


def _describe(instance_id):
    try:
        reservations = _client().describe_instances(InstanceIds=[instance_id])["Reservations"]
        return reservations[0]["Instances"][0]
    except (ClientError, IndexError, KeyError):
        # The notification is still useful without the IP or the stop reason.
        logger.exception("Could not describe %s", instance_id)
        return None


def _clear_stop_reason(instance_id):
    try:
        _client().delete_tags(Resources=[instance_id], Tags=[{"Key": messages.STOP_REASON_TAG}])
    except ClientError:
        logger.exception("Could not remove the stop reason tag from %s", instance_id)


def lambda_handler(event, context):
    logger.info("Event: %s %s", event.get("detail-type"), event.get("detail"))

    instance = None
    instance_id = event.get("detail", {}).get("instance-id")
    is_state_change = event.get("detail-type") == messages.STATE_CHANGE
    if is_state_change and instance_id and event["detail"].get("state") in ("running", "stopped"):
        instance = _describe(instance_id)

    message = messages.build_message(event, instance)
    if message is None:
        return {"sent": False}

    sent = webhook.send(message)
    # Only consume the reason once it has actually been announced.
    if sent and messages.stop_reason_code(instance):
        _clear_stop_reason(instance_id)
    return {"sent": sent}
