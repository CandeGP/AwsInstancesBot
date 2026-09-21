"""Unit tests for the server_control Lambda. Run with:

    python -m unittest discover -s lambdas/tests -t lambdas -v
"""

import json
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server_control"))
os.environ["INSTANCE_ID"] = "i-0123456789abcdef0"
os.environ["WEBHOOK_PARAM_NAME"] = "/discord-bot/aws-instances-bot/webhook-url"

from server_control import config_service  # noqa: E402
from server_control import ec2_service  # noqa: E402
from server_control import handler  # noqa: E402


class FakeEc2:
    def __init__(self, state="stopped"):
        self.state = state
        self.calls = []

    def describe_instances(self, InstanceIds):
        instance = {
            "InstanceId": InstanceIds[0],
            "InstanceType": "t3.micro",
            "State": {"Name": self.state},
            "LaunchTime": datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        }
        if self.state == "running":
            instance["PublicIpAddress"] = "203.0.113.10"
        return {"Reservations": [{"Instances": [instance]}]}

    def start_instances(self, InstanceIds):
        self.calls.append(("start", InstanceIds))

    def stop_instances(self, InstanceIds):
        self.calls.append(("stop", InstanceIds))

    def create_tags(self, Resources, Tags):
        self.calls.append(("tag", Resources, Tags))


def event(method, resource):
    return {"httpMethod": method, "resource": resource}


class ServiceTests(unittest.TestCase):
    def test_status_running_includes_ip(self):
        result = ec2_service.get_status(FakeEc2("running"), "i-1")
        self.assertEqual(result["state"], "running")
        self.assertEqual(result["public_ip"], "203.0.113.10")
        self.assertEqual(result["game_port"], 16261)

    def test_status_stopped_hides_ip(self):
        result = ec2_service.get_status(FakeEc2("stopped"), "i-1")
        self.assertIsNone(result["public_ip"])
        self.assertIsNone(result["launch_time"])

    def test_start_from_stopped_calls_aws(self):
        ec2 = FakeEc2("stopped")
        result = ec2_service.start_server(ec2, "i-1")
        self.assertTrue(result["changed"])
        self.assertEqual(result["state"], "pending")
        self.assertEqual(ec2.calls, [("start", ["i-1"])])

    def test_start_when_running_is_noop(self):
        ec2 = FakeEc2("running")
        result = ec2_service.start_server(ec2, "i-1")
        self.assertFalse(result["changed"])
        self.assertEqual(ec2.calls, [])

    def test_start_while_stopping_conflicts(self):
        with self.assertRaises(ec2_service.ServerError) as ctx:
            ec2_service.start_server(FakeEc2("stopping"), "i-1")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_stop_from_running_calls_aws(self):
        ec2 = FakeEc2("running")
        result = ec2_service.stop_server(ec2, "i-1")
        self.assertTrue(result["changed"])
        self.assertEqual(result["state"], "stopping")
        # The reason tag must be written before the stop so the notifier can read it.
        self.assertEqual(
            ec2.calls,
            [("tag", ["i-1"], [{"Key": "LastStopReason", "Value": "command"}]), ("stop", ["i-1"])],
        )

    def test_stop_still_happens_if_tagging_fails(self):
        ec2 = FakeEc2("running")

        def broken_tags(Resources, Tags):
            raise RuntimeError("AccessDenied")

        ec2.create_tags = broken_tags
        result = ec2_service.stop_server(ec2, "i-1")
        self.assertTrue(result["changed"])
        self.assertEqual(ec2.calls, [("stop", ["i-1"])])

    def test_stop_when_stopped_is_noop(self):
        ec2 = FakeEc2("stopped")
        self.assertFalse(ec2_service.stop_server(ec2, "i-1")["changed"])
        self.assertEqual(ec2.calls, [])

    def test_stop_while_pending_conflicts(self):
        with self.assertRaises(ec2_service.ServerError) as ctx:
            ec2_service.stop_server(FakeEc2("pending"), "i-1")
        self.assertEqual(ctx.exception.status_code, 409)


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.ec2 = FakeEc2("stopped")
        handler._ec2 = self.ec2

    def test_routes_start(self):
        response = handler.lambda_handler(event("POST", "/server/start"), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["state"], "pending")
        self.assertEqual(self.ec2.calls, [("start", ["i-0123456789abcdef0"])])

    def test_routes_status(self):
        response = handler.lambda_handler(event("GET", "/server"), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["state"], "stopped")

    def test_unknown_route_is_404(self):
        response = handler.lambda_handler(event("DELETE", "/server"), None)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(self.ec2.calls, [])

    def test_conflict_maps_to_409(self):
        self.ec2.state = "stopping"
        response = handler.lambda_handler(event("POST", "/server/start"), None)
        self.assertEqual(response["statusCode"], 409)


class FakeSsm:
    def __init__(self):
        self.calls = []

    def put_parameter(self, **kwargs):
        self.calls.append(kwargs)


WEBHOOK = "https://discord.com/api/webhooks/123456789/abc-DEF_ghi"


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.ssm = FakeSsm()
        handler._ssm = self.ssm

    def put(self, body, **extra):
        return handler.lambda_handler({**event("PUT", "/config/notifications"), "body": body, **extra}, None)

    def test_stores_webhook_as_secure_string_and_never_echoes_it(self):
        response = self.put(json.dumps({"webhook_url": WEBHOOK}))
        self.assertEqual(response["statusCode"], 200)
        self.assertNotIn("abc-DEF", response["body"])
        self.assertEqual(
            self.ssm.calls,
            [
                {
                    "Name": "/discord-bot/aws-instances-bot/webhook-url",
                    "Value": WEBHOOK,
                    "Type": "SecureString",
                    "Overwrite": True,
                }
            ],
        )

    def test_accepts_base64_body(self):
        import base64

        encoded = base64.b64encode(json.dumps({"webhook_url": WEBHOOK}).encode()).decode()
        self.assertEqual(self.put(encoded, isBase64Encoded=True)["statusCode"], 200)

    def test_rejects_non_discord_urls(self):
        for url in (
            "https://evil.example/api/webhooks/1/abc",
            "http://discord.com/api/webhooks/1/abc",
            "https://discord.com.evil.example/api/webhooks/1/abc",
            "https://discord.com/api/webhooks/notanumber/abc",
            "",
            None,
            123,
        ):
            response = self.put(json.dumps({"webhook_url": url}))
            self.assertEqual(response["statusCode"], 400, url)
        self.assertEqual(self.ssm.calls, [])

    def test_rejects_invalid_or_missing_body(self):
        self.assertEqual(self.put("not json")["statusCode"], 400)
        self.assertEqual(self.put(None)["statusCode"], 400)
        self.assertEqual(self.put(json.dumps(["x"]))["statusCode"], 400)

    def test_ssm_failure_maps_to_502_without_details(self):
        from botocore.exceptions import ClientError

        def broken(**kwargs):
            raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "secret detail"}}, "PutParameter")

        self.ssm.put_parameter = broken
        response = self.put(json.dumps({"webhook_url": WEBHOOK}))
        self.assertEqual(response["statusCode"], 502)
        self.assertNotIn("secret detail", response["body"])

    def test_config_service_is_the_only_place_that_validates(self):
        with self.assertRaises(config_service.ServerError):
            config_service.set_notification_webhook(self.ssm, "p", "{}")


if __name__ == "__main__":
    unittest.main()
