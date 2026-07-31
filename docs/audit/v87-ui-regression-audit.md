# Version8.7 UI Regression Audit

**Date:** 2026-07-26 (JST)  
**Repo:** `KEIBA-Single-AI`  
**目的:** Version7 / Version8.7 で意図した最新 UI と、現在の作業ツリー／本番（`expect-keiba.com`）の差分洗い出し  
**スコープ:** UI・配線・Ops 閲覧ダッシュボード・Routing。PE / CE / AI / ResultAutomation / Research コアロジックは非変更前提の監査。

---

## 1. Executive Summary

| 判定 | 内容 |
|------|------|
| **P0** | Challenge（`saved.html`）が旧「今月の成績」UI のまま。ナビだけ「チャレンジ」。`challenge-dashboard.js` / API / CSS は未配線。本番も `balanceUI=true`・`challengeJS=false`。 |
| **P0（対応済）** | `/login` の `ERR_TOO_MANY_REDIRECTS`（`_redirects` × pretty URL）。現在本番 `/login` は 200。 |
| **P1** | Ops Dashboard は V8.7 ポータルとして新設済みだが、カード値の大半が **静的スナップショット／固定文字列**。旧 Ops（RA 詳細テーブル・Conversation Metrics 等）は `ops.html` 置換で欠落。 |
| **P1** | UTF-8 破損→`git checkout HEAD` 復旧で **キャッシュバンストとメンテ JS 以外は HEAD 構造に戻った画面が多い**（意図した新 UI が未コミット／未配線なら「古い見た目」が本番に残る）。 |
| **P2** | Home に `#homeChallengeSlot` 未配置。Settings 専用 HTML なし（`profile.html` が相当）。`history.html` / Ops portal JS 等が **git 未追跡**のままデプロイされている。 |

本番プローブ（2026-07-26）: 対象 12 画面とも HTTP 200、`auto-maintenance` v12.4（ops 除く）、UTF-8 `\ufffd` = 0。

---

## 2. 回帰一覧

| ID | 画面 | 症状 | 原因 | 優先度 |
|----|------|------|------|--------|
| R-01 | Challenge / saved | タイトル「今月の成績」、`page-balance` / `balance-hero`。Challenge バナー・AI vs ユーザー比較なし | 新 UI（`challenge-dashboard.js`）が HTML 未配線。ナビラベルのみ先行変更 | **P0** |
| R-02 | Home | Challenge ホーム枠なし。固定ナビ文言が「今月の成績」系のまま混在しうる | `#homeChallengeSlot` 未追加、`challenge-dashboard.js` 未読込 | **P1** |
| R-03 | Nav | `partials-nav.js` は「チャレンジ」、`shell.js` / 一部 index は旧表記 | ラベル統一未完了 | **P1** |
| R-04 | Ops | 旧詳細 Ops（RA stages 表・V7.3 grids・Conversation）が消失 | V8.7 で `ops.html` をポータル UI に置換（-622/+71 vs HEAD） | **P1**（意図的置換か要確認） |
| R-05 | Ops cards | Knowledge / Deploy / Reports / 大半 Production がプレースホルダ | `portal-snapshot.json` + portal.js 固定 fallback。週次成果物未公開 | **P1** |
| R-06 | Login | （過去）無限 308 | `_redirects` の `/login → login.html 200` × CF pretty URL | **P0 修正済** |
| R-07 | 複数 HTML | HEAD 復元後、構造は旧のまま cache bust / AM のみ新 | UTF-8 破損対応で `git checkout HEAD` | **P1**（プロセスリスク） |
| R-08 | history / win5* | 未追跡 HTML を本番投入 | 作業ツリーのみ | **P2** |
| R-09 | Settings | `settings.html` なし | 設計上 `profile.html` | **P2**（ドキュメント化で可） |
| R-10 | Ops 認可 | （過去）ADMIN でも拒否 | `Auth.me` の `user.role` 未 unwrap + `role==="ADMIN"` 固定 | **P0 修正済**（`roles.js`） |

