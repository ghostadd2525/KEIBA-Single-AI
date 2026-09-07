# Version67 — Rule Dependency

**Date:** 2026-07-28  
**枠:** Signal 不足 / Data 不足 / Rule 設計  
**対象:** Top3 Rule の Trigger FP（R1=50, R7=57, R8=46）

---

## ⑥ Dependency 集計

| Rule | Rule設計 | Data | Signal | FP n |
|---|---:|---:|---:|---:|
| R1_mixed_short_field | **50** | 0 | 0 | 50 |
| R7_midupper_diff | **57** | 0 | 0 | 57 |
| R8_core_default | **46** | 0 | 0 | 46 |

定義（測定）:

- **Data:** `restored_ok=False`  
- **Signal:** 復元成功だが当該原子が missing  
- **Rule設計:** 上記以外（値が揃った上で条件ロジックが Intent と乖離）

→ Trigger FP **153 件すべて Rule設計**。Signal/Data は Top3 FP の主因ではない。

（原子 Missing率はコーパス全体で ~15.8% あるが、Top3 FP レースでは発火条件を満たす値が存在。）

---

## R8 先行 Rule bottleneck（46 件すべて）

各先行 Rule が FAIL したときの bottleneck（重複カウント可）:

| Prior Rule | bottleneck signal | 形態 |
|---|---|---|
| R1 | short_field_pressure | margin |
| R2 | short_field_pressure | margin |
| R3 | phase | margin |
| R4 | late_stop | margin |
| R5 | chaos | margin |
| R6 | chaos | margin |
| R7 | difficulty | margin |

Missing bottleneck は **0**。R8 FP は「信号欠落で落ちた」ではなく **閾値未満で R1–R7 が落ち、DEFAULT に落下**。

---

## 含意（改修指示ではない）

| Rule | 依存の意味 |
|---|---|
| R1 | 設計: sfp ゲートが支配。OR は選別力不足 |
| R7 | 設計: difficulty 単独 Must が広すぎる |
| R8 | 設計: 正の core Must が無く DEFAULT 構造 |

Signal 供給を増やしても、現行条件式のままでは Top3 FP の主因は解けない（本データ上）。
