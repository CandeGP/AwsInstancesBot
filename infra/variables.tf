variable "aws_region" {
  description = "AWS region where the game server will be created."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for AWS resource names."
  type        = string
  default     = "aws-instances-bot"
}

variable "instance_type" {
  description = "EC2 instance type for the game server."
  type        = string
  default     = "t3.micro" #cambiamos la version de la instancia de m5.large a t3.micro, aws no me deja pq es muy caro
}

variable "root_volume_size_gb" {
  description = "Size of the encrypted root volume in GB."
  type        = number
  default     = 20
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed to access SSH. Keep empty to disable SSH ingress."
  type        = list(string)
  default     = []
}

variable "auto_stop_enabled" {
  description = "Enables the scheduled AutoStop rule."
  type        = bool
  default     = true
}

variable "auto_stop_schedule" {
  description = "EventBridge schedule for the AutoStop check, in UTC."
  type        = string
  default     = "rate(15 minutes)"
}

variable "auto_stop_cpu_threshold" {
  description = "Average CPU percentage at or below which an instance is considered idle."
  type        = number
  default     = 5
}

variable "auto_stop_idle_minutes" {
  description = "How long CPU must remain below the threshold before stopping."
  type        = number
  default     = 30
}