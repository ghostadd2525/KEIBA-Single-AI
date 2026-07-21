# β公開当日 Runbook（Phase13）

**対象:** 管理者が招待制βを安全に公開する当日手順  
**前提:** Phase12 = **GO**（[`release-readiness.md`](./release-readiness.md)）  
**禁止:** コード / API / UI / 契約 / IaC 構造の変更。本ドキュメントは運用のみ。

関連:

- Access 確認: [`release-access-check.md`](./release-access-check.md)
- 招待運用: [`invitation-operation.md`](./invitation-operation.md)
- AI 障害: [`ai-incident-runbook.md`](./ai-incident-runbook.md)
- 公開直後: [`health-checklist.md`](./health-checklist.md)
- 失敗時: [`rollback-runbook.md`](./rollback-runbook.md)
- 日常監視: [`beta-monitoring.md`](./beta-monitoring.md)

---

## 0. デプロイ適用順序（確定）

**この順序を守る。** 後工程を先にやると Access 未保護のまま Pages が晒される、または BFF が AI に届かない。

| 順 | 対象 | 実施内容 | 完了条件 |
|----|------|----------|----------|
| 1 | **Terraform（Access + Tunnel）** | `plan` → 管理者承認 → `apply`。`allowed_emails` / ドメインが非空であること | Access アプリと Tunnel が存在。**Everyone Allow なし** |
| 2 | **Python AI** | `AI_HOST=127.0.0.1` `AI_ALLOW_PUBLIC_BIND=0` で起動。health OK | `127.0.0.1:8000` のみ listen |
| 3 | **Tunnel（cloudflared）** | Tunnel token でコネクタ起動（systemd 可） | Connected / Healthy。外部から :8000 不可 |
| 4 | **Secrets（Pages）** | `AI_BASE_URL` / `AI_API_KEY` / `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` | staging/production 双方（使う環境）に設定 |
| 5 | **Cloudflare Pages（UI + Functions/BFF）** | 本番ブランチをデプロイ（`public` + `functions`）。seed は空または意図した招待のみ | デプロイ成功。`users.json`/`invitations.json` にデモ無し |
| 6 | **Workers 疎通** | Access 通過後に `/api/*`（Functions）が応答 | 401/200 等の期待どおり（未認証は Access で遮断） |
| 7 | **Access 最終確認** | [`release-access-check.md`](./release-access-check.md) サインオフ | 全項目 PASS |
| 8 | **機能スモーク** | Prediction / Analysis / Kaoba | [`health-checklist.md`](./health-checklist.md) |
| 9 | **Invitation 発行** | `npm run beta -- issue` → コミット/デプロイ | `show` で issued |
| 10 | **テスター配布** | URL + 一時IDのみ（パスワードは作らせる） | Access 許可メールにテスター含む |

### コンポーネント対応表

| 名称 | 実体 |
|------|------|
| Cloudflare Pages | UI（`public/`）+ Pages Functions BFF（`functions/`） |
| Workers | Pages Functions（別 Worker プロジェクトにしない） |
| Tunnel | `infra/cloudflare` の Tunnel → AI ホスト `cloudflared` |
| Python AI | `services/win5-ai`（loopback のみ） |
| Secrets | Pages プロジェクトの Environment variables / secrets |
| Terraform | `infra/cloudflare/terraform`（管理者のみ apply） |

```text
[Terraform: Access+Tunnel]
        ↓
[Python AI listen 127.0.0.1]
        ↓
[cloudflared Tunnel Connected]
        ↓
[Pages Secrets]
        ↓
[Pages Deploy]
        ↓
[Access サインオフ]
        ↓
[Health / Invitation / 配布]
```

---

## 1. 公開当日タイムライン（時系列）

想定: 所要 90–180 分（初回 apply 済みなら短縮可）。  
**T-0 = テスターへの配布時刻。**

### T-120 〜 T-90 — 準備

| # | 作業 | 担当 | メモ |
|---|------|------|------|
| A1 | リリースブランチ / タグ確認。デモ seed が混入していないこと | 管理者 | `public/data/users.json` / `invitations.json` |
| A2 | `config/beta.json` と `public/config/beta.json` 同期。`maintenance_mode: true` 推奨（配布直前まで） | 管理者 | スモーク中はメンテでも可 |
| A3 | 連絡チャネル準備（テスター告知・障害連絡） | 運営 | |
| A4 | Rollback 担当と手順の読み合わせ | 運営 | [`rollback-runbook.md`](./rollback-runbook.md) |

### T-90 〜 T-60 — インフラ

