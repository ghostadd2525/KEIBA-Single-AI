terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = var.name_prefix
  tags = merge(
    {
      Project   = "expect-keiba-ai"
      Baseline  = "v1.0.0-beta"
      Component = "python-ai-host"
      ManagedBy = "terraform-aws"
    },
    var.extra_tags
  )
}