---

## 3. 画面別ステータス（意図 vs 現状）

### 3.1 Home（`index.html`）
- **意図 (V7/V8):** 開催一覧・本命カード・（V7）Challenge スロット。
- **現状:** HEAD 差分は主に AM/CSS キャッシュ。本番 `challengeJS=false`。
- **API:** Prediction list / Supply / User.history / Stats heatmap（`ExpectApi`）。
- **固定値:** AI 説明カード等のマーケ文言（HTML 固定）。`app.js` + sample bundle 経路あり（モックゲート外でも注意）。

### 3.2 Races（`races.html`）
- **現状:** 構造は HEAD 系 + cache/AM。大きな UI 回帰は検出せず。
- **API:** `/api/races`, `/api/race-cards`, predictions。

### 3.3 Analysis（`analysis.html`）
- **現状:** UTF-8 復旧後タイトル正常。レイアウトは Bottom Nav flex 修正済。
- **API:** Prediction + Analysis。失敗時 `?mock=1` で mocks。

### 3.4 Challenge / saved（`saved.html`）— **最大回帰**
- **意図 (V7):** `#challengeBanner`, `#aiScoreCard`, `#userScoreCard`, `#profitCompareBars`, `#weekCompareBars`, `challenge-dashboard.js`, `GET /api/v1/challenge/monthly`。
- **現状:**
  - title: 「今月の成績」
  - `page-balance` / `balance-hero` / stats-grid / 閲覧履歴
  - bind: `User.history` + `Supply.coverage` → `bindSavedPage`
  - **未ロード:** `challenge-dashboard.js`
  - CSS に Challenge 用スタイルは追加済だが HTML 未使用
  - BFF `functions/api/v1/challenge/` と `user.js#challengeMonthly` は未追跡／未配線のまま存在
- **本番:** `balanceUI=true`, `challengeJS=false`

### 3.5 MyPage（`mypage.html`）
- **現状:** V8.7 ADMIN 運営メニュー追加（意図どおり差分大）。
- **API:** `/api/users/me`, invites, supply。ADMIN ポータルは `ExpectRoles`。

### 3.6 Ops Dashboard（`ops.html`）
- **意図 (V8.7):** 閲覧専用 6 セクション。ADMIN のみ。
- **現状:** 新ポータル UI 本番稼働（`ops-portal-v87.js`）。旧フル Ops は欠落。
- **詳細カード分類:** §4。

### 3.7 Login / Maintenance
- **Login:** 200・UTF-8 正常・`data-skip-auto-maintenance`。認証ゲート対象外。
- **Maintenance:** 静的案内 + AM。200。

### 3.8 History（`history.html`）
- **現状:** 未追跡だが本番 200。購入履歴 + `user-race-results`。
- **リスク:** リポジトリ正本と本番のドリフト。

### 3.9 Odds / Chat / Profile（Settings）
- **Odds / Chat:** 大きな構造回帰なし（cache/AM）。Chat は Conversation/Kaoba API。
- **Profile:** settings 相当。`/api/users/me` PATCH。

---

## 4. Ops Dashboard カード分類

**データ経路**

1. `GET /api/ops/portal` … `portal-snapshot.json` + `research-scheduler.json` + Maintenance 計算  
2. クライアント `mergeLiveHints` …  
   - `GET /api/ops/research-scheduler`  
   - `GET /api/ops/result-automation`  
   - `GET /api/ops/v71-metrics`  

`research-scheduler.json` は現状ほぼ空 `{}` → Research 系は snap / 固定 fallback に寄りやすい。

### 4.1 System

