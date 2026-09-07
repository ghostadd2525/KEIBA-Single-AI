# Version 3 — Admission Correction Design

**Date:** 2026-07-24  
**Status:** Design Complete · Design **PASS** · A-05 Accuracy **implemented**（[`v3-a05-accuracy-report.md`](./v3-a05-accuracy-report.md)）  
**RCA:** PASS（[`v3-lab-offline-rca.md`](./v3-lab-offline-rca.md)）  
**PRR:** HOLD 継続  
**Scope:** Admission のみ · Selection / Evaluation / Representation / Purchase 対象外

---

## 1. Purpose

Offline Gate FAIL（Control 59 → Treatment 42）の主因である **Admission A-03 過剰 promote** に対し、  
**A-03 を変更せず**、実データ向けの独立 Admission Candidate を設計する。

本 Round は **設計のみ**。実装・AB 実行・Shadow・Production・Phase 3 には着手しない。

---

## 2. RCA 正本（前提の固定）

| 項目 | 結論 |
|------|------|
| 主因 | A-03 過剰 promote（実フィールドで style-rarity が過発火） |
| 副因 | D1 が promote 後の `model_rank`/`win_prob` を忠実に増幅 |
| A-04 | 副次（悪化 29 のうち A-04 promote 3） |
| Flag 誤適用 | 否定 |
| データリーク | 否定 |
| Metric | Lab / Offline Gate とも top-1 pick == winner（一致） |

---

## 3. Non-Goals

| 非目標 | 理由 |
|--------|------|
| A-03 コード改変 | 独立候補方針 · 回帰比較を壊さない |
| Selection / Evaluation / Representation / Purchase 改変 | スコープ外 |
| Feature Flag 既定値変更 | 本番リスク |
| 本 Round の実装・AB 実行 | 停止条件 |
| Shadow / Production / Phase 3 | PRR HOLD |

---

## 4. Design Contents（索引）

| # | 設計項目 | 詳細文書 |
|---|----------|----------|
| 1 | A-03 の設計上の問題点 | 本文 §5 + Spec §2 |
| 2 | Lab / Offline 入力分布差への対応 | 本文 §6 |
| 3 | promote 発火条件の見直し方針 | Spec §3 |
| 4 | 本命保護 Admission 設計 | Spec §4 |
| 5 | 新 Admission Candidate | Spec §5（**A-05** 予約） |
| 6 | Feature Flag 設計 | [`v3-admission-correction-flag-design.md`](./v3-admission-correction-flag-design.md) |
| 7 | AB 実験計画 | [`v3-admission-correction-experiment-plan.md`](./v3-admission-correction-experiment-plan.md) |
| 8 | Hard Gate | Spec §7 + Success Criteria |
| 9 | 成功条件 | [`v3-admission-correction-success-criteria.md`](./v3-admission-correction-success-criteria.md) |

**Design Specification（正本仕様）:** [`v3-admission-correction-spec.md`](./v3-admission-correction-spec.md)

---

## 5. A-03 の設計上の問題点（要約）

1. **Field ゲートが実データで常時開放**  
   `PROMOTE_FIELD_MIN=12` は Lab では Pool×9 のみ開くが、Real では 86% が field≥12。

2. **Style rarity 単体が弱すぎる**  
   `coverage_score ≥ 100` ≒ deep 帯に core にない脚質が 1 頭いれば即 promote。大頭数では高頻度。

3. **Hard promote が D1 を強制**  
   `model_rank=1` + `win_prob = top_wp+0.08` により、下流 Evaluation（D1）が本命を捨てざるを得ない。

4. **本命保護が存在しない**  
   `winner_rank=1` / 強い top-1 margin を壊さないゲートがない。Offline 悪化 29 はすべて rank1 破壊。

5. **Lab 過適合**  
   Accurcy corpus の Hit 層 field=8 前提で「安全」に見えた。実分布（field mean 14.6）では危険。

詳細: Spec §2。

---

## 6. Lab と Offline の入力分布差への対応方針

| 方針 | 内容 |
|------|------|
| **Dual-Gate 必須** | Lab Accuracy のみで PASS としない。Offline Gate（実 285R）を同格 Hard Gate にする |
| **発火率ターゲットを Offline で定義** | promote 率を Lab の 3% に合わせるのではなく、Real 上で「本命破壊ゼロ + 正の深掘り」に校正 |
| **分布アウェアな閾値** | field / style rarity を単独必要条件にしない。本命 margin・相対深さを併用 |
| **Lab コーパス改善は別枠** | 本 Candidate の必須ではないが、回帰用に Real-like field 層の追加を Experiment Plan に推奨 |
| **A-03 は凍結資産** | Baseline v3 比較用に残す。置換は Flag 切替で行う |

---

## 7. Candidate 概要（A-05）

| 項目 | 値 |
|------|-----|
| Candidate ID | **A-05**（Admission Correction） |
| Policy ID（予約） | `AP-V3-A05-favorite-safe-coverage` |
| Stage | Admission のみ |
| 対 A-03 | **独立** · A-03 ソース非改変 · Primary 実験では同時 ON 禁止 |
| 核心アイデア | **Favorite-Safe Gate** + **厳格 Coverage** + **Soft / Conditional Promote** |
| Flag（予約） | `F_V3_A05_ADM_FAVSAFE_ENABLED`（既定 OFF · 本 Round 未追加） |

狙い: Offline で A-03 が取った正しい深掘り（+12）の方向性は残しつつ、本命破壊（−29）を設計で封じる。

---

## 8. Deliverables

| 提出物 | パス |
|--------|------|
| Admission Correction Design | 本文書 |
| Design Specification | [`v3-admission-correction-spec.md`](./v3-admission-correction-spec.md) |
| Experiment Plan | [`v3-admission-correction-experiment-plan.md`](./v3-admission-correction-experiment-plan.md) |
| Feature Flag Design | [`v3-admission-correction-flag-design.md`](./v3-admission-correction-flag-design.md) |
| Success Criteria | [`v3-admission-correction-success-criteria.md`](./v3-admission-correction-success-criteria.md) |

---

## 9. Decision Implications

| 項目 | 状態 |
|------|------|
| RCA | PASS（維持） |
| PRR | **HOLD**（維持） |
| Offline Gate | FAIL（維持 · 本設計で次手を定義） |
| 実装 | **未着手** |

---

## 10. Stop Condition

**Admission Correction Design 完了。ここで停止する。**  
実装 · AB 実行 · Shadow · Production · Phase 3 には着手しない。
