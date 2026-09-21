output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.game_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the game server."
  value       = aws_instance.game_server.public_ip
}

output "security_group_id" {
  description = "Security group ID attached to the game server."
  value       = aws_security_group.game_server.id
}

output "auto_stop_lambda_name" {
  description = "Name of the AutoStop Lambda."
  value       = aws_lambda_function.auto_stop.function_name
}


output "server_api_url" {
  description = "Base URL of the server control API (use as SERVER_API_URL in the bot)."
  value       = aws_api_gateway_stage.server_control.invoke_url
}

output "server_api_key" {
  description = "API key for the server control API (use as SERVER_API_KEY in the bot). Read with: terraform output -raw server_api_key"
  value       = aws_api_gateway_api_key.bot.value
  sensitive   = true
}

output "server_control_lambda_name" {
  description = "Name of the server control Lambda."
  value       = aws_lambda_function.server_control.function_name
}

output "notifier_lambda_name" {
  description = "Name of the Discord notifier Lambda."
  value       = aws_lambda_function.notifier.function_name
}

output "discord_webhook_ssm_parameter" {
  description = "SSM parameter (SecureString) holding the Discord webhook URL. Set it with /notificaciones in Discord."
  value       = local.webhook_param_name
}