| カード | 分類 | 利用 API | 取得 JSON の出所 | 失敗時表示 | 固定文字列 |
|--------|------|----------|------------------|------------|------------|
| Pages | 静的スナップショット | `/api/ops/portal` | `portal-snapshot.system.pages` | （portal 全体失敗時）アクセス不可 / 取得失敗 | fallback `"Cloudflare Pages"` |
| EC2 | 静的 | 同上 | `system.ec2` | 同上 | `"AI/PI host"` |
| PI | 静的 | 同上 | `system.pi` | 同上 | `"proxy"` |
| AI | 静的 | 同上 | `system.ai` | 同上 | `"proxy"` |
| ResultAutomation | **Live 上書き** + 初期静的 | portal + `/api/ops/result-automation` | `run.status` / `status` | live 失敗時は snapshot / `"read-only status"` | note: API パス文言 |
| Research Scheduler | **Live 上書き** + 静的 | portal + `/api/ops/research-scheduler` | `current_phase` 等 | snapshot `"03:00 JST"` | — |

### 4.2 Production

| カード | 分類 | 利用 API | 取得 JSON | 失敗時 | 固定 |
|--------|------|----------|-----------|--------|------|
| Prediction | 静的（任意 v71 上書き） | portal; 任意 `/api/ops/v71-metrics` | snap `read-only` | `"live"` fallback（portal.js） | `"read-only"` in snap |
| Board | 同上 | 同上 | 同上 | 同上 | 同上 |
| History | 同上 | 同上 | 同上 | 同上 | 同上 |
| Challenge | 同上 | 同上 | 同上 | 同上 | 同上 |
| Archive | 同上 | 同上 | 同上 | 同上 | 同上 |
| Realtime | 同上 | 同上 | 同上 | 同上 | 同上 |
| Maintenance | **サーバ Live** | `/api/ops/portal` 内 `resolveOpsModeDetailed` | `CLOSED` / `PUBLIC` | portal 失敗時セクション非表示 | note: 閲覧専用バナー |

### 4.3 Research

| カード | 分類 | 利用 API | JSON | 失敗時 | 固定 |
|--------|------|----------|------|--------|------|
| Current Week | Live 上書き可 | portal + research-scheduler | `week_id` | `"—"` | — |
| Current Phase | Live 上書き可 | 同上 | `current_phase` | `"—"` | — |
| Next Run | Live 上書き可 | 同上 | `next_run` | `"毎日 03:00 JST"` | 同上 |
| Recovery | Live 上書き可 | 同上 | `recovery` → active/idle | `idle` | — |
| Decision | **静的のみ** | portal のみ | `snap.research.decision` | `"—"` | note: `no_improvement = success` |

### 4.4 Knowledge

| カード | 分類 | API | JSON | 失敗時 | 固定 |
|--------|------|-----|------|--------|------|
| Knowledge Score | 静的 | portal | snap `"—"` | `"—"` | `"—"` |
| Accepted Patterns | 静的 | portal | `"—"` | `"—"` | `"—"` |
| Rejected Patterns | 静的 | portal | `"—"` | `"—"` | `"—"` |
| Governance | 静的 | portal | `"read-only"` | `"read-only"` | `"read-only"` |

### 4.5 Deploy

| カード | 分類 | API | JSON | 失敗時 | 固定 |
|--------|------|-----|------|--------|------|
| Deploy Queue | 静的 | portal | `"empty"` | `"empty"` | `"empty"` |
| Accept済み候補 | 静的 | portal | `"0"` | `"0"` | `"0"` |
| deploy-note | 静的 + scheduler 文言 | portal | `deploy_note_only` | 同左 | note: Production 自動適用禁止 |

### 4.6 Reports

| カード | 分類 | API | JSON | 失敗時 | 固定 |
|--------|------|-----|------|--------|------|
| Weekly Report | 静的 | portal | `pending publish` | 同左 | 同左 |
| Baseline Health Check | 静的 | portal | `pending publish` | 同左 | 同左 |
| Boundary Audit | 静的 | portal | `pending publish` | 同左 | 同左 |
| Incident Report | 静的 | portal | `none` | 同左 | `none` |

**UI 固定バナー（カード外）:** 「閲覧専用ダッシュボード — Production への書き込み・自動適用は行いません。」

