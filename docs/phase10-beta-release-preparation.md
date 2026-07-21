# Phase10: Beta Release Preparation

**Status:** Implemented  
**目的:** 招待制βを安全に開始・運営できる状態（機能追加なし）  
**禁止遵守:** PredictionBundle / Analysis / Kaoba 契約変更なし、Cloudflare IaC 変更なし、UI デザイン変更なし、API 契約変更なし

---

## 1. CLI 一覧

入口: `npm run beta -- <command> ...`（実装: `scripts/beta-admin.mjs`）

| コマンド | 用途 |
|----------|------|
| `issue <INVITE_ID> [--note] [--expires]` | 招待発行（issued） |
| `list [--status STATUS]` | 招待一覧 |
| `disable <INVITE_ID>` | 招待停止 |
| `disable --user <USER_ID>` | アカウント停止 |
| `enable <INVITE_ID>` | 招待再有効化 |
| `enable --user <USER_ID>` | アカウント再開 |
| `show <INVITE_ID>` | 招待詳細（紐づくユーザー要約） |
| `reset-password <USER_ID> <NEW_PASSWORD>` | パスワード再設定 |

互換: `node scripts/issue-invite.mjs ...` → `beta-admin issue` に委譲。

データ: `public/data/invitations.json` / `users.json`  
監査追記: `logs/audit/beta-audit.jsonl`  
テスト分離: `BETA_ADMIN_ROOT`

---

## 2. 監査ログ仕様

### 形式

JSONL（1行1イベント）。Workers では `console.log` に `{ "audit": true, ... }`。CLI はファイル追記。

### フィールド

| フィールド | 型 | 説明 |
|------------|-----|------|
| `ts` | string (ISO) | 時刻 |
| `type` | string | イベント種別 |
| `ok` | boolean | 成否 |
| `actor` | string\|null | 実行者（user_id / cli） |
| `target` | string\|null | 対象（invite_id / user_id） |
| `detail` | object | 付加情報 |
| `request_id` | string\|null | cf-ray 等（Workers） |
| `source` | string | CLI のみ `"cli"` |

### イベント種別（必須）

| type | 発火点 |
|------|--------|
| `login_success` | POST `/api/auth/login` 成功 |
| `login_failure` | 同 失敗 |
| `invitation_used` | POST `/api/auth/invite/start` |
| `setup_complete` | POST `/api/auth/setup` 成功 |
| `account_disabled` | CLI `disable --user` |
| `prediction_used` | `/api/predictions*` 成功（middleware） |
| `analysis_used` | `/api/analysis/*` 成功 |
| `kaoba_used` | `/api/kaoba/chat` 成功 |

追加（運営）: `invitation_issued` / `invitation_disabled` / `invitation_enabled` / `password_reset` / `account_enabled`

実装: `functions/_lib/auditLog.js`

---

## 3. beta.json 仕様

正本: `config/beta.json`  
ASSETS: `public/config/beta.json`（同期必須）  
読込: `functions/_lib/betaConfig.js` → `/config/beta.json`

| キー | 型 | 説明 |
|------|-----|------|
| `schema_version` | string | `expect-beta-config/1.0` |
| `beta_name` | string | β名称 |
| `maintenance_mode` | boolean | true で Auth 以外の `/api/*` を 503 |
| `maintenance_message` | string | メンテメッセージ |
| `terms_version` | string | setup 時に記録 |
| `invitation_required` | boolean | 招待制フラグ（現状 true） |
| `max_concurrent_sessions` | number\|null | 将来用 |
| `audit.enabled` | boolean | 利用監査 |
| `audit.sink` | string | `jsonl` |

---

## 4. 運営マニュアル

[`beta-operation.md`](./beta-operation.md)

---

## 5. 公開前チェックリスト

[`beta-security-checklist.md`](./beta-security-checklist.md)

---

## 6. 変更ファイル一覧

| パス | 内容 |
|------|------|
| `scripts/beta-admin.mjs` | 運営 CLI |
| `scripts/issue-invite.mjs` | issue 互換ラッパー |
| `config/beta.json` | 運営設定正本 |
| `public/config/beta.json` | ASSETS 同期 |
| `functions/_lib/betaConfig.js` | 設定読込 |
| `functions/_lib/auditLog.js` | 監査 JSONL |
| `functions/_middleware.js` | Auth / メンテ / 利用監査 |
| `functions/_lib/userRepository.js` | setStatus / setPassword / list |
| `functions/_lib/invitationRepository.js` | enable |
| `functions/api/auth/login.js` | ログイン監査 |
| `functions/api/auth/invite/start.js` | 招待利用監査 |
| `functions/api/auth/setup.js` | 初回設定監査 + terms_version |
| `docs/beta-operation.md` | 運営マニュアル |
| `docs/beta-security-checklist.md` | 公開前チェック |
| `docs/phase10-beta-release-preparation.md` | 本成果物 |
| `tests/contract/beta-ops.test.mjs` | Phase10 テスト |
| `package.json` | `beta` / test スクリプト |
| `.gitignore` | audit JSONL |
| `logs/audit/.gitkeep` | 監査ディレクトリ |

---

## 7. テスト結果

```text
npm test
ℹ tests 60
ℹ pass 60
ℹ fail 0
```

Phase10 追加: `tests/contract/beta-ops.test.mjs`（beta.json 同期・AuditEvent・CLI・docs）  
既存契約・スナップショットもすべて PASS。
