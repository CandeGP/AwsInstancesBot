"""EC2 operations for the game server: read status, start and stop.

All functions take the boto3 EC2 client as a parameter so they can be tested
with a fake client and never create AWS connections on import.
"""

GAME_PORT = 16261

# States in which the instance is already on its way to (or at) each goal.
_RUNNING_STATES = {"running", "pending"}
_STOPPED_STATES = {"stopped", "stopping"}


class ServerError(Exception):
    """Business error that maps directly to an HTTP status code."""

    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _describe(ec2, instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    reservations = response.get("Reservations", [])
    if not reservations or not reservations[0].get("Instances"):
        raise ServerError(404, "La instancia del servidor no existe.")
    return reservations[0]["Instances"][0]


def _summary(instance, state=None):
    state = state or instance["State"]["Name"]
    is_running = state == "running"
    launch_time = instance.get("LaunchTime")
    return {
        "instance_id": instance["InstanceId"],
        "state": state,
        "instance_type": instance["InstanceType"],
        # The public IP changes on every start, so it is only meaningful while running.
        "public_ip": instance.get("PublicIpAddress") if is_running else None,
        "game_port": GAME_PORT,
        "launch_time": launch_time.isoformat() if is_running and launch_time else None,
    }


def get_status(ec2, instance_id):
    instance = _describe(ec2, instance_id)
    return {**_summary(instance), "message": "Estado del servidor consultado."}


def start_server(ec2, instance_id):
    instance = _describe(ec2, instance_id)
    state = instance["State"]["Name"]

    if state in _RUNNING_STATES:
        return {**_summary(instance), "changed": False, "message": "El servidor ya esta encendido o arrancando."}
    if state != "stopped":
        raise ServerError(409, f"El servidor esta en estado '{state}'. Intenta de nuevo en unos minutos.")

    ec2.start_instances(InstanceIds=[instance_id])
    return {**_summary(instance, state="pending"), "changed": True, "message": "Encendiendo el servidor."}


def stop_server(ec2, instance_id):
    instance = _describe(ec2, instance_id)
    state = instance["State"]["Name"]

    if state in _STOPPED_STATES:
        return {**_summary(instance), "changed": False, "message": "El servidor ya esta apagado o apagandose."}
    if state != "running":
        raise ServerError(409, f"El servidor esta en estado '{state}'. Intenta de nuevo en unos minutos.")

    ec2.stop_instances(InstanceIds=[instance_id])
    return {**_summary(instance, state="stopping"), "changed": True, "message": "Apagando el servidor."}
