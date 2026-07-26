# Version 8.5.1 Baseline Certification

**Date:** 2026-07-26 (JST)  
**Repo:** `KEIBA-Single-AI`  
**Source audit:** [`docs/audit/system-regression-audit.md`](./system-regression-audit.md)  
**Scope:** 同監査で **FAIL** となった項目のみ  
**Mode:** Certification のみ（**コード修正なし**）

---

## Certification Summary

| ID | Issue | 意図判定 | 推奨判断 | 修正要否 |
|----|-------|----------|----------|----------|
| **CE-01** | AbilityScores overlay（CE） | **意図した製品変更**（git 未コミット・Hard Lock 外） | **条件付き正式採用**（8.5.1 Exception） | **要**（git 正本化 + ADR。差し戻しは非推奨） |
| **SEC-01** | stub JWT role escalation | **意図した OPS-1A 設計** + **意図しない昇格穴** | **脆弱経路は正式採用しない** | **要**（セキュリティ修正） |
| **SEC-02** | `isAdminUser` fail-open | **意図したブートストラップ** | **fail-open は正式採用しない** | **要**（fail-closed 化） |
| **SEC-03** | `/api/ops/conversation` 無認可 | **意図した API 追加** + **意図しないゲート欠落** | **無認可は正式採用しない** | **要**（ADMIN ゲート） |

| 項目 | 結果 |
|------|------|
| **Version8.5.1 Certification** | **CONDITIONAL（保留）** |
| 条件 | Security P0 3件の修正完了後に **PASS** へ昇格可能。CE-01 は Exception 文書化＋コミット後に Baseline へ編入可 |

---

## 調査方法

1. `git blame` / `git log` / `git show` で導入コミットを特定  
2. HEAD コミット済み内容と作業ツリー（`Not Committed Yet`）を分離  
3. 設計文書（OPS-1A / runbook / operations-runbook）と照合  
4. AbilityScores については agent transcript（能力特徴量 UI 要求〜EC2 反映）も証拠として参照  

**Baseline 定点:** Version8.5 Operations Lock（`docs/ops/v8-operations-baseline.md`）。git tag `v8.5` は無し。コミット済み HEAD の CE / Auth を「ロック時点の正本」とみなす。

---

# 1. CE-01 — AbilityScores overlay

## Issue

`services/win5-ai/platform/core-overlay/ai_platform/core/candidate_evaluation/__init__.py` に  
`ABILITY_FEATURE_KEYS` / `runners_frame` / CE row の **`AbilityScores`** 付与が追加されている。  
system-regression-audit では Version8.5 Hard Lock（CE 変更禁止）違反として **FAIL**。

## 意図判定（Git + 経緯）

| 観点 | 結果 |
|------|------|
| **Git 履歴** | AbilityScores 行はすべて **`Not Committed Yet`**。最終コミット済み版は `2e087fa` / `03e7a4f` の Rank/Confidence 投影のみ |
| **コミットメッセージ** | AbilityScores を説明する commit **なし** |
| **ADR / Research Proposal** | **なし**（285R / Canary 経路外） |
| **製品経緯** | ユーザー要求「評価内訳を自信度ではなく馬の能力特徴量％へ」に対し、同一セッションで CE 透過 → BFF `piPredictionMapper` → UI `analysis-bind` → **EC2 へ scp 反映**まで実施（会話ログ証拠） |
| **関連 WT 差分** | `functions/_lib/piPredictionMapper.js` の AbilityScores 読取も **未コミット**。一方 `analysis-bind.js` の `chartsFromAbilityScores` / `ability_scores` 消費は **HEAD に既に存在** |

**判定:**  
- 製品意図としては **意図した変更**  
- Version8.5 Baseline / git 正本の観点では **ロック外・未認定のドリフト**（「意図しない Hard Lock 違反」）

## 原因

1. UI（評価内訳）のために特徴量を CE 行へ載せる実装を選択した  
2. Rank / Confidence 計算式は維持し「透過」に留めたが、**CE 出力スキーマ変更 = Hard Lock 上の CE 変更**  
3. git に入れず EC2 へ直接同期したため、**リポジトリ Baseline と実行系が乖離**

## 影響範囲

| 層 | 影響 |
|----|------|
| PE / Purchase | **なし**（購入ロジック非変更） |
| Rank / Confidence 算出 | **変更なし**（投影時の付帯フィールド追加） |
| CE 契約 / Downstream | CE JSON に `AbilityScores` が増える |
| BFF / Web | `ability_scores` → 評価内訳バー（能力％） |
| Research / 285R | 未経由 |
| 本番 EC2 | 会話ログ上、既に AbilityScores 付き overlay を配置済みの可能性が高い |

## 修正要否

**要（プロセス）。ロジック差し戻しは非推奨。**

必須アクション（実装は本 Certification 外）:

1. ADR（例: `docs/adr/…-abilityscores-passthrough.md`）で「透過のみ・Rank/Confidence 非変更」を宣言  
2. CE + BFF mapper を git にコミットし、EC2 と一致させる  
3. Version8.5.1 Baseline Health Check に **Certified Exception: CE schema passthrough** を追記  
4. コメントの UTF-8 破損を修復  

## 推奨判断

### **条件付き正式採用（Version 8.5.1 Certified Exception）**

**戻さない理由**

- ユーザー要求に基づく意図変更であり、本番 UX（評価内訳）が依存  
- スコアリング／PE 非変更の透過に限定されている  
- HEAD へ CE だけ戻すと、EC2 または UI と不整合になり **意図した UX 回帰**になる  

**正式採用の条件（すべて必須）**

- [ ] ADR 承認  
- [ ] git 正本化（未コミット解消）  
- [ ] 「CE ロジック変更」ではなく **schema passthrough exception** と明記  
- [ ] Hard Lock 文言を 8.5.1 で「評価用特徴量の透過付帯は Exception 可」と更新するか、Exception リストで管理  

**却下して戻す場合の条件（非推奨）**

- Hard Lock を一字一句厳格維持し、能力％は CE を触らず別経路のみで供給する再設計を行う場合のみ。

---

# 2. SEC-01 — stub JWT role escalation

## Issue

署名なし `stub.<payload>.<exp>` トークンに `role` を埋め込め、`users.json` / KV に profile が無い `sub` のとき `resolveAuthorization` が **`source: "token"`** でその role を採用し、ADMIN bypass / portal / invitations に到達しうる。

## 意図判定（Git）

| 証拠 | 内容 |
|------|------|
| `c5af306` (2026-07-20) | `authorization.js` **新規追加**。`else if (session.role) { source = "token" }` |
| `docs/ops/ops-1a-admin-bypass.md` | ロール付与優先順位: (1) users.json (2) **トークン内 role（stub、任意）** (3) admin_user_ids |
| `functions/_lib/auth.js` | コメント: role は optional（OPS-1A）。**正本は users.json / allowlist** |
| `operations-runbook` / release notes | `AUTH_MODE=stub` を現行として明記 |

**判定:**

- トークン role フォールバック自体は **意図した OPS-1A 設計**（Version8.5 以前から Baseline に含まれる）  
- 署名なし stub と profile 欠落を組み合わせた **任意 ADMIN 昇格**は設計が想定する運用（正本 = users.json）を外れた **意図しない攻撃面**

## 原因

1. Beta 認証を stub のまま本番相当で運用（文書化された現行）  
2. OPS-1A が「正本は profile / allowlist」としつつ token.role を第2優先に残した  
3. profile 欠落時に token.role へフォールバックするため、未知 `sub` + 偽造 role が通る  

## 影響範囲

| 対象 | 影響 |
|------|------|
| OPS CLOSED bypass | 偽造 ADMIN で通過しうる |
| `/api/ops/portal` / invitations | 昇格後に到達しうる |
| Prediction / PE / CE / RA | 直接は非対象（認可層） |
| 現行運用緩和 | 招待制 + 既知 user_id 前提だが、**未知 sub 偽造は残る** |

## 修正要否

**要（セキュリティ修正）。**  
OPS-1A の「ADMIN bypass」設計そのものを Version8.5 から取り除く必要はない。

推奨修正方針（実装は別タスク）:

- profile / allowlist に無いユーザーは **常に USER**（token.role 無視）、または  
- stub でも HMAC 等で改ざん検知、または  
- 本番 `AUTH_MODE` を署名付きへ移行  

## 推奨判断

### **脆弱な昇格経路は正式採用しない / 戻す対象は「欠陥」のみ**

- Version8.5 時点の **既知設計負債**（8.5 以降の新規回帰ではない）  
- 8.5.1 では **欠陥を残したまま Certified PASS にしない**  
- 「token.role を正本にする」運用は **不採用**（文書どおり正本は users.json / allowlist）

---

# 3. SEC-02 — `isAdminUser` fail-open

## Issue

複数 Ops API の `isAdminUser` が `admin_user_ids` **空配列なら `return true`**（全ログインユーザーを admin 扱い）。

該当例: `functions/api/ops/dashboard.js`（および同パターンの research-scheduler / result-automation / v71-metrics）。

## 意図判定（Git）

| 証拠 | 内容 |
|------|------|
| `03e7a4f` (2026-07-22) | Version 2 production parity で `if (!ids.length) return true` 導入 |
| ファイルヘッダコメント | 「**admin_user_ids 設定時は**管理者のみ」→ 未設定時オープンを示唆 |
| HEAD `config/beta.json` | `admin_user_ids: ["admin-20260721","admin-smoke"]` あり → **現行は緩和状態** |

**判定:**

- allowlist 未設定時の開放は **意図した初期ブートストラップ**  
- 本番 Beta で allowlist 必須運用にした後も fail-open が残っているのは **意図しない残余リスク**（設定消し込み事故で全開放）

## 原因

Version 2 Ops ダッシュボード導入時の「未設定 = 開発容易性」優先。その後 allowlist 運用に移行したが、コードのデフォルトは fail-open のまま。

