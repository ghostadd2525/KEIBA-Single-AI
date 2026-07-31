# Version65 — World Accuracy（Precision / Recall）

**Date:** 2026-07-28  
**Predicted:** Production AI Legacy World  
**Ground Truth:** Design Intent Oracle（V42–V45）  
**n:** 285

---

## 全体

| Metric | AI (Legacy) |
|---|---:|
| Agreement / Accuracy | **22.1%** |
| Macro Precision | **17.3%** |
| Macro Recall | **14.4%** |

---

## ⑤ Precision / ⑥ Recall

| World | Support (GT) | Precision | Recall | 注 |
|---|---:|---:|---:|---|
| core | 45 | 19.2% | 44.4% | AI core=104 → FP 多い |
| midupper | 92 | 32.7% | 39.1% | 相対的に最良だが不十分 |
| midhole | 50 | 6.7% | 2.0% | ほぼ未検出 |
| rank7 | 7 | n/a | **0.0%** | AI が一度も付与せず |
| mixed | 40 | 10.7% | 15.0% | |
| bug | 25 | n/a | **0.0%** | AI が一度も付与せず |
| unsatisfied | 26 | n/a | **0.0%** | AI は常にいずれか World |

### 読み（測定）

- rank7 / bug / unsatisfied は **Recall 0** — 設計意図上存在しても AI が出せない。  
- core は Recall 44% だが Precision 19% — **意図外の core 押し込み**（V42 DEFAULT と整合）。  
- midhole は Intent GT 50 件に対し AI 正解 1 件。

Shadow 対照の P/R は JSON `precision_recall.shadow`（主判定外）。
