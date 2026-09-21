# Discord notifications
#
# EventBridge (instance state changes + health alarm) -> Lambda notifier -> Discord webhook
#
# The webhook URL is a secret, so it is NOT managed by Terraform (it would end up in the
# state and in CI). It is set from Discord with /notificaciones, which creates the webhook and
# stores it as a SecureString through PUT /config/notifications (see control_api.tf).
# Manual fallback:
#
#   aws ssm put-parameter --name /discord-bot/aws-instances-bot/webhook-url \
#     --type SecureString --value "https://discord.com/api/webhooks/..." --overwrite
#
# Until the parameter exists the notifier logs a warning and sends nothing.

locals {
  # SSM reserves names starting with "aws" or "ssm", so the project name cannot be the first segment.
  webhook_param_name = "/discord-bot/${var.project_name}/webhook-url"
  webhook_param_arn  = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${local.webhook_param_name}"
  instance_arn       = "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/${aws_instance.game_server.id}"
}

data "archive_file" "notifier" {
  type        = "zip"
  output_path = "${path.module}/../lambdas/notifier.zip"

  source {
    content  = file("${path.module}/../lambdas/notifier/handler.py")
    filename = "handler.py"
  }

  source {
    content  = file("${path.module}/../lambdas/notifier/messages.py")
    filename = "messages.py"
  }

  source {
    content  = file("${path.module}/../lambdas/notifier/webhook.py")
    filename = "webhook.py"
  }
}

# ---------------------------------------------------------------------------
# Lambda + least-privilege role
# ---------------------------------------------------------------------------

resource "aws_iam_role" "notifier" {
  name = "${var.project_name}-notifier-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "notifier" {
  name              = "/aws/lambda/${var.project_name}-notifier"
  retention_in_days = 14
}

resource "aws_iam_role_policy" "notifier" {
  name = "${var.project_name}-notifier-policy"
  role = aws_iam_role.notifier.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # DescribeInstances does not support resource-level permissions.
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
      {
        # Removes the LastStopReason tag once the reason has been announced.
        Effect   = "Allow"
        Action   = ["ec2:DeleteTags"]
        Resource = local.instance_arn
      },
      {
        # The SecureString uses the default aws/ssm key, which needs no extra KMS grant.
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = local.webhook_param_arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.notifier.arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "notifier" {
  function_name    = "${var.project_name}-notifier"
  role             = aws_iam_role.notifier.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.notifier.output_path
  source_code_hash = data.archive_file.notifier.output_base64sha256
  timeout          = 20

  environment {
    variables = {
      WEBHOOK_PARAM_NAME = local.webhook_param_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.notifier]
}

# ---------------------------------------------------------------------------
# Health alarm: fires when EC2 status checks fail (only meaningful while running)
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${var.project_name}-status-check"
  alarm_description   = "EC2 status checks are failing on the game server."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.game_server.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0

  # A stopped instance publishes no metrics; that is not a failure.
  treat_missing_data = "notBreaching"
}

# ---------------------------------------------------------------------------
# EventBridge rules -> notifier
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "instance_state" {
  name        = "${var.project_name}-instance-state"
  description = "Game server started, stopped or terminated."

  event_pattern = jsonencode({
    source        = ["aws.ec2"]
    "detail-type" = ["EC2 Instance State-change Notification"]
    detail = {
      "instance-id" = [aws_instance.game_server.id]
      state         = ["running", "stopped", "terminated"]
    }
  })
}

resource "aws_cloudwatch_event_rule" "health_alarm" {
  name        = "${var.project_name}-health-alarm"
  description = "Game server health alarm changed state."

  event_pattern = jsonencode({
    source        = ["aws.cloudwatch"]
    "detail-type" = ["CloudWatch Alarm State Change"]
    detail = {
      alarmName = [aws_cloudwatch_metric_alarm.status_check.alarm_name]
      state     = { value = ["ALARM", "OK"] }
    }
  })
}

resource "aws_cloudwatch_event_target" "notifier" {
  for_each = {
    instance_state = aws_cloudwatch_event_rule.instance_state.name
    health_alarm   = aws_cloudwatch_event_rule.health_alarm.name
  }

  rule      = each.value
  target_id = "notifier-lambda"
  arn       = aws_lambda_function.notifier.arn
}

resource "aws_lambda_permission" "notifier" {
  for_each = {
    instance_state = aws_cloudwatch_event_rule.instance_state.arn
    health_alarm   = aws_cloudwatch_event_rule.health_alarm.arn
  }

  statement_id  = "AllowEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = each.value
}
