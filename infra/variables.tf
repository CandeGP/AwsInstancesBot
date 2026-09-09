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