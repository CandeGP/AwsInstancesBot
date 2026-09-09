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

