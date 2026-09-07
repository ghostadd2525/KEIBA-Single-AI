# Version67 — Trigger Rule Anatomy Audit

**Date:** 2026-07-28  
**Subject:** R1 / R7 / R8 の内部条件責任分解  
**Locks:** Trigger / Threshold / Signal / Polarity / PE / Prediction / Production — **変更禁止**  
**Parents:** V66（Top3 = R7 57 / R1 50 / R8 46）

---

## 結論（1行）

条件単位の失敗点は特定できたが、主因は閾値ではなく **Rule 構造**（R8=DEFAULT、R7=difficulty 単一、R1=sfp ゲート＋広すぎる OR）。Governance **C**。

---

## ① Rule 内部条件（実コード）

### R1_mixed_short_field → `mixed_world`

```text
AND(
  short_field_pressure >= 0.72,          # AND gate
  OR(
    phase >= 0.48,
    chaos >= 0.42,
    difficulty >= 0.42
  )                                       # OR bundle
)
```

| 要素 | 種別（記述） |
|---|---|
| sfp≥0.72 | AND 必須ゲート（Must 的） |
| phase / chaos / difficulty | OR 腕（Aux 的・代替経路） |
| Exclusion | Rule 本体に無し |

### R7_midupper_diff → `midupper_world`

```text
AND( difficulty >= 0.50 )
```

| 要素 | 種別 |
|---|---|
| difficulty≥0.50 | 単一条件（Must 的・唯一） |
| Aux / Exclusion / OR | **無し** |

### R8_core_default → `core_world`

```text
DEFAULT  # parts=[] — R1–R7 全 FAIL 時に発火
```

| 要素 | 種別 |
|---|---|
| 正の Must | **無し**（V42: 能力決着ではない） |
| 実質 | 他 Rule の残余 = Exclusion-of-others |

---

## ② 条件別 Failure（Trigger FP 内）

### R1（FP 50）

| 観測 | n |
|---|---:|
| sfp ゲート True（必須） | **50/50** |
| OR 腕が 3 本同時 True | 42 |
| OR 腕 2 本 | 7 |
| OR 単独 difficulty のみ | 1 |
| 依存: Rule設計 | **50** |

OR 寄与（FP 上で True だった回数）: difficulty **50** / chaos **49** / phase **42**。  
→ FP 時はほぼ常に OR 全体が通り、**選別は sfp ゲートのみ**。

### R7（FP 57）

| 観測 | n |
|---|---:|
| difficulty≥0.50 | **57/57** |
| 依存: Rule設計 | **57** |

単一条件のため、失敗点 = その条件そのもの。

### R8（FP 46）

| 観測 | n |
|---|---:|
| R1–R7 全 FAIL（margin） | **46/46** |
| 先行 bottleneck 例 | 全件で sfp/phase/chaos/difficulty 等が margin 不足 |
| 依存: Rule設計 | **46**（Data 0） |

正条件が無いため、「どの原子が失敗したか」ではなく **残余構造自体**が FP 源。

---

## 数値正本

`docs/research/_v67-rule-anatomy.json`
