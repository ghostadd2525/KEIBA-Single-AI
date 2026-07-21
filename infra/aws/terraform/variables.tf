variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "name_prefix" {
  type    = string
  default = "expect-ai"
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "root_volume_gb" {
  type    = number
  default = 40
}

variable "ami_id" {
  type        = string
  default     = ""
  description = "Empty = latest Ubuntu 24.04 amd64 from SSM parameter"
}

variable "subnet_id" {
  type        = string
  description = "Subnet for EC2 (prefer private with NAT, or public with minimal SG)"
}

variable "vpc_id" {
  type = string
}

variable "key_name" {
  type        = string
  default     = ""
  description = "EC2 key pair name; empty if SSM-only"
}

variable "enable_ssh" {
  type    = bool
  default = false
}

variable "allowed_ssh_cidrs" {
  type    = list(string)
  default = []
}

variable "enable_cloudwatch_logs" {
  type    = bool
  default = true
}

variable "extra_tags" {
  type    = map(string)
  default = {}
}
