# System Regression Audit

**Date:** 2026-07-26 (JST)  
**Repo:** `KEIBA-Single-AI` (`main` @ `155e6c7` + working tree)  
**Baseline:** **Version8.5**（`docs/ops/v8-operations-baseline.md` / `scripts/ops/v8/ops-baseline.mjs` `BASELINE_LOCK = "8.5"`）  
**Mode:** 調査のみ（コード修正なし）  
**比較軸:** Version8.5 固定宣言 × 現作業ツリー × 本番プローブ（`expect-keiba.com`）× Version7 / 8.6 / 8.7 意図差分

> **Baseline 定点について:** git tag `v8.5` は存在しない。Version8.5 は **Operations Lock 宣言**（2026-07-26 Effective）として扱い、禁止変更（PE / CE / AI / Production ロジック）と Research 境界を正本とする。HEAD との hash 比較でコア・ドリフトを検証した。

---

# Executive Summary

| 判定 | 結果 |
|------|------|
| **総合** | **WARNING** |
| **Version8.5 Baseline Integrity** | **FAIL**（CE overlay 実ロジック差分） |
| Frontend（Challenge P0） | **PASS**（本番 `/saved` も Challenge UI） |
| Backend API 追加 | **PASS**（削除 0 / 追加のみ） |
| Security（stub JWT / ops gate） | **FAIL** |
| Research 境界 | **PASS**（`production_auto_apply: false`） |
| ResultAutomation | **WARNING**（大規模拡張 + timer 2分） |
| Infra（_redirects / Maintenance） | **PASS**（login ループ対策済み） |
| Git ↔ Deploy 整合 | **WARNING**（重要 JS/API が未追跡のまま Pages 投入） |

**要約:** UI 側の最大回帰（Challenge「今月の成績」）は作業ツリー・本番とも解消。Version8.6 Scheduler / Version8.7 Ops Portal は意図追加として整合。一方 **CE AbilityScores 透過は Version8.5 Hard Lock 違反候補**、stub JWT の role 昇格経路と `/api/ops/conversation` の BFF 管理者ゲート欠如は **Security FAIL**。RA は Production 経路で HEAD から大きく変化（Netkeiba / cadence / settle）。Research → Production コア自動適用は無し。

---

# 1. Frontend Audit

## 1.1 画面マップ

| 画面 | ファイル | 判定 | メモ |
|------|----------|------|------|
| Home | `public/index.html` | **PASS** | `#homeChallengeSlot` + challenge-dashboard |
| Challenge | `public/saved.html` | **PASS** | V7 Challenge DOM（`challengeBanner` 等）。旧 `balance-hero` なし |
| Races / Race | `races.html` / `race.html` | **PASS** | 構造回帰なし（cache/AM 中心） |
| Analysis | `analysis.html` | **PASS** | `?mock=1` ゲートあり |
| Odds | `odds.html` | **PASS** | |
| History | `history.html` | **WARNING** | 未追跡 HTML が本番投入されうる |
| Chat | `chat.html` | **PASS** | |
| MyPage | `mypage.html` | **WARNING** | V8.7 ADMIN メニューは意図。ラベル「今月の成績」残存 |
| Ops | `ops.html` | **WARNING** | V8.7 ポータル構造 PASS。データ多く No Data |
| Login | `login.html` | **PASS** | `data-skip-auto-maintenance` |
| Maintenance | `maintenance.html` | **PASS** | |
| Win5* | `win5.html` 等 | **WARNING** | 準備中コピー + AM 未読込 |

## 1.2 回帰一覧（Frontend）

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| FE-01 | Challenge 旧「今月の成績」UI | P0 | **解消**（DOM + `challenge-dashboard.js` + monthly API） |
| FE-02 | Home Challenge スロット欠落 | P1 | **解消** |
| FE-03 | ナビ「チャレンジ」混在 | P1 | **部分残存**（`mypage.html` / `conversation-ui.js` / onboarding） |
| FE-04 | Login 308 ループ | P0 | **解消**（`_redirects` rewrite 撤去） |
| FE-05 | `/saved` pretty URL の stale HTML | P1 | **緩和**（`_headers` max-age=0）。本番プローブ PASS |
| FE-06 | Ops 固定マーケ文言 | P1 | **緩和**（No Data/Pending）。週次 JSON 未公開で空表示は残る |
| FE-07 | Win5 に auto-maintenance 未接続 | P1 | **未解消** |
| FE-08 | 未使用 JS（`client.js` / adapters / compose / bundle / bindSavedPage） | P2 | **残存** |
| FE-09 | `challenge-dashboard.js` / `ops-portal-v87.js` が git 未追跡 | P1 | **残存**（HEAD 復元で再回帰リスク） |

