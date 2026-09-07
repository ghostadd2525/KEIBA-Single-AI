# Version64 — World Classification Accuracy（Precision / Recall）

**Date:** 2026-07-28  
**Predicted:** V44 Shadow (`v44_world`)  
**Ground Truth:** V43 Semantic Expected-Characteristics Oracle  
**n:** 285

---

## 全体

| Metric | Shadow | Legacy（対照） |
|---|---:|---:|
| Accuracy | **9.5%** | 22.5% |
| Macro Precision | **23.2%** | （参考） |
| Macro Recall | **20.5%** | （参考） |

---

## ③ Precision / ④ Recall（Shadow）

| World | Support (GT) | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| core_world | 80 | 6 | 2 | 74 | **75.0%** | **7.5%** |
| midupper_world | 54 | 1 | 5 | 53 | 16.7% | **1.9%** |
| midhole_world | 82 | 4 | 20 | 78 | 16.7% | **4.9%** |
| rank7_world | 7 | 6 | 59 | 1 | **9.2%** | 85.7% |
| mixed_world | 11 | 1 | 5 | 10 | 16.7% | 9.1% |
| bug_world | 25 | 0 | 0 | 25 | n/a（未予測） | **0.0%** |
| unsatisfied | 26 | 9 | 167 | 17 | **5.1%** | 34.6% |

### 読み（測定）

- **core:** Precision は高い（出した 8 件中 6 が GT core）が Recall 7.5% — **ほぼ拾えない**。  
- **rank7:** Recall は高いが Precision 9.2% — **過剰割当**（FP 59）。  
- **bug:** Shadow は 0 件 — 設計 Must（exception_flag）が供給されない（V45/V59 と整合）。  
- **unsatisfied:** FP 167 — GT では World があるのに Shadow が落とす主因。

---

## Legacy 対照（参考・非主判定）

Legacy は Semantic GT に対し Accuracy 22.5%。Shadow より高いが、V45 のとおり **Spec 準拠の Positive Match 実装ではない**（DEFAULT core 等）。本フェーズの主検証対象は Shadow。

---

## 設計シェアとの乖離（再掲）

Shadow は core/midupper をほぼ出さず、unsatisfied と rank7 に偏る。  
Design share（core 30% / midupper 35%）と **観測分布が一致しない**。
