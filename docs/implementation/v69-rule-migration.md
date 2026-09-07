# Version69 — Rule Migration Plan

**Date:** 2026-07-28  
**Status:** Design only — コード変更なし  
**Chain:** Shadow → Dual → Soft → Cutover（V46 維持）  
**Focus Rules:** R7 / R1 / R8（Logic Form のみ）

---

## 移行原則

1. **Production 決定は Soft まで Legacy**（`classify_world_line_type`）。  
2. V69 新 Logic Form は Shadow/Dual で観測。  
3. Soft は「決定に影響しうるが即 rollback 可能」な段階。  
4. Cutover は別 Decision + PASS ゲート後のみ。  
5. Threshold 数値・World/Polarity は全 Stage で変更禁止。

---

## Stage Map

```text
Shadow  →  Dual  →  Soft  →  Cutover
  │         │         │         │
  │         │         │         └─ Production = V69 Decision Tree
  │         │         └─ Flag: V69 may influence research/ops preview only
  │         └─ Legacy + V69 parallel; decision = Legacy
  └─ V69 eval only; decision = Legacy
```

---

## Shadow

### Purpose
R7/R1/R8 新 Logic Form を 285R（および拡張コーパス）で評価し、Legacy と差分ログ。

### Scope
- 実装（将来）: `v69_logic_form` 評価のみ  
- 出力: per-race `legacy_world`, `v69_world`, `match_set`, Must gaps, Exclude hits  
- **Production return 不変**

### PASS
- [ ] Dual ログと同等の再現可能な Shadow 完走  
- [ ] Legacy 分布が Shadow 導入前後で一致（非干渉）  
- [ ] R7/R1/R8 旧経路 vs 新 MATCH の差分表が生成される

### Rollback
Shadow ジョブ停止。データ破棄可。Production 影響なし。

---

## Dual

### Purpose
同一入力で Legacy 決定と V69 Decision Tree を並列固定観測。

### Scope
- W-S1 型 Dual-Eval を V69 Form に拡張  
- KPI: Intent GT 一致率（V65 定義）、R7/R1/R8 FP 帰属件数、unsatisfied 率  
- 決定権限: **Legacy**

### PASS
- [ ] Intent 一致率が Legacy 比で非悪化、または乖離理由が Must Missing に限定して説明可能  
- [ ] DEFAULT→core 件数が V69 側で 0（構造要件）  
- [ ] difficulty 単独 midupper が V69 側で 0  

### Rollback
Dual フラグ OFF。Legacy のみ。

---

## Soft

### Purpose
限定環境で V69 決定を「参照可能」にする（本番購入決定はまだ Legacy、または明示オプトイン）。

### Scope（設計）
- Flag: `V69_TRIGGER_SOFT`  
- Soft ON 時のみ preview / research ticket が V69 world を表示しうる  
- **本 Blueprint は Soft 実装を承認しない** — ゲート設計のみ

### PASS（設計要件）
- [ ] 即時 Rollback（フラグ OFF）で Legacy に戻る手順が文書化  
- [ ] Soft 期間の差分アラート（unsatisfied 急増等）

### Rollback
`V69_TRIGGER_SOFT=0`。残ログは監査用。

---

## Cutover

### Purpose
Production の World 決定を V69 Decision Tree に切替。

### Scope（設計）
- `classify_world_line_type` を V69 解決器へ置換、またはラッパで V69 優先  
- Legacy R1–R8 は `legacy_classify` として残置（Rollback 用）

### PASS（必須）
- [ ] Dual/Soft PASS  
- [ ] 別 Decision で Cutover 明示承認  
- [ ] Rollback 手順のリハーサル完了  
- [ ] Prediction/PE 非変更の確認（World ラベルのみ）

### Rollback
- フラグで Legacy `classify_world_line_type` に即戻し  
- またはバイナリ/設定の前版戻し

---

## Rule 別 Migration 注記

| Rule | Shadow/Dual で見るもの | Soft/Cutover リスク |
|---|---|---|
| R7→MIDUPPER_MATCH | difficulty 単独消滅；APT Missing→unsatisfied | unsatisfied 増 |
| R1→MIXED_MATCH | 圧力 first-match 消滅；multi_path 依存 | mixed 減・他 World 増 |
| R8→CORE_MATCH | DEFAULT 消滅；top_gap∧sep | core 減・unsatisfied 増 |

---

## 実装順序（将来・未承認）

1. Shadow evaluator（読み取り専用）  
2. Dual レポート（Intent / FP 帰属）  
3. Soft flag（別承認）  
4. Cutover（別承認）  

**本フェーズでは 1–4 のコードを書かない。**
