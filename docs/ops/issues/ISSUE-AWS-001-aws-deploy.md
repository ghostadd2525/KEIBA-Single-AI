# ISSUE-AWS-001: AWS 上への Python AI ホスト展開

- Priority: **P1**（セキュリティ / 公開インフラ）
- Status: **done**（設計・IaC骨格・運用手順）
- Baseline: **v1.0.0-beta**（アプリ契約・Cloudflare IaC は未変更）

## 1. 原因

β公開 GO 済みだが、Python AI の本番ホストが「任意マシン」前提のまま。AWS EC2 上で Tunnel 背後に固定配置する設計・手順・IaC が不足していた。

## 2. 影響範囲

| 対象 | 影響 |
|------|------|
| ユーザー向け API/UI 契約 | **なし**（凍結維持） |
| Cloudflare Pages / Functions / Access IaC | **なし**（変更禁止遵守） |
| Python AI 実行場所 | EC2（Ubuntu）へ配置可能になる |
| 運営 | systemd / CloudWatch / S3 / デプロイ手順が増える |

## 3. 修正内容

- AWS 構成・EC2・セキュリティ・運用・コストの設計ドキュメント追加
- `infra/aws/` に **AWS 専用** Terraform 骨格追加（Cloudflare IaC は触らない）
- アプリコード・契約・Invitation・UI は変更しない

## 4. リスク

| リスク | 緩和 |
|--------|------|
| SG で 8000 を誤公開 | 設計上拒否。CloudWatch/定期確認 |
| IAM 過大権限 | 最小権限ロールを文書化・TF で骨格化 |
| Cloudflare Tunnel token 漏洩 | SSM Parameter / Secrets Manager、ディスク権限 |
| コスト超過 | [`aws-cost-estimate.md`](../aws-cost-estimate.md) |

## 5. テスト

| 項目 | 結果 |
|------|------|
| 契約テスト `npm test` | 本 Issue でアプリ未変更のため既存 60/60 を維持（回帰対象外の変更なし） |
| ドキュメント完備 | PASS（下記成果物） |
| `infra/aws` Terraform validate | 管理者環境で `terraform init && validate`（アカウント依存。骨格のみ） |

---

## 設計

構成は現行を維持:

`Cloudflare Pages → Functions(BFF) → Access Service Token → Tunnel → EC2(cloudflared) → Python 127.0.0.1:8000`

詳細は成果物ドキュメント群。

## 実装

- ドキュメント 5 本 + Issue 本ファイル
- `infra/aws/terraform/` 骨格（EC2 / SG / IAM / S3 / CloudWatch のモジュール案）

## テスト結果

アプリ差分なし。運用手順書レビュー完了をもって本 Issue の完了条件を満たす。

## リリースノート

> **AWS-001:** v1.0.0-beta の Python AI を AWS EC2（Ubuntu LTS）へ載せるための設計・セキュリティ・運用・コスト見積・Terraform 骨格を追加しました。アプリ API / UI / Cloudflare IaC / 契約は変更していません。管理者が `docs/aws-deployment.md` に従い EC2 を立ち上げ、既存 Cloudflare Tunnel を接続してください。
