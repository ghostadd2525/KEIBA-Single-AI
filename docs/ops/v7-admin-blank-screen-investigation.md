# ADMIN 真っ白画面 — 調査報告（2026-07-26）

## 結論（真っ白画面の原因）

**主因: 本番 `index.html` の UTF-8 破損**

- `<title>…/title>` のように `</title>` の `<` が欠落
- 置換文字多数 → HTML/後続スクリプトが壊れて **白紙表示**
- ADMIN / USER 共通で発生しうる（Maintenance 画面以前の問題）

**副因: `/api/system/status` が未デプロイ**

- 本番レスポンス: `Content-Type: text/html`（= SPA の `index.html` フォールバック）
- HTTP 200 だが JSON ではない

---

## Network 結果（本番 expect-keiba.com）

| URL | HTTP | Content-Type | 内容 |
|-----|------|--------------|------|
| `GET /api/system/status` | **200** | **text/html** | index.html（API 未配線） |
| `GET /api/ops/public-status` | **200** | application/json | OK（旧 calendar / `ops_mode:PUBLIC`） |
| `GET /api/health` | **200** | application/json | OK（degraded あり） |
| `GET /api/auth/me`（無トークン） | **200** | **text/html** | HTML フォールバック疑い |

---

## Console エラー（推定）

本番 HTML 破損により典型的に:

1. HTML パース異常（未閉じ title / 壊れた属性）
2. 後続 inline / 外部 JS の SyntaxError または早期中断
3. 画面描画前にスクリプト停止 → **真っ白**

※ `/api/system/status` が HTML でも、クライアントが JSON パース失敗→ public-status フォールバックすればゲート自体は継続可能。**白紙の直接原因は index.html 破損**。

---

## 初期化フロー（修正後）

```
index.html
  → auth.js (requireAuth)
  → auto-maintenance.js run()
       1) loadAutoFlag (v11_auto_maintenance)
       2) 【先に】isOpsBypassUser()  ← ADMIN / allowlist / me.role
       3) ADMIN なら: status 取得のみ・applyGate スキップ・forceClear 禁止
       4) USER なら: fetchStatus → applyGate
            - maintenance → forceLogout → /login
            - 未認証 → maintenance.html
```

処理順の保証: **ADMIN 判定 →（その後のみ）USER 向けメンテ処理**

---

## ADMIN 確認項目への回答

| # | 質問 | 結果 |
|---|------|------|
| 1 | ADMIN 初期化フロー | 上記。修正後は bypass を status ゲートより先に実行 |
| 2 | ADMIN で forceClearAuthState? | **修正前:** bypass 後は呼ばない設計だったが、判定遅延・HTML破損が主問題。**修正後:** bypass 時は `runOnce` が applyGate 自体を呼ばず、`forceLogoutToLogin` も `__EXPECT_MAINT_BYPASS` で拒否 |
| 3 | ADMIN 後メンテ完全スキップ? | **修正後: YES** |
| 4 | status と ADMIN 判定順 | **修正後: ADMIN 先 → status**。status は JSON Content-Type 必須（HTML なら public-status へ） |
| 5 | Console 原因 | **破損 index.html** |
| 6 | Network | 上表 |

---

## 修正内容

1. `public/index.html` — HEAD の正常 UTF-8 から復元 + `auto-maintenance.js?v=12.2`
2. `public/assets/auto-maintenance.js` v12.2
   - ADMIN 判定を最優先しメンテ処理スキップ
   - `forceClearAuthState` を ADMIN で呼ばない
   - `/api/system/status` が HTML のとき JSON とみなさない
3. デプロイ必須: `index.html` + `auto-maintenance.js` +（推奨）`functions/api/system/status.js`

---

## デプロイ後の確認手順

1. ハードリロードで `index.html` / `auto-maintenance.js?v=12.2` を取得
2. ADMIN ログイン → ホームが表示（真っ白でない）
3. DevTools Network: `/api/system/status` が JSON、または public-status にフォールバック
4. Console に SyntaxError がないこと
5. JWT / localStorage が ADMIN セッションで消えないこと
