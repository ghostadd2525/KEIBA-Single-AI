# API Runtime Investigation — Production No Data

**Date:** 2026-07-27（JST）  
**Scope:** 本番 `https://expect-keiba.com` — ホーム / レース / チャレンジ / マイページが No Data・取得失敗  
**Method:** 実 HTTP プローブ + BFF コード経路照合（推測排除）  
**Code fix:** 本ドキュメントは原因特定のみ（修正未実施）

---

## 結論（原因）

**主因は AI / DB 障害ではなく、Cloudflare Pages Functions の認証ミドルウェアでリクエストが遮断されていること。**

二重ゲートが同時に効いている。

| # | ゲート | 条件 | 結果 |
|---|--------|------|------|
| **A（主因）** | `STUB_AUTH_FORBIDDEN` | `EXPECT_ENV=production` かつ `ALLOW_STUB_AUTH≠1` かつ `AUTH_MODE=stub`（または Bearer 付き） | **HTTP 401** — ログイン後のほぼ全 `/api/*` |
| **B（副因）** | `OPS_CLOSED` | Research Week（`ops_mode=CLOSED`）かつ Bearer **なし** かつ ADMIN bypass なし | **HTTP 503** — 未認証の商品 API |

ログイン API はいまも **stub トークンを発行**する一方、本番ミドルウェアは stub（および `AUTH_MODE=stub` 時の Bearer 付き要求）を拒否する。  
→ **「ログイン成功 → 以降の API が全部 401」** のデッドロック。

AI / PI まで到達していない（BFF 手前で落ちる）。

Ops が「表示される」理由: `/ops` は静的 HTML + **認証不要の** `/ops-data/*.json` が読める。商品画面は認証付き API 必須のため全滅しやすい。

---

## 到達マップ

```
Browser
  ↓  Authorization: Bearer <login が発行した stub.*>
Pages（静的 HTML は配信成功）
  ↓
Functions `_middleware.js`
  ↓ requireAuth()
  ✖ 401 STUB_AUTH_FORBIDDEN   ← ここで停止（主因）
  （Bearer 無しなら）
  ✖ 503 OPS_CLOSED            ← Research Week（副因）
  ✕ BFF ハンドラ未到達
  ✕ AI API 未呼び出し
  ✕ DB 未到達
```

健康な経路の対照:

```
Browser（Bearer 無し）→ /api/health → 200（exempt）
Browser → /api/ops/public-status → 200（exempt）→ ops_mode=CLOSED を返却
Browser → /ops-data/*.json → 200（静的・認証不要）
```

---

## ① Browser Network 相当（実プローブ）

※ 本番ブラウザの DevTools には未接続。同等の Request URL / Status / Body を urllib で取得。

### 共通ヘッダ

| 項目 | 値 |
|------|-----|
| Accept | `application/json` |
| User-Agent | Chrome 相当 |
| Cookie | 未使用（トークンは Bearer / localStorage 想定） |
| Authorization | なし / `Bearer stub.…` / `Bearer not-a-stub.token` |

### 画面別想定リクエストと実測

