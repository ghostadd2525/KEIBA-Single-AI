# W-S3 Exclusion Analysis

**Date:** 2026-07-28  
**Version:** 61  
**Parent:** `w-s3-exclusion-shadow.md`  
**Cohort:** 104（Unsatisfied ∩ Must→Exclude）

---

## Structural split (reminder)

| Bucket | n | Source |
|---|---:|---|
| Unsatisfied | 176 | W-S1 |
| Must→Exclude ∩ Unsatisfied | **104** | V57 / 本再評価 |
| All Must fail ∩ Unsatisfied | 72 | V57（本フェーズ対象外） |
| Must→Exclude on full 285R | 140 | 再計測 |
| Must→Exclude but other World MATCH | 36 | 140−104 |

---

## Clause × World（104・全 Near Worlds）

| Clause | n |
|---|---:|
| CORE_EXCL:sfp↑_F+ | 77 |
| CORE_EXCL:mid_band_open_ForbidDef | 55 |
| MIDUPPER_EXCL:mid_band_open_ForbidDef | 26 |
| CORE_EXCL:chaos↑_F+ | 24 |
| CORE_EXCL:late∧sust_F+ | 13 |
| MIDHOLE_EXCL:top_gap↑_monopoly_F+ | 13 |
| MIDUPPER_EXCL:chaos∧high_pace_rank7_region | 7 |
| MIDHOLE_EXCL:chaos∧difficulty_extreme | 6 |
| RANK7_EXCL:top_gap↑_ability_resolution | 1 |

**UNEXPLAINED exclude:** 0（条項分解で説明可能）

---

## Polarity ADR interaction（変更なし）

| Clause family | W-S3 polarity link |
|---|---|
| sfp↑ on core | High = **F+**（ADR）→ Exclude 発火は契約整合 |
| chaos↑ on core | High = **F+** → 整合 |
| late∧sust on core | AND-F+ → 整合 |
| mid_band_open | core/midupper Forbid-as-def → 整合 |
| top_gap↑ on midhole/rank7 | midhole F+ monopoly / rank7 Exclude → 整合 |

→ 「条項が ADR と矛盾して発火」ではない。  
問題は **観測極性（median）下で F+ 方向が同時に立ちすぎる**こと。

---

## True vs False Exclusion

| Kind | n | Rate | Meaning |
|---|---:|---:|---|
| True Exclusion | 53 | 51.0% | 除外 World の勝ち帯と不一致/ soft |
| False Exclusion | 51 | 49.0% | 除外 World の勝ち帯と一致なのに除外 |

False Exclusion の primary World 偏り（参考）: core が多い（cohort の 81 が core Near）。

---

## Design-aligned vs Outcome-aligned

| Lens | Result |
|---|---|
| Design / ADR clause lens | 104/104 aligned → 「設計どおりの条項」 |
| Outcome / Winner Alignment lens | 49% false → 「結果から見て過剰」 |

Governance **C** は後者を主根拠とする（ユーザー判定軸: Exclusion 過剰）。

---

## What was not changed

- Polarity ADR 本文  
- Trigger / Exclusion 実装  
- Production Decision  
- Thresholds（未導入）  

---

*Analysis only.*