## 1.3 本番プローブ（2026-07-26）

| URL | 結果 |
|-----|------|
| `/saved` | `challengeBanner=true`, `balance-hero=false`, `challenge-dashboard=true` |
| `/` | `homeChallengeSlot=true` |
| `/ops` | ops-portal あり、`data-skip-auto-maintenance` |
| `/login` | 200、skip AM |
| `/api/system/status` | 200、`maintenance:true`（Research Week 中・仕様） |

## 1.4 Mock / Stub / Dummy

- Mock は `mock-gate.js`（`?mock=1` / `EXPECT_USE_MOCK`）配下が中心 → **意図的**
- Ops クライアントは stub マーケ文字列を **No Data** へ正規化 → **意図的（V8.7 修正後）**
- `win5.html`「準備中」→ **製品スタブ（WARNING）**
- `favorites.js` の deprecated 固定カタログ → **P2**

**Frontend 総合: WARNING**（P0 UI は閉じたがラベル残差・未追跡資産・Win5 AM が残る）

---

# 2. Backend Audit

## 2.1 Endpoint 在庫

| 指標 | 値 |
|------|-----|
| HEAD 追跡 API | 約 32 |
| 作業ツリー | 約 47（**+15 未追跡、削除 0**） |

### 主な追加（意図: V7 周辺 UI / V8.6 / V8.7）

| Endpoint | 系統 |
|----------|------|
| `GET /api/ops/portal` | V8.7 Ops Portal |
| `GET /api/ops/research-scheduler` | V8.6 |
| `GET /api/ops/result-automation` | RA ダッシュボード |
| `GET /api/ops/v71-metrics` | Ops メトリクス |
| `GET /api/system/status` | Maintenance 正本 |
| `GET /api/v1/challenge/monthly` | Challenge |
| `GET /api/v1/results/day-archive` | 結果アーカイブ（**無認証**） |
| `…/user-race-results*` / `user/progress` | ユーザー台帳 |
| `…/races/:id/{data-status,history,official-result}` | Race 詳細拡張 |

**削除 API:** 検出なし。

## 2.2 Middleware / Auth / Maintenance

順序（`functions/_middleware.js`）: `requireAuth` → `resolveAuthorization` → `evaluateOpsAccess`。

| 項目 | 判定 |
|------|------|
| Research Week 自動 CLOSED（日 21:00〜土 00:00 JST） | **PASS**（`v11_auto_maintenance: true`） |
| ADMIN / OPS / DEVELOPER bypass | **PASS**（設計どおり） |
| `system/status` 公開 | **PASS** |
| stub JWT（既定 `AUTH_MODE`） | **FAIL**（下記 Security） |
| Ops API 認可の二重実装 | **WARNING**（portal は厳格、他は `isAdminUser`） |

## 2.3 レスポンス / Schema

- Ops portal: 空は **No Data / Pending**（マーケ固定文言撤去）→ **概ね準拠**
- `research-scheduler.js`: 欠損時に `"毎日 03:00 JST"` 等の固定フォールバック → **No Data 方針 WARNING**
- Challenge monthly: AI プロキシ依存。CLOSED 時は 503 → UI は No Data / メンテ（仕様）

**Backend 総合: WARNING**（在庫・削除なしは健全。認可と scheduler 文言が減点）

---

# 3. AI Audit

## 3.1 Hard Lock 対象（Version8.5）

| コンポーネント | vs HEAD (hash) | 判定 |
|----------------|----------------|------|
| PE `research/pool-entry-v2/v2_pool_entry_v2.py` | **IDENTICAL** | **PASS** |
| CE research `research/ce-v2/v2_ce_v2.py` | **IDENTICAL** | **PASS** |
| Scoring / Confidence / Explain / Prediction adapter | **IDENTICAL**（status `M` でも hash 同一） | **PASS** |
| **本番 CE overlay** `…/candidate_evaluation/__init__.py` | **DIFF**（+87 行級） | **FAIL** |

## 3.2 CE 差分内容（証拠）

