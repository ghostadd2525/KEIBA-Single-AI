# W-S3 Exclusion Shadow Re-evaluation

**Date:** 2026-07-28  
**Version:** 61  
**Scope:** Shadow 再評価のみ — Trigger / Polarity / Signal / Production / Prediction 変更禁止  
**Premise:** W-S3 Polarity ADR = Accepted（閾値未導入；観測は batch-median 継続）  
**Cohort:** Unsatisfied かつ Must→Exclude = **104**（V57 定義）  
**Data:** `w-s3-exclusion-104-rows.jsonl` / `w-s3-exclusion-shadow-data.json`

---

## Production / 285R（Δ0）

| Metric | Δ |
|---|---:|
| Prediction Fingerprint | 0（一致） |
| Hit | 0 |
| Purchase | 0 |
| rank710 | 0 |
| other_1_3 | 0 |
| other_10_13 | 0 |
| rank46 | 0 |
| other_miss | 0 |

Decision authority = **Legacy** のみ。

---

## Method（推測禁止）

| Term | Definition（実測） |
|---|---|
| **Near Match** | ある World で `must=True` かつ `exclude=True`（Exclude 除去なら MATCH） |
| **Cohort 104** | Near Match **かつ** `v44_world=unsatisfied`（V57） |
| **True Exclusion** | Cohort 内・primary Near World の Winner Alignment ≠ `aligned` |
| **False Exclusion** | Cohort 内・primary Near World の WA = `aligned`（勝ち帯と矛盾して除外） |
| **Clause** | V44 EXCLUDE × W-S3 F+ ラベルで発火条項を分解（評価器 exclude と整合） |
| **design_aligned** | 発火条項が UNEXPLAINED 以外（104/104） |

Primary Near World 優先順: core → midupper → midhole → rank7 → mixed → bug。

---

## ① Exclusion 妥当性（104）

| 観点 | 結果 |
|---|---|
| 条項が V44/W-S3 F+ に整合して発火 | **104/104 design_aligned** |
| 勝ち馬帯との整合（False Exclusion） | **51/104 (49.0%)** |
| True Exclusion | **53/104 (51.0%)** |

**解釈:** Exclusion **条項自体は設計どおり発火**している。一方、勝ち馬 Alignment では約半数が「本来その World 帯に入るのに除外」→ **過剰発火（観測極性下）**。

---

## ② World別内訳（104・Near World 重複可）

| World | n（must∧exclude） |
|---|---:|
| core_world | 81 |
| midupper_world | 32 |
| midhole_world | 13 |
| rank7_world | 1 |
| mixed_world | 0 |
| bug_world | 0 |

---

## ③ False Exclusion

**n = 51 / 104 (49.0%)**  
Primary Near World の Winner Alignment = `aligned`。

---

## ④ True Exclusion

**n = 53 / 104 (51.0%)**  
WA = soft 25 + misaligned 28。

---

## ⑤ Near Match

| Scope | n |
|---|---:|
| Cohort 104（Unsatisfied ∩ Must→Exclude） | **104** |
| 285R 全体の Must→Exclude | **140** |
| うち他 World が Positive Match できた件数 | **36**（140−104） |

Exclude を除けば Positive Match 候補になる件数（Cohort）= **104**。

---

## ⑥ Winner Alignment（primary Near World）

| Alignment | n |
|---|---:|
| aligned | 51 |
| soft | 25 |
| misaligned | 28 |

---

## ⑦ Exclusion Root Cause（primary 条項ランキング）

| Rank | Clause | n |
|---|---|---:|
| 1 | `CORE_EXCL:sfp↑_F+` | 77 |
| 2 | `CORE_EXCL:mid_band_open_ForbidDef` | 55 |
| 3 | `CORE_EXCL:chaos↑_F+` | 24 |
| 4 | `CORE_EXCL:late∧sust_F+` | 13 |
| 5 | `MIDHOLE_EXCL:top_gap↑_monopoly_F+` | 13 |
| 6 | `MIDUPPER_EXCL:mid_band_open_ForbidDef` | 9 |
| 7 | `MIDHOLE_EXCL:chaos∧difficulty_extreme` | 6 |
| 8 | `RANK7_EXCL:top_gap↑_ability_resolution` | 1 |

全 Near Worlds 合算の条項ランキングは `w-s3-exclusion-analysis.md`。

---

## Governance

# **C — Exclusion が過剰**

根拠: False Exclusion 率 **49%**。条項は設計整合だが、勝ち帯整合で見て過剰。  
主因候補条項: **sfp↑** と **mid_band_open**（core）。

詳細: `w-s3-governance.md`

---

*Version61 — shadow re-eval only. No Trigger/Polarity/Production changes.*
