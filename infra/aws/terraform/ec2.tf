data "aws_ssm_parameter" "ubuntu_ami" {
  count = var.ami_id == "" ? 1 : 0
  name  = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-volume-type/gp3/ami-id"
}

locals {
  ami_id = var.ami_id != "" ? var.ami_id : data.aws_ssm_parameter.ubuntu_ami[0].value
}

resource "aws_security_group" "ai" {
  name        = "${local.name_prefix}-ec2"
  description = "Expect Python AI — no public :8000"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []
    content {
      description = "SSH admin"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.allowed_ssh_cidrs
    }
  }

  egress {
    description = "HTTPS for Tunnel, apt, AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP for apt (optional; tighten if possible)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name_prefix}-ec2-sg" })
}

resource "aws_instance" "ai" {
  ami                    = local.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ai.id]
  iam_instance_profile   = aws_iam_instance_profile.ai.name
  key_name               = var.key_name != "" ? var.key_name : null

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required"
  }

  user_data = <<-EOF
              #!/bin/bash
              set -euo pipefail
              # SSM agent is present on Ubuntu AWS images in most regions.
              # App install is intentional (see docs/aws-deployment.md) — not auto-cloned here.
              EOF

  tags = merge(local.tags, { Name = "${local.name_prefix}-ec2" })
}

resource "aws_cloudwatch_log_group" "expect_ai" {
  count             = var.enable_cloudwatch_logs ? 1 : 0
  name              = "/expect/ai/expect-ai"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "cloudflared" {
  count             = var.enable_cloudwatch_logs ? 1 : 0
  name              = "/expect/ai/cloudflared"
  retention_in_days = 14
  tags              = local.tags
}