`CandidateEvaluationProjector` に:

- `ABILITY_FEATURE_KEYS`（history_score / distance_score 等）
- `runners_frame` 引数
- CE row への **`AbilityScores` 付与**
- `CorePipeline` が `scored_frame` を projector に渡す

Rank / Confidence 算出式そのものは大きく変えていないが、**本番 CE 契約・出力スキーマ変更**であり Version8.5「PE / CE / AI 変更禁止」に抵触する。

## 3.3 Prediction / AI 周辺

- `services/win5-ai/app/main.py` 等に user/challenge/admin ルート拡張（**コア PE 外の製品層**）
- BFF `predictionAdapter` 等は status dirty だがコア PE 非変更方針と別レイヤ

**AI 総合: FAIL**（CE overlay 1 点で Hard Lock 非達成）

---

# 4. Research Audit

## 4.1 `scripts/ops/v8/`（全 21 ファイル・HEAD 比 **未追跡 NEW**）

| 役割 | ファイル例 |
|------|------------|
| Runner / Scheduler | `runner.mjs`, `runner-lib.mjs`, `run-day.mjs`, `calendar.mjs`, `week-id.mjs` |
| Analyzer | `pattern-detect.mjs`, `root-cause-score.mjs`, `analyzer-feedback.mjs` |
| Proposal / Validation | `rank-proposals.mjs`, `proposal-validate.mjs` |
| Canary | `canary-ranked.mjs` |
| 285R Baseline | `baseline-285r.mjs`, `ops-baseline.mjs`（`BASELINE_LOCK="8.5"`） |
| Decision / Knowledge / Governance | `decide.mjs`, `knowledge-base.mjs`, `governance.mjs` |
| Report / Incident | `weekly-report.mjs`, `incident-*.mjs` |

## 4.2 Production 影響

| 書込先 | 評価 |
|--------|------|
| `development/weekly|scheduler|analysis|knowledge/*` | Research 専用 → **OK** |
| `public/ops-data/research-scheduler.json` | 公開静的パス → **境界 WARNING（ソフト）** |
| PE / CE / AI / Production DB への自動 apply | **禁止明示**（`production_auto_apply: false` / deploy-note only） |

V8.6 Runner（`npm run v8:runner` / systemd 03:00 JST）は **意図した Version8.6 追加**。Version8.5 の「Research 新機能追加停止」との関係は、**運用自動化（Scheduler）として文書化済み**でコア非変更。

**Research 総合: PASS**（Production コア自動適用なし。ops-data 書込のみ WARNING）

---

# 5. Production Boundary Audit

```
Research (V8) ──write──► development/* (+ public/ops-data snapshot)
            └──X──► PE / CE / Scoring / Prediction Engine（自動適用禁止）

ResultAutomation (Production) ──► race_results / evaluations / Miss / Archive / user settle
            └──X──► Research weekly pipeline（実行しない）

CE overlay AbilityScores ──► Production CE path  【LOCK RISK】
```

| 境界 | 判定 |
|------|------|
| Research → Production コア | **PASS**（ガード文言・フラグ一致） |
| Production → Research 汚染 | **PASS**（V8 は RA 結果を観測する側） |
| CE Hard Lock | **FAIL** |
| RA Production 挙動拡張 | **WARNING**（意図 V7.3 の可能性、ゲート要） |

---

# 6. Infrastructure Audit

| 項目 | 状態 | 判定 |
|------|------|------|
| Cloudflare Pages | 本番配信中。HTML `max-age=0` 強化 | **PASS** |
| Functions | `_routes.json` include `/*` | **PASS** |
| `_redirects` | rewrite **ゼロ**（login/ops ループ対策コメント明記） | **PASS** |
| `_headers` | `/saved` `/ops` `/login` 等 pretty URL も no-cache | **PASS** |
| systemd V8 scheduler | `expect-v8-research-scheduler.{service,timer}` **未追跡** | **WARNING** |
| RA timer | HEAD: 12:00+21:00 → WT: **`*:0/2:00`（2分）** | **WARNING** |
| package.json | `v8:*` scripts 追加、deps 不変 | **PASS** |
| beta.json | `config/` ≡ `public/config/`（作業ツリー） | **PASS** |
| Docs drift | v8.7 文書が `_redirects /ops→ops.html` 記載のまま | **WARNING** |

**Infra 総合: WARNING**

---

# 7. Database Audit