---

## 5. 固定値 / MOCK / stub ホットスポット

| 場所 | 種別 | 備考 |
|------|------|------|
| `public/ops-data/portal-snapshot.json` | 静的プレースホルダ | Ops カード値の主ソース |
| `functions/api/ops/portal.js` | fallback 文字列 | `"—"`, `"live"`, `"pending"` 等 |
| `public/assets/ops-portal-v87.js` | ゲート文言 | ADMIN のみ / ログイン必要 |
| `public/assets/api/mock-gate.js` | モック許可 | `?mock=1` / `EXPECT_USE_MOCK` |
| `public/assets/api/{prediction,analysis,kaoba,client}.js` | mock fallback | `data/mocks/*` |
| `public/data/sample_data.js` / `app.js` | sample bundle | Home 経路に注意 |
| `public/index.html` | 固定マーケ文言 | 「モック準拠」コメント残存 |
| `public/maintenance.html` | 固定案内 | メンテ説明 |
| `public/saved.html` | 旧 balance 固定コピー | 「的中・収支 API は未提供…」系 |
| `stub.` JWT | 認証スタブ | `roles.js` / `auto-maintenance.js` がパース |

`innerHTML` の大半は動的描画。問題は **Ops プレースホルダを live と誤認すること** と **Challenge DOM 欠落**。

---

## 6. 本番クライアントが呼ぶ `/api` 一覧（ユニーク）

```
/api/admin/invitations
/api/analysis/:id
/api/auth/favorites
/api/auth/invite/start
/api/auth/login
/api/auth/logout
/api/auth/me
/api/auth/setup
/api/confidence/:id
/api/conversation/chat
/api/data/coverage
/api/diagnostics/fallback-reasons
/api/diagnostics/missing
/api/health
/api/kaoba/chat
/api/ops/portal
/api/ops/public-status
/api/ops/research-scheduler
/api/ops/result-automation
/api/ops/v71-metrics
/api/predictions
/api/predictions/:id
/api/race-cards
/api/races
/api/races/:id/board
/api/races/:id/data-status
/api/races/:id/history
/api/races/:id/odds-series
/api/system/status
/api/tickets/:id
/api/users/me
/api/v1/challenge/monthly
/api/v1/chat
/api/v1/favorites
/api/v1/history
/api/v1/results/day-archive
/api/v1/stats/heatmap
/api/v1/stats/summary
/api/v1/user-race-results
/api/v1/user-race-results/:id
/api/v1/user-race-results/:id/settle
/api/v1/user-race-results/settle-pending
/api/v1/user/progress
```

**画面 → 主要 API（要約）**

| 画面 | fetch / ExpectApi |
|------|-------------------|
| Home | predictions, coverage, history, heatmap |
| Races | races, race-cards, predictions |
| Analysis | predictions/:id, analysis/:id |
| Challenge(saved) | **現状** history, coverage（challenge/monthly **未使用**） |
| MyPage | users/me, invitations, coverage |
| Ops | ops/portal, research-scheduler, result-automation, v71-metrics |
| Login | auth/login, auth/invite/start |
| Maintenance | system/status, ops/public-status（AM） |
| History | user-race-results?view=history, day-archive |
| Odds | races, odds-series, board |
| Chat | conversation/chat, kaoba/chat |
| Profile | users/me |

非 API: `/config/beta.json`（features / admin_user_ids）。

---

## 7. Version7 との差分・欠落

| V7 要素 | 状態 |
|---------|------|
| Challenge ダッシュボード UI | **欠落（DOM 未配線）** — JS/CSS/API は半実装 |
| Home Challenge スロット | **欠落** |
| Maintenance Mode（Research Week） | **あり**（system/status + AM v12.4） |
| ResultAutomation Ops 詳細 | **旧 ops.html ではあり → V8.7 ポータルではカード要約のみ** |
| Conversation Ops Metrics | **旧 ops 依存 → 現行ポータルに無し** |
| Bottom nav「チャレンジ」 | ラベルのみ先行 |

