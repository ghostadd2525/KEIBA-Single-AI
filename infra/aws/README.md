# AWS Terraform — Expect Python AI host

**Scope:** AWS only. Do **not** modify `infra/cloudflare/`.  
**Docs:** [`docs/aws-architecture.md`](../../docs/aws-architecture.md)

```bash
cd infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply   # admin approval required
```

Modules (flat files in this skeleton):

| File | Resources |
|------|-----------|
| `main.tf` | provider, locals |
| `network.tf` | optional default VPC SG |
| `iam.tf` | instance role + instance profile |
| `s3.tf` | backup bucket |
| `ec2.tf` | instance + CW log group stubs |
| `variables.tf` / `outputs.tf` | |

GitHub Actions notes: [`../github-actions/README.md`](../github-actions/README.md)
