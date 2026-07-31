# Version102 — Missing Semantic Inventory

**Generated:** `2026-07-28T13:10:35+00:00`

**原則:** 新しい Feature は追加しない。現有情報で説明できない／first-class でない部分のみ。

| ID | Missing（first-class） | Held instead | n_races |
|---|---|---|---:|
| `MS-1` | Expected Strategy as race payload | V75 static map keyed by world_label | 285 |
| `MS-2` | Affinity vector in dual-eval / Core emit | Derivable from decision_trace must_gaps (research) | 176 |
| `MS-3` | Exclusion reasons list in decision_trace | exclude:bool only; reasons via research mirror of V44 predicates | 176 |
| `MS-4` | ExplanationConfidenceBundle emit (ADR-010) | Derivable from Completeness/trace slots | 285 |
| `MS-5` | Near Miss class / near_world as Core emit | Derivable from must∧exclude in decision_trace | 176 |
| `MS-6` | Natural-language why sentence | Structured traces only | 285 |

## 詳細

### `MS-1`

- impact: ES adds no race-specific semantic beyond World
- new_feature: **False**

### `MS-2`

- impact: Affinity not first-class; explanation needs derivation step
- new_feature: **False**

### `MS-3`

- impact: Why excluded needs off-payload reconstruction
- new_feature: **False**

### `MS-4`

- impact: EC defined but not returned as Core object
- new_feature: **False**

### `MS-5`

- impact: Taxonomy exists in research; not serialized on race
- new_feature: **False**

### `MS-6`

- impact: Machine-closed ≠ human prose; not a Feature gap
- new_feature: **False**

## 結論

説明不能な『未知概念』よりも、**保持形態が導出依存**であることが主欠落。
Feature 追加ではなく、既存 Trace の first-class 露出が論点（実装は別 Decision・本監査では禁止）。
