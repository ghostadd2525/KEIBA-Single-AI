# 一時ID発行機能 — 設計レビュー

**Date:** 2026-07-21  
**Status:** **設計提出 / 承認待ち**（承認後にのみ実装）  
**対象リポジトリ:** `C:\win5-ai\KEIBA-Single-AI`（本番認証。`expect-keiba-ai` は UI プロトタイプで auth 非関与）  
**制約:** 既存ログイン画面の **デザイン（HTML/CSS 見た目）は変更しない**

---

## 0. 背景と既存との関係

現状の「一時ID（初回）」は **招待 → setup → 恒久アカウント作成** である。

| 既存 | 本要件 |
|------|--------|
| `invitations` + `/api/auth/invite/start` → `setup_token` | **新規** `temporary_login_tokens` |
| 初回設定で login_id/password 作成 | 一時IDだけで **セッション発行** |
| 1回で `activated`（アカウント化） | 1回で `used`（ログイン消費） |
| CLI `beta-admin issue` | 管理者 API + 管理画面 |

**方針:** 既存 invite/setup フローは **維持**。本機能は並走する **ワンタイム・ログイン用トークン** として新設する。  
ログイン画面のタブ名・レイアウト・CSS は触らない。同一「一時ID」入力欄から、トークン種別で分岐する（見た目不変・JS 配線のみ最小）。

```text
[一時ID入力] ──► 種別判定
                  ├─ temporary_login_token → セッション発行 → アプリへ
                  └─ invitation (既存)     → setup_token → setup.html
```

---

## 1. データモデル

### 1.1 論理テーブル `temporary_login_tokens`

| 列 | 型 | 説明 |
|----|-----|------|
| `id` | UUID | 主キー（内部） |
| `token_hash` | string | **平文は保存しない**（§6） |
| `token_prefix` | string(8) | 一覧・照合用の先頭プレフィックス（平文） |
| `status` | enum | `active` / `used` / `expired` / `revoked` |
| `expires_at` | datetime (UTC) | 有効期限 |
| `used_at` | datetime \| null | 利用日時 |
| `issued_by` | string | 発行者 user_id / login_id |
| `created_at` | datetime (UTC) | 発行日時 |
| `revoked_at` | datetime \| null | 任意（失効時刻） |
| `revoke_reason` | string \| null | 任意 |

要件の `token` 列は **平文ではなく `token_hash`** とする（セキュリティ §6）。API 応答の `temporary_id` のみ平文を一度返す。

### 1.2 永続化方針（β → 本番）

| 段階 | 保存先 | 備考 |
|------|--------|------|
| **β（推奨実装）** | Cloudflare Pages Functions 側: Durable 相当が無いため、**まず** `public/data/temporary_login_tokens.json` + メモリオーバーレイ（`invitations.json` と同型） | 既存 auth β と一貫 |
| **本番候補** | SQLite（AI DB）または Cloudflare D1 | マイグレーション `00x_temporary_login_tokens.sql` |

設計上の契約（列・status・ハッシュ）はストレージ実装に依存しない。

**自動失効:** 読み取り・一覧・ログイン検証時に `expires_at < now` かつ `status=active` なら **`expired` に遷移**（lazy expiry）。バッチは任意。

---

## 2. トークン生成

| 項目 | 仕様 |
|------|------|
| 乱数 | `crypto.getRandomValues` / Node `crypto.randomBytes` **32 bytes** |
| エンコード | URL-safe Base64（約 43 文字）または UUID v4 + 追加乱数 |
| 形式例 | `tmp_<base64url>`（プレフィックスで invite と区別しやすくする） |
| 有効期限 | デフォルト **24h**（発行 API で上書き可、上限例: 168h） |
| 利用 | **single-use**（成功ログインで `used`） |

---

## 3. API 設計

### 3.1 発行（管理者のみ）

`POST /api/admin/temporary-login-tokens`

**認証:** Bearer access + `role=ADMIN`（または `EXPECT_ADMIN_USER_IDS` / `admin_user_ids` allowlist）

**Request（例）:**

```json
{
  "expires_in_hours": 24
}
```

**Response 201:**

```json
{
  "schema_version": "expect-auth/1.1",
  "temporary_id": "tmp_…",
  "expires_at": "2026-07-22T01:00:00.000Z",
  "invite_url": "https://expect-keiba.com/login?id=tmp_…",
  "id": "…",
  "status": "active",
  "issued_by": "admin-user-id",
  "created_at": "2026-07-21T01:00:00.000Z"
}
```

- `invite_url` のオリジンは env `PUBLIC_SITE_ORIGIN`（未設定時はリクエスト Origin / 既定本番ドメイン）。
- **平文 `temporary_id` はこの応答のみ**。以降はハッシュ照合。

### 3.2 一覧（管理者）

`GET /api/admin/temporary-login-tokens?status=&limit=`

返却は平文トークンを含まない:

```json
{
  "items": [
    {
      "id": "…",
      "token_prefix": "tmp_Ab12",
      "status": "active",
      "expires_at": "…",
      "used_at": null,
      "issued_by": "…",
      "created_at": "…"
    }
  ]
}
```

### 3.3 失効（管理者）

`POST /api/admin/temporary-login-tokens/:id/revoke`

- `active` → `revoked`
- 既に `used` / `expired` / `revoked` は 409 + 理由

### 3.4 ログイン（一時ID）

`POST /api/auth/temporary-login`

**Request:**

```json
{ "temporary_id": "tmp_…" }
```

（互換: `id` / `temp_id` も受理）

**検証順:**