## 影響範囲

| 条件 | 影響 |
|------|------|
| `admin_user_ids` が非空（現行） | 実質 allowlist + role 判定。**当面の被害面は限定** |
| allowlist 空 or beta 読込失敗で空扱い | **全認証ユーザーが Ops 系に入れる** |
| V8.6/8.7 新規 Ops API | 同一ヘルパ複製で攻撃面が拡大 |

## 修正要否

**要。** fail-open を **fail-closed**（空なら 403）へ変更すべき。

## 推奨判断

### **fail-open 挙動は正式採用しない**

- 「現行 beta に ID が入っていること」は **運用上の緩和であり Certification 合格条件ではない**  
- allowlist 設定値自体は **正式採用（維持）**  
- コードの `ids.length === 0 → true` は **8.5.1 で廃棄対象**

戻す（git revert `03e7a4f`）は不要。ピンポイントで fail-closed 化する。

---

# 4. SEC-03 — `/api/ops/conversation` authorization

## Issue

`functions/api/ops/conversation.js` に BFF 側の管理者チェックがなく、Bearer を任意転送するだけ。PUBLIC 中は匿名でも AI ops dashboard へ到達しうる。

## 意図判定（Git）

| 証拠 | 内容 |
|------|------|
| `dcc73d4` (2026-07-25) | Conversation V5 observability 追加。BFF は proxy + compose のみで誕生 |
| 同コミットの `ops/dashboard.js` | 既に `isAdminUser` あり → **非対称** |
| `conversation-observability-runbook.md` | ローカル AI `curl` 手順中心。Pages BFF の ADMIN 要件は未規定 |

**判定:**

- Observability API / ops.html への露出は **意図した機能追加**  
- **BFF 管理者ゲート欠落は意図しない欠陥**（他 `/api/ops/*` との一貫性欠如）

## 原因

「Platform を変えず境界で metrics を載せる」方針で AI へプロキシしたが、Pages 公開面の認可を dashboard と揃える実装が漏れた。

## 影響範囲

| 対象 | 影響 |
|------|------|
| Conversation / Ollama / Knowledge の ops メトリクス・アラート | 漏洩しうる |
| PE / CE / Prediction ロジック | 非変更 |
| AI 側が独自認証する場合 | 緩和されうるが **BFF は信頼境界として不足** |

## 修正要否

**要。** `resolveAuthorization` / `isAdminUser`（fail-closed 版）と同等の ADMIN ゲートを追加。

## 推奨判断

### **エンドポイントは維持（正式採用）／無認可は不採用（修正）**

- API 削除や V5 observability の巻き戻しは不要  
- 「誰でも読める Ops conversation」状態は **Certified しない**

---

# 5. Cross-cutting — Version8.5 との関係

| Issue | 8.5 Lock 時点で既に存在？ | 8.5 以降の新規？ |
|-------|---------------------------|------------------|
| SEC-01 | **はい**（OPS-1A / stub） | 新規回帰ではない。V8.7 で影響面拡大 |
| SEC-02 | **はい**（V2 dashboard） | 同上（新規 Ops API が複製） |
| SEC-03 | **はい**（V5、8.5 宣言と同日帯） | Baseline 文書と同時期の既存欠陥 |
| CE-01 | **いいえ**（HEAD に無し） | **作業ツリー + EC2 直置きのロック外変更** |

---

# 6. Version 8.5.1 — 総合推奨

## 戻すもの / 採用するもの

| 対象 | 判断 |
|------|------|
| CE AbilityScores（透過） | **条件付き正式採用（Exception）** — Hard Lock を破ったまま黙認は不可。ADR+git 必須 |
| stub 認証モード自体 | 現行どおり **暫定採用可**（runbook 通り）。別リリースで署名付きへ |
| token.role による profile 無し昇格 | **不採用 → 修正** |
| `admin_user_ids` 空時 fail-open | **不採用 → 修正** |
| `/api/ops/conversation` 無認可 | **不採用 → 修正** |
| Conversation observability 機能 | **正式採用（維持）** |

## Certification Gate

```
Version8.5.1 = Version8.5
  + CE-01 Certified Exception（ADR + git 一致）
  + SEC-01/02/03 修正完了
  → Baseline Integrity PASS / Security PASS
```

現状（修正前）: **CONDITIONAL — 未認定**

## 次アクション（修正提案一覧のみ・実装しない）

1. CE-01: ADR 作成 → CE / mapper をコミット → EC2 と hash 照合 → 8.5.1 Exception 登録  
2. SEC-01: profile/allowlist 必須化、または token.role 無効化／署名必須  
3. SEC-02: 全 `isAdminUser` を fail-closed に統一（可能なら `_lib` へ集約）  
4. SEC-03: conversation BFF に ADMIN ゲート追加  
5. 再監査: system-regression-audit の該当 FAIL を再判定し、本 Certification を PASS 更新  

---

*本ドキュメントは Certification のみ。コード変更は行っていない。*