| 画面 | 主な API | Authorization | HTTP | Response code | 本文要旨 |
|------|----------|---------------|------|---------------|----------|
| ホーム | `/api/predictions` 等 | Bearer stub | **401** | `STUB_AUTH_FORBIDDEN` | stub authentication is not allowed in production (Version8.5.1) |
| ホーム | 同上 | なし | **503** | `OPS_CLOSED` | Research Week メンテ |
| レース | `/api/races` `/api/race-cards` | Bearer stub | **401** | `STUB_AUTH_FORBIDDEN` | 同上 |
| レース | 同上 | なし | **503** | `OPS_CLOSED` | 同上 |
| チャレンジ | `/api/v1/challenge/dashboard` | Bearer stub | **401** | `STUB_AUTH_FORBIDDEN` | 同上 |
| チャレンジ | 同上 | なし | **503** | `OPS_CLOSED` | 同上 |
| マイページ | `/api/users/me` `/api/auth/me` | Bearer stub | **401** | `STUB_AUTH_FORBIDDEN` | 同上 |
| マイページ | 同上 | なし | **401** | `UNAUTHORIZED`（要ログイン） | login required 系 |
| Ops | `/api/ops/portal` `/api/ops/console` | Bearer stub | **401** | `STUB_AUTH_FORBIDDEN` | API は失敗 |
| Ops | `/ops-data/portal-snapshot.json` 等 | なし | **200** | JSON | **静的 Publish は成功** |
| 共通 | `/api/health` | なし | **200** | ok | `expect_env=production`, PI ok, RA degraded |
| 共通 | `/api/ops/public-status` | なし | **200** | ok | `ops_mode=CLOSED`, Research Week |

### 実測レスポンス原文（抜粋）

**Bearer なし `/api/races` → 503**

```json
{
  "ok": false,
  "error": {
    "code": "OPS_CLOSED",
    "message": "ただいまメンテナンス中です（Research Week）。日曜 21:00 〜 土曜 0:00（JST）はご利用いただけません。…",
    "details": null
  }
}
```

**Bearer stub `/api/races` → 401**

```json
{
  "ok": false,
  "error": {
    "code": "STUB_AUTH_FORBIDDEN",
    "message": "stub authentication is not allowed in production (Version8.5.1)",
    "details": null
  }
}
```

**非 stub の適当な Bearer でも → 401 `STUB_AUTH_FORBIDDEN`**  
（`AUTH_MODE=stub` かつ production かつ `ALLOW_STUB_AUTH≠1` のため、`mode === "stub"` 分岐で Bearer 付きが一律拒否）

**`/api/ops/public-status` → 200（メンテ状態の正本）**

```json
{
  "ops_mode": "CLOSED",
  "reason": "research_week_maintenance",
  "maintenance": true,
  "maintenance_start": "2026-07-26T21:00:00+09:00",
  "maintenance_end": "2026-08-01T00:00:00+09:00",
  "schedule_reason": "Research Week",
  "next_open_date_jst": "2026-08-01"
}
```

UI 文言との対応:

| UI | クライアント側 |
|----|----------------|
| 「Prediction API からレース一覧を取得できませんでした」 | `index.html` — Prediction fetch 失敗時 |
| 「レースがありません」 | `races.html` — 空配列 / 取得失敗後の empty |
| Challenge「No Data」 | `challenge-dashboard.js` — API 失敗時 |
| マイページ会員情報不可 | `/api/users/me` 401 |

---

## ② BFF（Functions）到達状況

| API | 到達 | Status | 遮断層 |
|-----|------|--------|--------|
| `/api/health` | ✅ ハンドラ | 200 | exempt |
| `/api/ops/public-status` | ✅ ハンドラ | 200 | exempt |
| `/api/system/status` | ✅ ハンドラ | 200 | exempt |
| `/api/races` | ✖ middleware | 401 or 503 | auth / ops_mode |
| `/api/race-cards` | ✖ middleware | 401 or 503 | 同上 |
| `/api/predictions` | ✖ middleware | 401 or 503 | 同上 |
| `/api/v1/challenge/dashboard` | ✖ middleware | 401 or 503 | 同上 |
| `/api/users/me` | ✖ middleware / requireAccessSession | 401 | auth |
| `/api/auth/me` | ✖ middleware | 401 | auth |
| `/api/ops/portal` | ✖ middleware | 401 or 503 | auth / ops_mode |
| `/api/auth/login` | ✅（POST は auth 後に到達し得る） | 400/401 は資格情報 | ログイン自体は動くが **発行トークンが後段で使えない** |

Status 分布（今回のプローブ）:

