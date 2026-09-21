"""Unit tests for the notifier Lambda. Run with:

    python -m unittest discover -s lambdas/tests -t lambdas -v
"""

import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notifier"))
os.environ["WEBHOOK_PARAM_NAME"] = "/discord-bot/aws-instances-bot/webhook-url"

from notifier import handler  # noqa: E402
from notifier import messages  # noqa: E402
from notifier import webhook  # noqa: E402


def state_event(state, instance_id="i-1"):
    return {
        "detail-type": messages.STATE_CHANGE,
        "time": "2026-09-21T19:05:00Z",
        "detail": {"instance-id": instance_id, "state": state},
    }


def alarm_event(state, previous):
    return {
        "detail-type": messages.ALARM_CHANGE,
        "time": "2026-09-21T19:05:00Z",
        "detail": {"state": {"value": state}, "previousState": {"value": previous}},
    }


def instance(ip=None, reason=None):
    data = {"InstanceId": "i-1", "Tags": [{"Key": "Name", "Value": "x"}]}
    if ip:
        data["PublicIpAddress"] = ip
    if reason:
        data["Tags"].append({"Key": messages.STOP_REASON_TAG, "Value": reason})
    return data


class MessageTests(unittest.TestCase):
    def test_running_includes_address_and_local_time(self):
        text = messages.build_message(state_event("running"), instance(ip="203.0.113.10"))
        self.assertIn("`203.0.113.10:16261`", text)
        self.assertIn("<t:", text)

    def test_running_without_ip_still_notifies(self):
        text = messages.build_message(state_event("running"), None)
        self.assertIn("/status", text)

    def test_stopped_by_autostop_says_why(self):
        text = messages.build_message(state_event("stopped"), instance(reason="autostop"))
        self.assertIn("AutoStop", text)

    def test_stopped_by_command_says_why(self):
        text = messages.build_message(state_event("stopped"), instance(reason="command"))
        self.assertIn("/stopserver", text)

    def test_stopped_without_reason_has_no_reason_text(self):
        text = messages.build_message(state_event("stopped"), instance())
        self.assertTrue(text.startswith("🔴 **Servidor apagado**"))
        self.assertNotIn("AutoStop", text)
        self.assertFalse(text.endswith(" "))

    def test_terminated_warns(self):
        self.assertIn("eliminada", messages.build_message(state_event("terminated")))

    def test_transitional_states_are_ignored(self):
        self.assertIsNone(messages.build_message(state_event("pending")))
        self.assertIsNone(messages.build_message(state_event("stopping")))

    def test_alarm_and_recovery(self):
        self.assertIn("fallos de salud", messages.build_message(alarm_event("ALARM", "OK")))
        self.assertIn("recuperó", messages.build_message(alarm_event("OK", "ALARM")))

    def test_ok_after_insufficient_data_is_ignored(self):
        self.assertIsNone(messages.build_message(alarm_event("OK", "INSUFFICIENT_DATA")))

    def test_unknown_event_is_ignored(self):
        self.assertIsNone(messages.build_message({"detail-type": "Other"}))


class FakeEc2:
    def __init__(self, inst):
        self.inst = inst
        self.deleted = []

    def describe_instances(self, InstanceIds):
        return {"Reservations": [{"Instances": [self.inst]}]}

    def delete_tags(self, Resources, Tags):
        self.deleted.append((Resources, Tags))