| 項目 | 状態 |
|------|------|
| Supabase / RLS | **リポジトリ内に検出なし**（SQLite + app 層認可想定） |
| Migrations `001`–`008` | 既存 |
| `009_user_race_results.sql` | **未追跡 NEW**（ユーザー台帳 / P&L） |
| `010_user_progress_audit.sql` | **未追跡 NEW**（progress / purchase audit） |
| PE 独立コメント | あり（ユーザー台帳は PE 非接続方針） |

**Database 総合: WARNING**（スキーマ追加は製品層として妥当だが未追跡・適用手順の文書化不足）

---

# 8. Security Audit

| 項目 | 判定 | 根拠 |
|------|------|------|
| ADMIN allowlist | **PASS**（現行 `admin-20260721`, `admin-smoke`） | `beta.json` |
| USER / OPS CLOSED | **PASS** | middleware |
| Maintenance ADMIN bypass | **PASS**（設計どおり） | |
| JWT / stub token | **FAIL** | 署名なし `stub.*`。profile 欠落時 `source:"token"` で **token.role 採用** → 偽造 ADMIN 昇格しうる |
| `isAdminUser` fail-open | **FAIL** | `admin_user_ids=[]` なら **全ログインユーザー admin**（dashboard / scheduler / RA / v71） |
| `/api/ops/conversation` | **FAIL** | BFF に管理者チェックなし。Bearer 任意転送 |
| Ops Portal | **PASS**（厳格側） | `resolveAuthorization` + `opsPortalAccess` |
| day-archive 無認証 | **WARNING** | PII 無し前提だが脅威モデル未文書化 |

**Security 総合: FAIL**

---

# 9. Runtime Audit

| Unit / Script | 判定 |
|---------------|------|
| `npm run v8:mon`…`v8:fri` / `v8:runner` / `v8:report` / `v8:incident` | **PASS**（意図 V8.5/8.6） |
| `expect-v8-research-scheduler.timer` | **WARNING**（未追跡・EC2 適用状態は本監査外） |
| `expect-result-automation.timer` 2分 tick | **WARNING** |
| ResultAutomation runner + `ra_cadence` | **WARNING**（idle skip 設計はあるが頻度変更は本番影響大） |
| Collect / PI refresh timers | 既存・大きな意図外削除なし |

**Runtime 総合: WARNING**

---

# 10. Feature Flag Audit

| Flag | 値 | 評価 |
|------|-----|------|
| `v11_auto_maintenance` | true | 意図（Research Week） |
| `v2_ops_dashboard` | true | 既存 |
| `v8_research_enabled` | true | Research tooling ゲート |
| `v8_canary_*` / `v8_production_canary` | **false** | PE 非接続 → **PASS** |
| `maintenance_mode` | false | 手動 OFF |
| `ops_mode` | null | スケジュール従属 |

Production Canary 混入: **検出なし（フラグ OFF）**。

**Feature Flag 総合: PASS**

---

# 11. Dependency Audit

| 項目 | 判定 |
|------|------|
| npm dependencies 追加/削除 | **なし（PASS）** |
| `v8:*` scripts | 意図追加 |
| Dead / orphan frontend JS | **WARNING**（§1 FE-08） |
| 偽 dirty（hash identical な `M`） | **WARNING**（監査ノイズ・将来の差分判別阻害） |
| 重複 API 認可ヘルパ | **WARNING**（`isAdminUser` 複製） |

**Dependency 総合: WARNING**

---

# 12. Regression List

## P0

1. **CE Hard Lock 違反:** `services/win5-ai/platform/core-overlay/ai_platform/core/candidate_evaluation/__init__.py` の AbilityScores 透過（承認 or 差し戻し）
2. **Stub JWT role 昇格:** profile 無し時 token.role 採用 + 署名なし stub
3. **`isAdminUser` fail-open:** `admin_user_ids` 空で全ユーザー admin
4. **`GET /api/ops/conversation`:** BFF 管理者ゲート欠如

## P1

5. RA timer **2分 cadence** の本番ゲート（負荷・レート）
6. RA 大規模差分（Netkeiba / user settle / archive）の意図承認・ロールバック手順
7. 未追跡の本番資産コミット（`challenge-dashboard.js`, `ops-portal-v87.js`, `functions/api/ops/*`, `scripts/ops/v8/**`, migrations 009/010）
8. ナビ残差「今月の成績」（mypage / conversation-ui / onboarding）
9. Win5 系の auto-maintenance 未接続
10. research-scheduler 固定フォールバック文言（No Data 方針）
11. MyPage「購入履歴」リンク先の誤り可能性（history vs analysis）
12. Docs の `_redirects /ops` 記述ドリフト（再導入でループ再発）

