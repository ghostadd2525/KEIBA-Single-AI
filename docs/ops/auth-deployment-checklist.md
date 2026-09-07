# Auth Deployment Checklist（Production）

**Purpose:** Production で stub 認証デッドロック（ログイン発行 × middleware 拒否）を再発させない  
**Related:** `docs/audit/api-runtime-investigation.md`, Version8.5.1

---

## 必須ルール

`EXPECT_ENV=production`（または `prod`）かつ `AUTH_MODE=stub`（未設定含む）のとき:

| ALLOW_STUB_AUTH | 結果 |
|-----------------|------|
| `1` | 起動可（ブレークグラス） |
| 未設定 / `0` / 他 | **FATAL** — `Production cannot start with stub auth disabled.` |

恒久対策は署名 JWT 等への移行。stub 本番は一時措置のみ。

---

## デプロイ前チェックリスト

- [ ] `wrangler.toml` `[vars]` に `EXPECT_ENV` / `AUTH_MODE` / `ALLOW_STUB_AUTH` を確認
- [ ] Production + stub なら **`ALLOW_STUB_AUTH = "1"`** がある
- [ ] `npm run check:auth:prod` が **exit 0**
- [ ] `infra/cloudflare/env/production.env.example` と矛盾していない
- [ ] Cloudflare Dashboard の Pages → Settings → Environment variables でも `ALLOW_STUB_AUTH=1` を確認（Dashboard 上書きに注意）
- [ ] デプロイ後 `GET /api/health` が **200** かつ `allow_stub_auth: true`
- [ ] `GET /api/health` が **503 `PRODUCTION_AUTH_MISCONFIG`** になっていない

---

## コマンド

```bash
# ローカル / CI（wrangler.toml を検査）
npm run check:auth:prod

# example env も検査
node scripts/ops/check-production-auth.mjs --env-file infra/cloudflare/env/production.env.example

# Pages デプロイ（check 付き）
npm run deploy:pages
```

`deploy:pages` は内部で `check:auth:prod` を実行してから `wrangler pages deploy` する。

---

## デプロイ後スモーク

ADMIN（または有効な stub セッション）で:

| 画面 / API | 期待 |
|------------|------|
| `/api/health` | 200, `expect_env=production`, `allow_stub_auth=true` |
| `/api/users/me` | 200（Bearer あり） |
| ホーム | Prediction 一覧取得（Research Week 中は USER が 503 OPS_CLOSED の場合あり） |
| レース | 一覧または empty（API 成功） |
| マイページ | 会員情報表示 |
| Challenge | API 成功（No Data はデータ欠損時のみ） |

Research Week（日 21:00〜土 0:00 JST）中の **一般 USER** は `OPS_CLOSED` が仕様。ADMIN は bypass。

---

## 事故パターン（禁止）

1. `EXPECT_ENV=production` + `AUTH_MODE=stub` + `ALLOW_STUB_AUTH` 削除してデプロイ  
2. Dashboard だけ `ALLOW_STUB_AUTH` を消し、`wrangler.toml` も無い状態で CLI デプロイ  
3. login は stub 発行のまま、middleware だけ stub 禁止にする（デッドロック）

---

## ランタイム FATAL の見え方

| 経路 | 挙動 |
|------|------|
| Middleware | ほとんどの `/api/*` → 503 `PRODUCTION_AUTH_MISCONFIG` |
| `/api/health` | 503 + 同メッセージ（監視で検知） |
| `/api/ops/public-status` | 到達可（メンテ案内用） |