| Status | 意味 |
|--------|------|
| 200 | health / public-status / system-status / 静的 ops-data |
| 401 | `STUB_AUTH_FORBIDDEN` または未ログイン `UNAUTHORIZED` |
| 503 | `OPS_CLOSED`（Research Week） |
| 404/500/502 | **商品 API では未観測**（手前で落ちているため） |

---

## ③ AI API

| 項目 | 結果 |
|------|------|
| BFF→AI 呼び出し | **商品 API 経路では未実行**（middleware で遮断） |
| `/api/health` 経由の AI/RA 要約 | 到達（`ai_proxy_configured: true`） |
| RA health | `unhealthy`（failed_latest あり）— **今回の No Data 主因ではない** |
| PI health | `ok` / latency ~18ms — **健全** |

Timeout / AI 502 はホーム・レース全滅の説明にならない（リクエストが AI に届いていない）。

---

## ④ 認証

| 項目 | 実態 |
|------|------|
| ログイン発行 | `functions/api/auth/login.js` → 常に `makeStubToken(...)` |
| トークン形式 | `stub.<base64urlpayload>.<exp>` |
| Cookie セッション | なし（Bearer + localStorage `expect_access_token_v1`） |
| 本番ポリシー | `EXPECT_ENV=production` → stub 禁止（`ALLOW_STUB_AUTH=1` のみ例外） |
| `wrangler.toml` | `AUTH_MODE = "stub"`, `EXPECT_ENV = "production"`（`ALLOW_STUB_AUTH` なし） |
| health 実測 | `expect_env: "production"` |
| role / user_id | stub payload 例: `sub=admin-20260721`（※ role claim は検証時破棄設計） |
| 認証が通っているか | **通っていない**（Bearer 付きは 401） |

コード根拠（`functions/_lib/auth.js`）:

- Bearer なし → `requireAuth` は通過（`if (!token) return null`）
- production + stub 禁止 + (`stub` トークン **または** `AUTH_MODE=stub`) → `STUB_AUTH_FORBIDDEN`

Version8.5.1 認定書の既知残件と一致:

> 署名 JWT 未実装 — 本番 identity は当面 `ALLOW_STUB_AUTH=1` のブレークグラスが必要  
> （`docs/audit/v851-final-certification.md`）

---

## ⑤ Cloudflare Pages / Functions デプロイ

| 項目 | 結果 |
|------|------|
| 最新 Production デプロイ | `a026d196-…`（数分〜十数分前、Functions bundle 含む） |
| 直前 | `833250e9-…`（Publish Layer） |
| Static のみ更新か | **いいえ** — `Uploading Functions bundle` 済み |
| Functions と Pages 世代 | **一致**（同一 Pages deploy） |
| 今回の No Data 主因が「古い Functions」か | **否** — 現行 Functions の auth / ops_mode が意図どおり（厳格）に動いている |

---

## ⑥ 共通ライブラリ（今回変更の影響）

| 領域 | 判定 |
|------|------|
| `public/assets/api/client.js` fetch wrapper | **破壊なし** — Bearer 付与・エラー throw は正常。401/503 を UI エラーに変換しているだけ |
| Auth クライアント | **破壊なし** — トークン保存・送信は正常 |
| BFF Proxy (`aiProxy` / `piProxy`) | 商品経路未到達のため **今回の症状の直接原因ではない** |
| Ops Console / Publish Layer 変更 | 商品 API の auth/middleware を変更していない |
| `_middleware.js` / `auth.js` | V8.5.1 ポリシーどおり。**設定（ALLOW_STUB_AUTH 欠落 + AUTH_MODE=stub + production）との組み合わせが破綻** |

---

## ⑦ Version8.5.1 Baseline との差分