## P2

13. 死コード掃除（`bindSavedPage`, unused `client.js` / adapters / compose / bundle）
14. favorites の `/api/auth/favorites` vs `/api/v1/favorites` 二重経路
15. `profile.html` = Settings の文書化
16. `public/ops-data` への Research 書込境界レビュー
17. 偽 dirty（CRLF/index ノイズ）の整理
18. Ops Knowledge/Deploy/Reports の週次 publish パイプライン未接続（空表示）

---

# 13. Baseline Integrity

## Version8.5 との差分（分類）

### 意図した変更（Baseline 上に載る拡張として文書と整合）

| 領域 | 内容 |
|------|------|
| V8.5 Ops Mode | Baseline Lock 宣言・週次レポート・`no_improvement` 正常化 |
| V8.6 | Research Scheduler / Runner / systemd / `v8:runner` |
| V8.7 | ADMIN Ops Portal / mypage 運営導線 / portal API |
| UI 修復 | Challenge V7 復元、login ループ修正、Maintenance / system status |
| 製品層 | user-race-results / progress / challenge monthly（PE 非接続方針） |
| Flags | `v8_production_canary=false` 維持 |

### 意図しない / ゲート未承認の可能性が高い変更

| 領域 | 内容 |
|------|------|
| **CE overlay** | AbilityScores（**Hard Lock 違反**） |
| Security 既存欠陥の温存 | stub JWT / fail-open admin（V8.7 API 追加で攻撃面拡大） |
| Git 未追跡のまま本番 | Challenge/Ops JS・多数 API → HEAD 復元で再回帰 |
| ラベル残差 | 「今月の成績」が一部 UI に残存 |
| RA timer | 12/21 時 → 2 分（運用影響大） |

### Version 比較メモ

| Version | 対 Baseline | 回帰か |
|---------|-------------|--------|
| V7 Challenge UI | 復元済み | 以前の「今月の成績」回帰は **閉じた** |
| V8.5 | 正本 | CE 以外のコアは概ね維持 |
| V8.6 | 意図追加 | Research のみ。Production 自動適用なし |
| V8.7 | 意図追加 | Ops 閲覧。旧詳細 Ops 欠落は **意図的置換** |

---

# 14. Conclusion

## Version8.5 Baseline Integrity

| 項目 | 結果 |
|------|------|
| PE 変更なし | **PASS** |
| CE 変更なし | **FAIL**（AbilityScores） |
| AI / Scoring コア hash | **PASS** |
| Research → Production 自動適用なし | **PASS** |
| Production Canary OFF | **PASS** |
| Feature Flag 誤 ON（canary） | **PASS** |
| **Baseline Integrity 総合** | **FAIL** |

## 総合判定

**WARNING**（運用 UI・Research 境界・Challenge 復元は良好。ただし Baseline Integrity は CE により **FAIL**、Security に P0 が残る）

---

# 15. 修正提案一覧（実装は行わない）

1. CE AbilityScores 差分を **承認して ADR 化**するか、**HEAD へ差し戻し**て Hard Lock を回復する  
2. stub JWT: 署名必須化、または profile 必須・token.role 無視  
3. `isAdminUser`: allowlist 空は **fail-closed**（403）  
4. `/api/ops/conversation` に ADMIN ゲート追加  
5. RA timer / Netkeiba 拡張を **明示リリースノート + ロールバック手順**付きでゲート  
6. 未追跡の V8/V8.7/Challenge 資産をコミットし、git = Pages 正本化  
7. 「今月の成績」残ラベルを「チャレンジ」へ統一  
8. Win5 に AM 接続、または意図的除外を文書化  
9. research-scheduler の固定文言を No Data/Pending に統一  
10. `_redirects` 再導入禁止を runbook に固定（docs の誤記修正）  
11. migrations 009/010 の適用手順と PE 非接続保証を文書化  
12. 死コード・二重 favorites・偽 dirty の整理（P2）

---

*本監査は調査のみ。PE / CE / AI / ResultAutomation / Research コアへの修正は実施していない。*
