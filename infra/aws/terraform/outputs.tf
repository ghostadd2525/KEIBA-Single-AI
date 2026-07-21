output "instance_id" {
  value = aws_instance.ai.id
}

output "security_group_id" {
  value = aws_security_group.ai.id
}

output "instance_role_arn" {
  value = aws_iam_role.ai.arn
}

output "backup_bucket" {
  value = aws_s3_bucket.backup.bucket
}

output "private_ip" {
  value = aws_instance.ai.private_ip
}

output "next_steps" {
  value = "Install cloudflared + expect-ai per docs/aws-deployment.md; point Pages AI_BASE_URL at existing Tunnel hostname."
}
