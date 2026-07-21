# Optional GitHub Actions → EC2 deploy

## Recommended shape

1. `workflow_dispatch` or tag `v*`
2. GitHub OIDC → AWS IAM role (deploy-only)
3. Upload release tarball to the backup/deploy S3 bucket
4. SSM Run Command on the AI instance to:
   - download & extract under `/opt/expect-ai/releases/<id>`
   - flip `current` symlink
   - `systemctl restart expect-ai`
   - `curl -sf http://127.0.0.1:8000/health`

## Do not

- Store `TUNNEL_TOKEN` or `AI_API_KEY` in GitHub Actions secrets long-term if SSM Parameter Store is available
- Open SG :8000 for the workflow
- Modify Cloudflare Terraform from this workflow

## IAM for CI role (sketch)

- `s3:PutObject` on deploy prefix
- `ssm:SendCommand` / `GetCommandInvocation` on the AI instance
- No `ec2:TerminateInstances` unless explicitly approved

Wire a concrete `deploy.yml` in a follow-up Issue when the account IDs are known.
