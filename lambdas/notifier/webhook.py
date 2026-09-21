"""Sends messages to a Discord webhook whose URL lives in SSM Parameter Store (SecureString)."""

import json
import logging
import os
import time
import urllib.error
import urllib.request

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()

# The URL can be changed from Discord (/notificaciones), so a warm Lambda must not
# keep the old one forever.
CACHE_SECONDS = 300

_cache = None  # (url, monotonic expiry)


def _webhook_url():
    global _cache
    if _cache is not None and time.monotonic() < _cache[1]:
        return _cache[0]

    name = os.environ["WEBHOOK_PARAM_NAME"]
    try:
        response = boto3.client("ssm").get_parameter(Name=name, WithDecryption=True)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ParameterNotFound":
            logger.warning("SSM parameter %s does not exist yet; notifications are disabled.", name)
            return None
        raise
    url = response["Parameter"]["Value"]
    _cache = (url, time.monotonic() + CACHE_SECONDS)
    return url


def send(content):
    """Posts `content` to the webhook. Returns True if Discord accepted it.

    Configuration problems and permanent client errors are logged and return False (retrying
    would not help). Transient failures (5xx, 429, network) raise so EventBridge retries.
    """
    url = _webhook_url()
    if not url:
        return False

    request = urllib.request.Request(
        url,
        data=json.dumps({"content": content, "allowed_mentions": {"parse": []}}).encode("utf-8"),
        # Discord rejects the default Python-urllib User-Agent.
        headers={"Content-Type": "application/json", "User-Agent": "AwsInstancesBot-notifier/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500 and error.code != 429:
            logger.error("Discord rejected the webhook call: HTTP %s", error.code)
            return False
        raise