class HandlerTests(unittest.TestCase):
    def run_handler(self, event, inst, sent=True):
        handler._ec2 = FakeEc2(inst)
        with mock.patch.object(handler.webhook, "send", return_value=sent) as send:
            result = handler.lambda_handler(event, None)
        return result, send, handler._ec2

    def test_stop_sends_message_and_consumes_reason_tag(self):
        result, send, ec2 = self.run_handler(state_event("stopped"), instance(reason="autostop"))
        self.assertTrue(result["sent"])
        self.assertIn("AutoStop", send.call_args.args[0])
        self.assertEqual(ec2.deleted, [(["i-1"], [{"Key": "LastStopReason"}])])

    def test_reason_tag_is_kept_if_message_was_not_sent(self):
        _, _, ec2 = self.run_handler(state_event("stopped"), instance(reason="autostop"), sent=False)
        self.assertEqual(ec2.deleted, [])

    def test_no_tag_cleanup_when_there_is_no_reason(self):
        _, _, ec2 = self.run_handler(state_event("stopped"), instance())
        self.assertEqual(ec2.deleted, [])

    def test_ignored_event_sends_nothing(self):
        result, send, _ = self.run_handler(state_event("pending"), instance())
        self.assertFalse(result["sent"])
        send.assert_not_called()

    def test_alarm_event_does_not_describe_instance(self):
        ec2 = FakeEc2(instance())
        ec2.describe_instances = mock.Mock()
        handler._ec2 = ec2
        with mock.patch.object(handler.webhook, "send", return_value=True):
            handler.lambda_handler(alarm_event("ALARM", "OK"), None)
        ec2.describe_instances.assert_not_called()


class WebhookTests(unittest.TestCase):
    def setUp(self):
        webhook._cache = ("https://discord.example/api/webhooks/1/abc", float("inf"))

    def tearDown(self):
        webhook._cache = None

    def test_success(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            self.assertTrue(webhook.send("hola"))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "AwsInstancesBot-notifier/1.0")
        self.assertIn(b'"parse": []', request.data)

    def test_client_error_is_not_retried(self):
        error = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            self.assertFalse(webhook.send("hola"))

    def test_server_error_and_rate_limit_raise_for_retry(self):
        for code in (429, 503):
            error = urllib.error.HTTPError("u", code, "x", {}, None)
            with mock.patch("urllib.request.urlopen", side_effect=error):
                with self.assertRaises(urllib.error.HTTPError):
                    webhook.send("hola")

    def test_url_is_cached_then_refreshed_after_ttl(self):
        webhook._cache = None
        ssm = mock.Mock()
        ssm.get_parameter.side_effect = [
            {"Parameter": {"Value": "https://discord.example/old"}},
            {"Parameter": {"Value": "https://discord.example/new"}},
        ]
        with mock.patch("boto3.client", return_value=ssm):
            self.assertEqual(webhook._webhook_url(), "https://discord.example/old")
            self.assertEqual(webhook._webhook_url(), "https://discord.example/old")
            self.assertEqual(ssm.get_parameter.call_count, 1)

            url, _ = webhook._cache
            webhook._cache = (url, 0)  # expired
            self.assertEqual(webhook._webhook_url(), "https://discord.example/new")
            self.assertEqual(ssm.get_parameter.call_count, 2)

    def test_missing_parameter_disables_notifications(self):
        from botocore.exceptions import ClientError

        webhook._cache = None
        error = ClientError({"Error": {"Code": "ParameterNotFound", "Message": "x"}}, "GetParameter")
        with mock.patch("boto3.client") as client:
            client.return_value.get_parameter.side_effect = error
            self.assertFalse(webhook.send("hola"))


class ParameterNameTests(unittest.TestCase):
    def test_terraform_parameter_name_is_not_reserved_by_ssm(self):
        # SSM rejects names starting with "aws" or "ssm" (case-insensitive) with
        # "No access to reserved parameter name", which looks like an IAM problem.
        import re

        path = os.path.join(os.path.dirname(__file__), "..", "..", "infra", "notifications.tf")
        with open(path, encoding="utf-8") as tf:
            name = re.search(r'webhook_param_name\s*=\s*"([^"]+)"', tf.read()).group(1)
        self.assertTrue(name.startswith("/"))
        self.assertFalse(name.lstrip("/").lower().startswith(("aws", "ssm")), name)


if __name__ == "__main__":
    unittest.main()
