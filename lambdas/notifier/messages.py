"""Builds the Discord message for an EventBridge event. Pure functions, no AWS calls."""

from datetime import datetime

GAME_PORT = 16261

# Tag set by AutoStop and /stopserver right before stopping, read (and removed) by the notifier.
STOP_REASON_TAG = "LastStopReason"
STOP_REASONS = {
    "autostop": "Se apagó automáticamente por inactividad (AutoStop).",
    "command": "Se apagó con /stopserver.",
}

STATE_CHANGE = "EC2 Instance State-change Notification"
ALARM_CHANGE = "CloudWatch Alarm State Change"


def _tag(instance, key):
    for tag in (instance or {}).get("Tags", []):
        if tag["Key"] == key:
            return tag["Value"]
    return None


def stop_reason_code(instance):
    return _tag(instance, STOP_REASON_TAG)


def _when(event):
    # Discord renders <t:epoch:t> in each reader's own timezone.
    try:
        moment = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return ""
    return f" (<t:{int(moment.timestamp())}:t>)"


def _state_change(event, instance):
    state = event["detail"]["state"]
    when = _when(event)

    if state == "running":
        ip = (instance or {}).get("PublicIpAddress")
        address = f"`{ip}:{GAME_PORT}`" if ip else "la IP aún no está disponible, usa /status en un momento"
        return f"🟢 **Servidor encendido**{when}. Conéctate a {address}."

    if state == "stopped":
        reason = STOP_REASONS.get(stop_reason_code(instance), "")
        return f"🔴 **Servidor apagado**{when}. {reason}".rstrip()

    if state == "terminated":
        return f"⚫ **La instancia del servidor fue eliminada**{when}. Revisa AWS: el mundo del juego pudo perderse."

    return None


def _alarm_change(event):
    detail = event["detail"]
    state = detail["state"]["value"]
    when = _when(event)

    if state == "ALARM":
        return f"⚠️ **El servidor tiene fallos de salud**{when} (falló la verificación de estado de EC2). Puede necesitar reinicio."
    # OK only matters as a recovery; OK after INSUFFICIENT_DATA is just the instance booting.
    if state == "OK" and detail.get("previousState", {}).get("value") == "ALARM":
        return f"✅ **El servidor se recuperó**{when}. La verificación de estado volvió a la normalidad."
    return None


def build_message(event, instance=None):
    """Returns the message text, or None when the event does not deserve a notification."""
    kind = event.get("detail-type")
    if kind == STATE_CHANGE:
        return _state_change(event, instance)
    if kind == ALARM_CHANGE:
        return _alarm_change(event)
    return None