Version8.7 で **新規追加されたもの（回帰ではない）:**
- ADMIN 運営メニュー（mypage）
- Operations Portal（`/ops` 6 セクション、閲覧専用）
- `ExpectRoles` / login redirect hotfix

---

## 8. Git / HEAD 復元の影響

| ファイル | vs HEAD | 解釈 |
|----------|---------|------|
| 大半の `*.html` | 数行（AM/CSS バージョン） | UTF-8 復旧で構造は HEAD＝旧バランス UI のまま |
| `mypage.html` | +43/-6 | V8.7 運営メニュー |
| `ops.html` | +71/-622 | 旧 Ops 全置換 |
| `challenge-dashboard.js` | **UNTRACKED** | 新 UI が git 正本に未取り込み |
| `ops-portal-v87.js` / `history.html` | **UNTRACKED** | 本番デプロイと git の乖離リスク |
| `partials-nav.js` | ラベル「チャレンジ」のみ | |

**原因パターン:** PowerShell 等による UTF-8 破損 → `git checkout HEAD` → **古いが健全な HTML** が戻り、未コミットの新 UI 配線が消える／最初から無かった。

---

## 9. 修正優先度（推奨アクション）

### P0
1. **Challenge UI 配線:** `saved.html` を `challenge-dashboard.js` 期待 DOM に差し替え、スクリプト読込、`/api/v1/challenge/monthly` 接続。  
2. ナビ／shell／index の「チャレンジ」表記統一。  
3. （済）Login redirect / ADMIN role unwrap。

### P1
4. Ops: 週次成果物を `portal-snapshot` または専用 JSON に publish し、Knowledge/Deploy/Reports を実データ化。  
5. 旧 Ops 詳細（RA stages 等）が必要ならポータル内の「詳細」折りたたみとして復元方針を決定。  
6. 未追跡の本番投入ファイルを git に追加し、デプロイ＝コミットを一致させる。  
7. UTF-8 編集ルール（Python 書込 / PowerShell Set-Content 禁止）を運用固定。

### P2
8. Home `#homeChallengeSlot`。  
9. `settings` 別名 or docs で profile を正式 settings とする。  
10. index の sample/`モック準拠` コメント掃除。

---

## 10. API 接続状況（サマリ）

| 領域 | 接続 | 備考 |
|------|------|------|
| レース / 予想 / 分析 / オッズ | Live BFF | 本番経路 |
| Challenge monthly | API・クライアントあり、**UI 未接続** | P0 |
| Ops portal | Live だが **値は大半静的** | P1 |
| Ops RA / Scheduler / v71 | Live 補助 | Scheduler JSON 空に注意 |
| Auth / Maintenance status | Live | Login/AM 修正済 |
| Mock | `?mock=1` 時のみ | 本番既定オフ想定 |

---

## 11. スタブ一覧（Ops + UI）

| スタブ / 固定 | 用途 |
|---------------|------|
| `portal-snapshot.json` 全フィールド | Ops カード既定値 |
| portal.js `"—"`, `"pending publish"`, `"empty"`, `"0"`, `"read-only"` | fallback |
| Maintenance / Login 案内文 | 静的コピー |
| `stub.` access token | 認証モード |
| `data/mocks/*`, sample bundle | 開発・`?mock=1` |
| saved「収支 API 未提供」 | 旧 balance UI コピー |

---

## 12. 参照

- `public/saved.html`, `public/assets/api/challenge-dashboard.js`, `public/assets/partials-nav.js`
- `public/ops.html`, `public/assets/ops-portal-v87.js`, `functions/api/ops/portal.js`
- `public/ops-data/portal-snapshot.json`
- `docs/ops/v87-login-redirect-loop-hotfix.md`
- `docs/ops/v8.7-admin-ops-portal.md`

---

*本監査は読取・本番プローブに基づく。コード修正は含まない（P0 Challenge 配線は別タスク推奨）。*