| # | 作業 | 完了条件 |
|---|------|----------|
| B1 | Terraform `plan` 確認（差分が意図どおり） | Everyone にならないこと |
| B2 | Terraform `apply`（未適用時のみ。構造変更はしない） | Apply 成功 |
| B3 | Tunnel token / Service Token を安全に取得（ログに残さない） | 値を Secrets へ |
| B4 | Python 起動・health | OK |
| B5 | cloudflared 起動 | Connected |
| B6 | 外部から AI:8000 不可を確認 | 拒否/タイムアウト |

### T-60 〜 T-40 — Pages / Secrets / Access

| # | 作業 | 完了条件 |
|---|------|----------|
| C1 | Pages Secrets 設定・更新 | 4 秘密が揃う |
| C2 | Pages デプロイ | 最新コミットが Active |
| C3 | [`release-access-check.md`](./release-access-check.md) 実施 | サインオフ Yes |
| C4 | 未許可ブラウザで Pages URL | アプリに到達しない |

### T-40 〜 T-20 — 疎通・機能

| # | 作業 | 完了条件 |
|---|------|----------|
| D1 | 許可ユーザーで Access 通過 | login 画面表示 |
| D2 | 運営用に一時招待を 1 件 issue → デプロイ → setup → login | 成功 |
| D3 | Prediction（一覧・1レース詳細） | 実 AI 経路（モックっぽい固定データでないこと） |
| D4 | Analysis | 表示 OK |
| D5 | Kaoba chat | 応答 OK |
| D6 | 監査（CLI JSONL または wrangler tail で `audit:true`） | ログイン等が見える |
| D7 | 検証用招待を `disable` してデプロイ | 再利用不可 |

### T-20 〜 T-5 — 公開準備

| # | 作業 | 完了条件 |
|---|------|----------|
| E1 | テスター分の招待を `issue`（必要数のみ）→ デプロイ | `list --status issued` |
| E2 | Access 許可リストにテスターメール追加済み | |
| E3 | `maintenance_mode: false` に同期してデプロイ（メンテで隠していた場合） | 通常稼働 |
| E4 | [`health-checklist.md`](./health-checklist.md) を一通り PASS | |

### T-0 — 配布

| # | 作業 |
|---|------|
| F1 | テスターへ **Pages URL** + **一時ID** のみ送付（パスワードは送らない） |
| F2 | 事前告知: 障害時はモック表示があり得る・メンテ時は利用停止（[`ai-incident-runbook.md`](./ai-incident-runbook.md)） |
| F3 | setup 完了報告を受けたら [`invitation-operation.md`](./invitation-operation.md) に従い invite disable + デプロイ |
| F4 | 配布後 30 分は待機し、[`health-checklist.md`](./health-checklist.md) を再実行 |

### T+30 / T+終日

| # | 作業 |
|---|------|
| G1 | 重大障害ならメンテ ON または Rollback | [`rollback-runbook.md`](./rollback-runbook.md) |
| G2 | 当日終わりに [`beta-monitoring.md`](./beta-monitoring.md) の「初日」項目を記録 |

---

## 2. コマンド早見（管理者）

```bash
# Terraform（管理者・承認後のみ）
cd infra/cloudflare/terraform
terraform plan
terraform apply

# Python（AI ホスト）
export AI_HOST=127.0.0.1 AI_PORT=8000 AI_ALLOW_PUBLIC_BIND=0
python services/win5-ai/run.py

# Tunnel（AI ホスト）
cloudflared tunnel run --token "$TUNNEL_TOKEN"

# 招待
npm run beta -- issue BETA-.... --note "tester-a"
npm run beta -- list --status issued
npm run beta -- disable <INVITE_ID>

# メンテ
# config/beta.json と public/config/beta.json の maintenance_mode を編集 → Pages デプロイ
```

Pages Secrets 例（プロジェクト名は環境に合わせる）:

```bash
wrangler pages secret put AI_BASE_URL --project-name <PROJECT>
wrangler pages secret put AI_API_KEY --project-name <PROJECT>
wrangler pages secret put CF_ACCESS_CLIENT_ID --project-name <PROJECT>
wrangler pages secret put CF_ACCESS_CLIENT_SECRET --project-name <PROJECT>
```

---

## 3. Go / No-Go（当日）

| 判定 | 条件 |
|------|------|
| **配布してよい** | 適用順序 1–8 完了、Access サインオフ Yes、health PASS、メンテ方針明確 |
| **配布中止** | Everyone 開放、Python 外部公開、Secrets 欠落、Prediction がモックのみ、重大 5xx |

中止時はテスターに送らず、[`rollback-runbook.md`](./rollback-runbook.md) またはメンテ継続。

---

## 4. 役割分担（例）

| 役割 | 責任 |
|------|------|
| インフラ管理者 | Terraform / Access / Tunnel / Secrets |
| アプリ運営 | Pages デプロイ / 招待 CLI / テスター連絡 |
| 監視 | health・当日待機・monitoring 記録 |
