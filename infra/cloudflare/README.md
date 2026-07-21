# Cloudflare Zero Trust — Phase9-A（管理者適用用）

**このディレクトリは IaC / 設定テンプレートです。**  
`terraform apply` やダッシュボード操作は **管理者が実施**します。CI/エージェントは Cloudflare アカウントを変更しません。

仕様正本: [`docs/phase9-access-control.md`](../../docs/phase9-access-control.md)  
成果物まとめ: [`docs/phase9-a-access-infrastructure.md`](../../docs/phase9-a-access-infrastructure.md)

```
infra/cloudflare/
  terraform/          … Access / Tunnel 用 Terraform
  cloudflared/        … コネクタ設定例
  policies/           … Access Policy の論理定義（参照用 JSON）
  env/                … 環境別変数テンプレート
```

## 適用順序（管理者）

1. Zero Trust チーム作成・WARP 配布方針決定  
2. `terraform/` の `terraform.tfvars` を埋める → `plan` → `apply`  
3. Tunnel トークンで Python ホスト上に `cloudflared` を起動  
4. Pages に staging/production の Secrets を設定（`env/*.env.example` 参照）  
5. [`docs/phase9-a-access-infrastructure.md`](../../docs/phase9-a-access-infrastructure.md) §8 で動作確認  
