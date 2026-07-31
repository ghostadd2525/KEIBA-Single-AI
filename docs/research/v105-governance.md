# Version105 — Governance（Evidence）

**Date:** 2026-07-28  
**Parents:** ADR-003 · ADR-008 · ADR-009 · ADR-010 · V8 · V92 · V103 · V7/V8 Evidence Audit  
**Status:** Design only · **実装禁止**  
**Version tag 注記:** 同番号で `v105-shadow-resolver.md` / `v105-resolver-*` が既に存在する。本票群は **Evidence Governance** 専用（`v105-evidence-*`）。Resolver 票とスコープを共有しない。

---

```
【Production Diagnosis】
Evidence Governance 設計（統合カタログ）。コード・ストア・配線は行わない。

【Server Diagnosis】
Status: PASS（設計文書化）
Evidence: V8 Miss Evidence / ADR-009/010 / V103 / v7v8-evidence-layer-audit

【Client Diagnosis】
Status: BLOCKED
Client Evidence: UI 検証対象外（本フェーズ設計のみ）

Diff Summary: Product Evidence(EV-P) と Core Evidence(EV-S) を Taxonomy で分離。Decision(EV-D) を第三系統化。
Root Cause: N/A（予防ガバナンス）
Expected Action: 実装は別 Decision。本票は境界固定のみ。

【Decision】
Action Type: Evidence Governance Design
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Low
Expected Next Action: 実装承認時は EV-S ストア分離設計 → V103 PROMOTE 配線の順（本票外）
```

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | Evidence Governance |
| Implementation Required | **No** |
| PE / CE / RA / Decision / Trigger 変更 | **No** |
| 新 Feature / 新意味 | **No** |
| ストア統合（単一 JSON 混在） | **禁止** |
| Risk | Low |

---

## 硬制約

| ID | 制約 |
|---|---|
| G105-1 | Prediction 改善（EV-P）と Semantic 蓄積（EV-S）を同一 KPI・同一昇格経路にしない |
| G105-2 | EV-S を Miss Analyzer 必須入力にしない |
| G105-3 | EV-D ROI/PnL を Core Completeness 成功指標にしない（ADR-009） |
| G105-4 | Explanation Confidence を勝率/Calibration に再解釈しない（ADR-010） |
| G105-5 | Product V8「Decision」（FRI）と ADR-008 Decision Layer を同一 Owner 扱いしない |
| G105-6 | V103 DO_NOT_EXPORT / KEEP_DERIVED を本票で PROMOTE しない |
| G105-7 | 本フェーズでコード・DB・フラグ実装禁止 |

---

## 統合管理の意味（確定）

許可:

- 単一 **Taxonomy / Ownership / Lifecycle 語彙**
- 監査時の横断索引（クラスラベル必須）
- 混同検知チェックリスト

禁止:

- `evidence/improvement` に Semantic payload を混在保存
- Completeness Shadow 結果を Miss Root Cause enum に直結
- Affinity / EC を Hit 改善 Canary の成功条件にする

---

## 混同検知チェックリスト（運用）

| # | 問い | Fail 時 |
|---|---|---|
| 1 | このファイル/行は EV-P / EV-S / EV-D のどれか？ | 分類してから保存 |
| 2 | 更新トリガは Hit/Miss か、記述再観測か、Shadow か？ | クラス不一致なら拒否 |
| 3 | 昇格先は Knowledge / Contract Surface / Decision 推奨のどれか？ | 他クラス昇格は拒否 |
| 4 | Consumer が勝率語で EC を読んでいないか？ | ADR-010 違反 |
| 5 | Core 研究が ROI を成功定義にしていないか？ | ADR-009 違反 |

---

## 成果物

| 成果物 | Path |
|---|---|
| Evidence Taxonomy | `docs/research/v105-evidence-taxonomy.md` |
| Evidence Lifecycle | `docs/research/v105-evidence-lifecycle.md` |
| Evidence Ownership | `docs/research/v105-evidence-ownership.md` |
| Governance | `docs/research/v105-governance.md` |

---

## 一文

**管理は一つに、置き場と昇格は三つに分ける。**
