"""Runtime configuration that the bot can change from Discord.

Currently only the Discord webhook used by the notifier Lambda. The URL is stored as a
SecureString in SSM Parameter Store and is never returned or logged.
"""

import json
import re

from ec2_service import ServerError

# Only real Discord webhook URLs are accepted, so this route cannot be used to make the
# notifier post to (or leak data to) an arbitrary host.
_WEBHOOK_URL = re.compile(r"^https://(?:(?:canary|ptb)\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$")


def set_notification_webhook(ssm, param_name, body):
    try:
        data = json.loads(body or "")
    except ValueError:
        raise ServerError(400, "El cuerpo de la peticion debe ser JSON.")

    url = data.get("webhook_url") if isinstance(data, dict) else None
    if not isinstance(url, str) or not _WEBHOOK_URL.match(url):
        raise ServerError(400, "webhook_url no es una URL de webhook de Discord valida.")

    ssm.put_parameter(Name=param_name, Value=url, Type="SecureString", Overwrite=True)
    return {"message": "Canal de notificaciones actualizado."}