1. 正規化・空チェック  
2. ハッシュ照合でレコード存在  
3. `status === active`  
4. `now < expires_at`（切れなら `expired` に更新して失敗）  
5. 未使用（`used_at` null）

**成功:**

- `status = used`, `used_at = now`（原子的に）  
- **アクセスセッション発行**（既存 `makeStubToken` / access purpose、TTL は現行 access と同じ 24h）  
- 紐づくユーザー: **ゲスト用システムユーザー** または発行時に紐づけた `guest` ロール（下記 §3.5）

**失敗コード（例）:**

| code | HTTP | 意味 |
|------|------|------|
| `TEMP_ID_NOT_FOUND` | 404 | 存在しない |
| `TEMP_ID_USED` | 409 | 使用済 |
| `TEMP_ID_EXPIRED` | 410 | 期限切れ |
| `TEMP_ID_REVOKED` | 403 | 失効 |
| `TEMP_ID_INACTIVE` | 400 | その他 |

### 3.5 セッション主体（要承認ポイント）

一時IDログイン成功時、誰としてセッションを持つか:

| 案 | 内容 | 推奨 |
|----|------|------|
| **A. Guest セッション** | `sub=temp:<token_id>`, `role=USER`（または `GUEST`）, 恒久 users 行は作らない | **推奨（招待ログインに近い）** |
| **B. 都度ユーザー作成** | 使い捨て login_id を users に作成 | 運用が重い |
| **C. 既存 invite に合流** | setup 必須のまま | **本要件（即セッション）と不一致** |

**設計採択案: A**。`/api/auth/me` は guest プロファイル（表示名「ゲスト」等）を返す。権限は一般 USER 相当（管理 API 不可）。

---

## 4. ログイン画面との接続（デザイン非変更）

| 変更してよい | 変更禁止 |
|--------------|----------|
| `login.html` 内 JS の API 呼び出し分岐（最小） | レイアウト / 文言の見た目大幅変更 / `login.css` のビジュアル改修 |
| `?id=` クエリで入力欄へ自動入力（既存があれば流用） | タブ構成のデザイン変更 |

**推奨フロー（見た目そのまま）:**

1. ユーザーが「一時ID（初回）」欄に入力して送信（現状どおり）  
2. JS: まず `POST /api/auth/temporary-login`  
   - 成功 → 既存と同様に token を保存し **アプリへ**（setup へ行かない）  
   - `TEMP_ID_NOT_FOUND` → 既存 `POST /api/auth/invite/start` にフォールバック（初回招待）  
3. エラー表示は既存のエラー領域を流用

これにより **デザイン変更ゼロ**で両系統を共存させる。

---

## 5. 管理画面

新規: `public/admin/temporary-ids.html`（または既存 admin がある場合はその配下）

| 機能 | UI |
|------|-----|
| 新規発行 | 有効期限（時間）選択 → 発行 → **平文IDと invite_url を一度だけ表示**（コピー） |
| 一覧 | prefix / status / expires_at / issued_by / used_at |
| Revoke | active 行にボタン |

**保護:** ページ入場時に `/api/auth/me` で ADMIN 確認。非 ADMIN は拒否。  
CLI 互換: `scripts/beta-admin.mjs` に `temp-issue|temp-list|temp-revoke` を追加（任意・同一 API 呼び出し）。

---

## 6. セキュリティ

| 項目 | 仕様 |
|------|------|
| 保存 | `token_hash = SHA-256(token + server_pepper)` または既存 password 形式に合わせ `sha256$<pepper>$<hex>` |
| Pepper | env `TEMP_LOGIN_TOKEN_PEPPER`（未設定時は開発用固定を禁止し、起動警告） |
| 平文 | DB/JSON に保存しない。発行レスポンスのみ |
| 一覧 | prefix のみ（推測困難性は本体乱数に依存） |
| レート制限 | `/temporary-login` は IP あたり試行制限（設計: 10/min、実装段階で） |
| 監査 | 発行・利用・失効を `auditLog` に記録 |
| 推測 | 32 bytes 乱数（UUID 単独より長い） |

---

## 7. 契約・互換

- `contracts/expect-auth` を **1.1** に拡張（temporary-login / admin tokens）  
- 既存 `invite/start` / `setup` / `login` は破壊しない  
- Feature Flag（任意）: `TEMP_LOGIN_TOKENS_ENABLED` 既定 ON（β）

---

## 8. 実装スコープ（承認後）

1. Repository（hash 保存・lazy expire・atomic use）  
2. Admin API 3本 + temporary-login API  
3. 管理画面 HTML（新規）  
4. `login.html` の JS 分岐のみ（CSS/レイアウト不変）  
5. 単体テスト（発行・単回利用・期限・revoke・ハッシュ非保存）  
6. ドキュメント更新（`auth-service.md`）

**非スコープ（本設計）:** Prediction / Collector / RePick、ログイン CSS リデザイン、invite フロー廃止。

---

## 9. 承認チェックリスト

- [ ] 既存 invite/setup と並走（破壊しない）  
- [ ] Guest セッション案 A でよいか  
- [ ] 平文非保存（hash + prefix）でよいか  
- [ ] β は JSON+メモリ、本番は後続永続化でよいか  
- [ ] ログイン **デザイン非変更**・JS 分岐のみでよいか  
- [ ] 管理画面を新規 HTML でよいか  

---

## 10. 結論

**管理者発行・24h・single-use・hash 保存の `temporary_login_tokens` を新設し、管理 API/画面と `/api/auth/temporary-login` で即セッションを発行する。ログイン画面の見た目は維持し、同一入力から invite と分岐する。実装は本設計の承認後に着手する。**
