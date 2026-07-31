# Version8.7 UI Regression — 修正報告

**Date:** 2026-07-26  
**Scope:** P0 → P1 → P2（UI / API 接続のみ。PE / CE / AI / RA / Research ロジック非変更）

---

## 1. 修正一覧

### P0 — Challenge（saved）
| 項目 | 修正内容 |
|------|----------|
| 旧「今月の成績」廃止 | `saved.html` を Challenge ダッシュボード DOM に置換 |
| `challenge-dashboard.js` 接続 | スクリプト読込 + `bindDashboard(document)` |
| monthly API 接続 | `ExpectApi.User.challengeMonthly` → `GET /api/v1/challenge/monthly` |
| V7 UI | バナー / AI・ユーザー成績 / 収支比較 / 週次 / 月間購入リスト / 月切替 |
| ランキング | `#challengeProgress` に `progress`（レベル・ポイント・ランク）を表示。無ければ `No Data` |
| Home | `#homeChallengeSlot` + `bindHomeChallenge` |
| ナビ統一 | partials-nav / shell / index を「チャレンジ」、`data-nav="challenge"` |

### P1 — Ops Dashboard
| 項目 | 修正内容 |
|------|----------|
| 固定マーケ文言廃止 | `"Cloudflare Pages"` / `"live"` / `"read-only"` / `"pending publish"` 等を撤去 |
| 空ポリシー | 未生成は **`No Data`** または **`Pending`** |
| 実データ | Maintenance（ops-mode）、Pages=OK（応答自体）、health / scheduler / client live（RA・v71） |
| snapshot | `portal-snapshot.json` を空スキーマ化（偽値なし） |
| クライアント | stub 値を表示時に `No Data` へ正規化。v71/RA 未取得時は `No Data` |

### P2
| 項目 | 修正内容 |
|------|----------|
| ナビ表記差分 | 「今月成績」→「チャレンジ」に統一 |
| CSS | Challenge / progress / page-challenge 余白 |
| Audit 追記 | 本ファイル |

---

## 2. 変更ファイル一覧

| ファイル | 変更 |
|----------|------|
| `public/saved.html` | Challenge UI 全面置換 |
| `public/assets/api/challenge-dashboard.js` | progress/ranking 描画、失敗時 No Data |
| `public/index.html` | homeChallengeSlot、ナビ、challenge-dashboard 読込 |
| `public/assets/partials-nav.js` | data-nav=challenge |
| `public/assets/shell.js` | label チャレンジ |
| `public/assets/screens.css` | challenge-progress / page-challenge |
| `functions/api/ops/portal.js` | 実データ + No Data/Pending |
| `public/ops-data/portal-snapshot.json` | 空スキーマ |
| `public/assets/ops-portal-v87.js` | stub 正規化、v71/RA 失敗時 No Data |
| `public/ops.html` | JS cache bump |
| `docs/audit/v87-ui-regression-fixes.md` | 本報告 |
| `public/_headers` | `/saved` 等 pretty URL に `max-age=0`（拡張子なし HTML の stale 配信対策） |

---

## 3. 修正前後の画面比較

| 画面 | Before | After |
|------|--------|-------|
| **saved / Challenge** | 「今月の成績」・balance-hero・閲覧履歴・収支 API 未提供コピー | 「チャレンジ」・AIチャレンジバナー・AI/あなた成績・収支棒・週次・進捗/ランキング・月間購入リスト・月切替 |
| **Home** | Challenge 枠なし、ナビ「今月成績」 | `#homeChallengeSlot` + monthly API、ナビ「チャレンジ」 |
| **Ops** | snapshot 固定値（Cloudflare Pages / read-only / pending publish…） | Live 可能な項目は API、それ以外 No Data / Pending |
| **Nav** | 表記混在 | 「チャレンジ」に統一 |

---

## 4. 残課題（API 未実装・データ未生成）

| 項目 | 状態 |
|------|------|
| Challenge monthly | BFF は AI プロキシ依存。AI 未設定時は 502 → UI は No Data |
| Ops Knowledge / Deploy / Reports | 週次成果物 JSON の publish パイプライン未接続 → No Data / Pending |
| Ops Decision | snapshot 空 → No Data（Research Decision API 未配線） |
| Ops EC2/PI/AI | `/api/health` に詳細が無い場合 No Data |
| Ops Production 各サービス | v71-metrics が取れない環境では No Data |
| グローバル順位ランキング | progress に rank が無い場合 UI は No Data（別 API 未実装） |
| 旧 Ops 詳細（RA stages 表・Conversation Metrics） | V8.7 ポータル方針により非表示のまま（必要なら別タスク） |

---

## 5. 検証ポイント

1. ADMIN: `/saved` でチャレンジ UI、Network に `/api/v1/challenge/monthly`  
2. Home: Challenge スロット表示（API 成功時）  
3. ADMIN: `/ops` カードが固定マーケ文言ではなく No Data / Pending / 実値  
4. ナビ全画面で「チャレンジ」表記  

**本番プローブ（2026-07-26 再デプロイ後）:**  
`/saved`・`/saved.html` とも `challengeBanner` + `challenge-dashboard` あり、`balance-hero` なし。`/` に `homeChallengeSlot`。`/ops` に ops-portal。  
※ Research Week 中は API が `OPS_CLOSED`（503）となり UI は No Data / メンテ表示になるのは仕様。

*PE / CE / AI / ResultAutomation / Research コアは未変更。*
