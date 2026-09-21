# Discord bot -> API Gateway -> Lambda (Python) -> EC2
#
# Routes (all require the x-api-key header):
#   GET  /server        status
#   POST /server/start  start the game server
#   POST /server/stop   stop the game server
#   PUT  /config/notifications  set the Discord webhook for notifications (used by /notificaciones)

data "aws_region" "current" {}

# Explicit sources keep the zip deterministic (no __pycache__ or test files).
data "archive_file" "server_control" {
  type        = "zip"
  output_path = "${path.module}/../lambdas/server_control.zip"

  source {
    content  = file("${path.module}/../lambdas/server_control/handler.py")
    filename = "handler.py"
  }

  source {
    content  = file("${path.module}/../lambdas/server_control/ec2_service.py")
    filename = "ec2_service.py"
  }

  source {
    content  = file("${path.module}/../lambdas/server_control/config_service.py")
    filename = "config_service.py"
  }
}

# ---------------------------------------------------------------------------
# Lambda + least-privilege role (separate from the AutoStop role)
# ---------------------------------------------------------------------------

resource "aws_iam_role" "server_control" {
  name = "${var.project_name}-server-control-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "server_control" {
  name              = "/aws/lambda/${var.project_name}-server-control"
  retention_in_days = 14
}

resource "aws_iam_role_policy" "server_control" {
  name = "${var.project_name}-server-control-policy"
  role = aws_iam_role.server_control.id

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
        Effect = "Allow"
        # CreateTags records the stop reason ("command") for the Discord notification.
        Action   = ["ec2:StartInstances", "ec2:StopInstances", "ec2:CreateTags"]
        Resource = local.instance_arn
      },
      {
        # Lets /notificaciones replace the Discord webhook. Write-only: the Lambda cannot read it back.
        Effect   = "Allow"
        Action   = ["ssm:PutParameter"]
        Resource = local.webhook_param_arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.server_control.arn}:*"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

resource "aws_lambda_function" "server_control" {
  function_name    = "${var.project_name}-server-control"
  role             = aws_iam_role.server_control.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.server_control.output_path
  source_code_hash = data.archive_file.server_control.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      INSTANCE_ID        = aws_instance.game_server.id
      WEBHOOK_PARAM_NAME = local.webhook_param_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.server_control]
}

resource "aws_lambda_permission" "server_control_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.server_control.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.server_control.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# API Gateway (REST) with API key + usage plan
# ---------------------------------------------------------------------------

resource "aws_api_gateway_rest_api" "server_control" {
  name        = "${var.project_name}-server-control"
  description = "Control API for the game server, called by the Discord bot."

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "server" {
  rest_api_id = aws_api_gateway_rest_api.server_control.id
  parent_id   = aws_api_gateway_rest_api.server_control.root_resource_id
  path_part   = "server"
}

resource "aws_api_gateway_resource" "server_action" {
  for_each = toset(["start", "stop"])

  rest_api_id = aws_api_gateway_rest_api.server_control.id
  parent_id   = aws_api_gateway_resource.server.id
  path_part   = each.key
}

resource "aws_api_gateway_resource" "config" {
  rest_api_id = aws_api_gateway_rest_api.server_control.id
  parent_id   = aws_api_gateway_rest_api.server_control.root_resource_id
  path_part   = "config"
}

resource "aws_api_gateway_resource" "config_notifications" {
  rest_api_id = aws_api_gateway_rest_api.server_control.id
  parent_id   = aws_api_gateway_resource.config.id
  path_part   = "notifications"
}

locals {
  api_methods = {
    status = { resource_id = aws_api_gateway_resource.server.id, http_method = "GET" }
    start  = { resource_id = aws_api_gateway_resource.server_action["start"].id, http_method = "POST" }
    stop   = { resource_id = aws_api_gateway_resource.server_action["stop"].id, http_method = "POST" }

    notifications = { resource_id = aws_api_gateway_resource.config_notifications.id, http_method = "PUT" }
  }
}

resource "aws_api_gateway_method" "server_control" {
  for_each = local.api_methods

  rest_api_id      = aws_api_gateway_rest_api.server_control.id
  resource_id      = each.value.resource_id
  http_method      = each.value.http_method
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "server_control" {
  for_each = local.api_methods

  rest_api_id             = aws_api_gateway_rest_api.server_control.id
  resource_id             = each.value.resource_id
  http_method             = aws_api_gateway_method.server_control[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.server_control.invoke_arn
}

resource "aws_api_gateway_deployment" "server_control" {
  rest_api_id = aws_api_gateway_rest_api.server_control.id

  # Redeploy whenever a route or integration changes.
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.server,
      aws_api_gateway_resource.server_action,
      aws_api_gateway_resource.config,
      aws_api_gateway_resource.config_notifications,
      aws_api_gateway_method.server_control,
      aws_api_gateway_integration.server_control,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "server_control" {
  rest_api_id   = aws_api_gateway_rest_api.server_control.id
  deployment_id = aws_api_gateway_deployment.server_control.id
  stage_name    = "v1"
}

resource "aws_api_gateway_api_key" "bot" {
  name = "${var.project_name}-bot"
}

resource "aws_api_gateway_usage_plan" "bot" {
  name = "${var.project_name}-bot"

  api_stages {
    api_id = aws_api_gateway_rest_api.server_control.id
    stage  = aws_api_gateway_stage.server_control.stage_name
  }

  throttle_settings {
    rate_limit  = 5
    burst_limit = 10
  }

  quota_settings {
    limit  = 1000
    period = "DAY"
  }
}

resource "aws_api_gateway_usage_plan_key" "bot" {
  key_id        = aws_api_gateway_api_key.bot.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.bot.id
}
