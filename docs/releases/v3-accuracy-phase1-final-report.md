# Version 3 — Accuracy Phase 1 Final Report

**Date:** 2026-07-24  
**Close ID:** `v3-accuracy-phase1-close/1.0`  
**Status:** **CLOSED**  
**Design authority:** [`v3-design-report.md`](./v3-design-report.md)  
**Baseline:** `research/v3_lab/baselines/lab_baseline_p5.json`（**変更なし**）

---

## 1. 目的

Version 3 Accuracy Phase 1 の成果を固定し、次フェーズ研究を**別承認で**開始できる状態にする。  
本 Close では新しい Accuracy アルゴリズムは実装しない。

---

## 2. Decision（確定）

| 項目 | 決定 |
|------|------|
| Lab 一次採用候補 | **A-01（D1 Recalibrator）** Hit **246** |
| Lab 二次採用候補 | **A-02（D2 Listwise Reranker）** Hit **242** |
| 同時 ON | **採用しない** |
| 本番配線 | **行わない** |
| Baseline | **更新なし**（P5 `v3-lab-baseline-p5-v1` 維持） |

根拠: [`v3-accuracy-candidate-review.md`](./v3-accuracy-candidate-review.md)

---

## 3. Phase 1 成果サマリ

| マイルストーン | 結果 |
|----------------|------|
| Lab Baseline | Hit **218** / 285R |
| A-01 Lab + Validation | Hit **246** · churn 0 · **PASS** |
| A-02 Lab | Hit **242** · churn 0 · **PASS** |
| Candidate Review | 同一条件 Hit 246 > 242 · 改善重複率 **0** |
| Phase 1 Close | 本レポート |

```text
P5 Freeze → A-01 (Primary) → A-02 (Secondary) → Candidate Review → Phase 1 CLOSE
```

---

## 4. Candidate Registry

| Rank | ID | Flag | Hit | Status |
|------|-----|------|-----|--------|
| 1 | A-01 | `F_V3_RANK_D1_ENABLED` (OFF) | 246 | **lab_primary_candidate** |
| 2 | A-02 | `F_V3_RANK_D2_ENABLED` (OFF) | 242 | **lab_secondary_candidate** |

正本: `research/v3_lab/accuracy_candidate_registry.py`  
Artifact: `research/v3_lab/baselines/accuracy_phase1_close/accuracy_candidate_registry.json`  
文書: [`v3-accuracy-candidate-registry.md`](./v3-accuracy-candidate-registry.md)

---

## 5. Baseline

| 項目 | 値 |
|------|-----|
| Baseline ID | `v3-lab-baseline-p5-v1` |
| Control Hit | **218** |
| Phase 1 Close での更新 | **なし** |

---

## 6. Feature Flag Inventory（Accuracy 関連）

| Flag | 既定 | Phase 1 役割 |
|------|------|----------------|
| `F_V3_RANK_D1_ENABLED` | **OFF** | Primary Candidate |
| `F_V3_RANK_D2_ENABLED` | **OFF** | Secondary Candidate |

全 Flag 既定 OFF · 本番配線なし。  
詳細: [`v3-feature-flag-inventory.md`](./v3-feature-flag-inventory.md)

---

## 7. Experiment Status

| Experiment | Status |
|------------|--------|
| P0–P5 | complete / frozen |
| A-01 | **lab_primary_candidate** |
| A-02 | **lab_secondary_candidate** |
| Candidate Review | complete |
| Phase 1 Close | **complete** |
| Phase 2+ | **not_started / reserved** |

詳細: [`v3-experiment-status.md`](./v3-experiment-status.md)

---

## 8. 変更ファイル一覧（Close のみ）

| Path | 内容 |
|------|------|
| `research/v3_lab/accuracy_candidate_registry.py` | Candidate / Flag / Status スナップショット |
| `research/v3_lab/registry.py` | Experiment status 更新 |
| `research/v3_lab/baselines/accuracy_phase1_close/*` | JSON artifacts |
| `docs/releases/v3-accuracy-phase1-final-report.md` | 本レポート |
| `docs/releases/v3-accuracy-candidate-registry.md` | Candidate Registry |
| `docs/releases/v3-feature-flag-inventory.md` | Flag Inventory |
| `docs/releases/v3-experiment-status.md` | Experiment Status |
| `docs/releases/v3-experiment-roadmap.md` | Roadmap 更新 |
| `docs/releases/v3-design-report.md` | Phase 1 Close 追記 |

**未変更:** Evaluation ロジック · Representation · Admission · Selection · Purchase · V2 Production · API / UI / Ops / Explain · `lab_baseline_p5.json`

---

## 9. 次フェーズ

| 項目 | 状態 |
|------|------|
| Accuracy Phase 2 | **未着手**（別承認） |
| 新規アルゴリズム | 禁止（本 Close 範囲外） |
| 本番 ON | 禁止（別承認） |

---

## 10. 停止

**Accuracy Phase 1 Close 完了。ここで停止する。**  
Phase 2（新規アルゴリズム）には着手しない。