| 項目 | 8.5.1 | 現状 |
|------|-------|------|
| stub 本番禁止 | 仕様（PASS） | **稼働中** → 401 |
| 署名 JWT | 未実装（残件） | **依然未実装** |
| ブレークグラス `ALLOW_STUB_AUTH=1` | 認定書で必須と明記 | **未設定（実測で拒否）** |
| Research Week OPS_CLOSED | V7/V8 仕様 | **CLOSED 中**（〜 2026-08-01 00:00 JST） |
| Publish / Ops Console | 8.5.1 以降の追加 | 静的 ops-data は成功。商品 API とは別経路 |

API Layer / Auth / Proxy の「ロジック退行バグ」ではなく、**8.5.1 セキュリティ強化 + 本番ブレークグラス未投入 + stub ログインのまま**という構成不整合。

---

## 失敗 API 一覧（要約）

| API | 典型 Status | Error code | 到達点 |
|-----|-------------|------------|--------|
| `/api/predictions` | 401 / 503 | STUB_AUTH_FORBIDDEN / OPS_CLOSED | Middleware |
| `/api/races` | 401 / 503 | 同上 | Middleware |
| `/api/race-cards` | 401 / 503 | 同上 | Middleware |
| `/api/v1/challenge/dashboard` | 401 / 503 | 同上 | Middleware |
| `/api/users/me` | 401 | STUB_AUTH_FORBIDDEN / UNAUTHORIZED | Middleware |
| `/api/auth/me` | 401 | 同上 | Middleware |
| `/api/ops/portal` | 401 / 503 | 同上 | Middleware |
| `/api/ops/console` | 401（要認証） | STUB_AUTH_FORBIDDEN | Middleware |

成功（対照）:

| API / 資産 | Status |
|------------|--------|
| `/api/health` | 200 |
| `/api/ops/public-status` | 200 |
| `/api/system/status` | 200 |
| `/ops-data/*.json` | 200 |

---

## 修正案（実施はしない・提案のみ）

### 即時（運用ブレークグラス）

1. Cloudflare Pages Production に **`ALLOW_STUB_AUTH=1`** を設定（Version8.5.1 認定どおりの一時措置）
2. 再デプロイまたは vars 反映後、ログイン → Bearer stub で商品 API が middleware を通過するか確認
3. Research Week 中は **一般 USER は 503 OPS_CLOSED が仕様**。ADMIN は role bypass で通過（認証が通った場合）

### 恒久

1. 署名 JWT（または CF Access / 適切な verifier）を実装し、`AUTH_MODE` を stub から移行  
2. `login.js` の `makeStubToken` 依存を解消  
3. production では `ALLOW_STUB_AUTH` をデフォルト OFF のまま維持

### 切り分け確認コマンド（修正後）

```text
# 1) ログインで得た token で
GET /api/users/me          → 200 期待
GET /api/races             → 200（ADMIN）または 503 OPS_CLOSED（USER・Research Week）
GET /api/predictions       → 同上
# 2) Bearer 無し
GET /api/races             → 503 OPS_CLOSED（Week 中）
GET /api/health            → 200
```

---

## Ops が表示される理由（矛盾の解消）

1. `/ops` HTML は静的配信（`data-skip-auto-maintenance`）  
2. Publish 済み `/ops-data/*` は **認証不要で 200**（Research / Knowledge 等の実値の一部はここから見える）  
3. 商品画面は **必ず認証付き BFF** に依存 → 401/503 で文言どおり失敗  
4. Ops の `/api/ops/*` も Bearer stub では 401 だが、静的 JSON があるため「画面が空でない」印象になりやすい

---

## 最終判定

| 仮説 | 判定 |
|------|------|
| AI ダウンが主因 | **否**（未到達。health 上 PI は ok） |
| Pages 静的だけ更新で Functions 古い | **否**（Functions 同梱デプロイ済み） |
| 今回の Ops Console が商品 API を破壊 | **否**（auth/middleware は既存 8.5.1 ポリシー） |
| **本番 Auth 設定不整合（stub 発行 × stub 禁止）** | **主因（確定）** |
| Research Week OPS_CLOSED | **副因（Bearer 無し / USER）— 確定** |
