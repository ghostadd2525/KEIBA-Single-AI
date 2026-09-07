# Version 3 — P1 Lab Report

**Date:** 2026-07-24  
**Status:** **P1 Lab Complete**（Accuracy 介入なし）  
**Design authority:** [`v3-design-report.md`](./v3-design-report.md)  
**Code root:** `research/v3_lab/`（V2 Production 非配線）

---

## 1. 目的

V2 Final（Hit **218**）を維持したまま、V3 新世代アーキテクチャの **Offline Lab 基盤のみ**を構築する。  
Accuracy 改善・新アルゴリズム本番配線は行わない。

---

## 2. Pipeline 図

```text
[A] Representation  →  [B] Admission  →  [C] Selection
                                              ↓
                         [E] Purchase  ←  [D] Evaluation
```

```mermaid
flowchart LR
  Rep[Representation] --> Adm[Admission]
  Adm --> Sel[Selection]
  Sel --> Ev[Evaluation]
  Ev --> Pur[Purchase]
```

P1 では各 Stage は **スタブ**。`F_V3_*` がすべて OFF のとき identity。

---

## 3. Feature Flag 一覧

| Flag | 既定 | 役割 |
|------|------|------|
| `F_V3_LAB_ENABLED` | OFF | Lab マスタ |
| `F_V3_REPRESENTATION_ENABLED` | OFF | Representation stub |
| `F_V3_ADMISSION_ENABLED` | OFF | Admission stub |
| `F_V3_SELECTION_ENABLED` | OFF | Selection stub |
| `F_V3_EVALUATION_ENABLED` | OFF | Evaluation stub |
| `F_V3_PURCHASE_ENABLED` | OFF | Purchase stub |
| `F_V3_RANK_D1_ENABLED` | OFF | 予約（P2） |
| `F_V3_RANK_D2_ENABLED` | OFF | 予約（P2） |
| `F_V3_AP_BANDED_ENABLED` | OFF | 予約（P3） |
| `F_V3_AP_COVERAGE_ENABLED` | OFF | 予約（P3） |
| `F_V3_SEL_REORDER_ENABLED` | OFF | 予約（P4） |

Aliases: Roadmap の `WIN5_V3_*` を同名用途で読取可（実装は `flags.py`）。

**OFF ≡ V2 Production 非干渉**（本パッケージを本番経路から import しない）。

---

## 4. Contract 一覧

| Contract ID | Stage |
|-------------|-------|
| `v3-lab-representation/1.0` | Representation |
| `v3-lab-admission/1.0` | Admission |
| `v3-lab-selection/1.0` | Selection |
| `v3-lab-evaluation/1.0` | Evaluation |
| `v3-lab-purchase/1.0` | Purchase |
| `v3-lab-pipeline/1.0` | End-to-end LabBundle |

定義: `research/v3_lab/contracts.py`

---

## 5. 計測ポイント

| Metric point | 意味 |
|--------------|------|
| `lab.pipeline.start` / `end` | パイプライン境界 |
| `lab.stage.*` | 各 Stage 実行 |
| `lab.identity` | Flag OFF identity 経路 |
| `lab.ab.control_hit` | Control Hit |
| `lab.ab.treatment_hit` | Treatment Hit |
| `lab.ab.churn_hit` | Control hit → Treatment miss |

---

## 6. AB Harness

- モジュール: `research/v3_lab/ab_harness.py`
- Control 固定値: Hit **218** / Corpus **285R**（synthetic fixture）
- Treatment: P1 では Flag OFF のまま → Control と同一
- Hard Gate（将来）: Hit > 218 ∧ churn_hit = 0（P1 では未主張）
- **Control 再現:** `control_reproduces_218 == True`（テスト済）

Miss Taxonomy Lock: `taxonomy.py`（層 Eval/Boundary/Reorder/Pool/Delete、合計 miss=67）

---

## 7. Experiment Registry

| Experiment ID | Phase | Status |
|---------------|-------|--------|
| `v3-p1-lab-harness` | P1 | active_lab |
| `v3-rank-d1-recal-285r-ab` 他 | P2–P4 | reserved |

---

## 8. 変更ファイル一覧

| Path | 内容 |
|------|------|
| `research/v3_lab/flags.py` | F_V3_* |
| `research/v3_lab/contracts.py` | Stage contracts |
| `research/v3_lab/stages.py` | Stage stubs |
| `research/v3_lab/pipeline.py` | Lab pipeline |
| `research/v3_lab/metrics.py` | 計測 |
| `research/v3_lab/debug.py` | Debug 出力 |
| `research/v3_lab/ab_harness.py` | AB Harness |
| `research/v3_lab/registry.py` | Experiment Registry |
| `research/v3_lab/taxonomy.py` | Miss Taxonomy Lock |
| `research/v3_lab/tests/*` | Unit tests |
| `docs/releases/v2-maintenance-mode.md` | V2 保守宣言 |
| `docs/releases/v3-p1-lab-report.md` | 本レポート |
| `docs/releases/v3-design-report.md` | P1 実装ステータス追記 |
| `docs/releases/v3-experiment-roadmap.md` | P1 完了マーク |

**未変更:** V2 Production / Prediction API / RaceCardSummary / Operations / Explain / UI / Accuracy 本番ロジック

---

## 9. テスト結果

```text
cd research/v3_lab
python -m unittest discover -s tests -v
Ran 8 tests — OK
```

| Test | Result |
|------|--------|
| Flag default OFF | PASS |
| Pipeline identity | PASS |
| Contracts | PASS |
| Control Hit=218 reproduce | PASS |
| Taxonomy lock sum=67 | PASS |
| Registry / debug | PASS |

---

## 10. 停止条件

P1 Lab 完了。次の Accuracy 改善（P2 Ranking / Feature）には着手しない。
