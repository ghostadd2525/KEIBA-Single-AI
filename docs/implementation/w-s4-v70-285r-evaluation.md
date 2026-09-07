# W-S4 / Version70 — Trigger Refactoring Shadow — 285R

**Generated:** `2026-07-28T07:39:36+00:00`  
**Gate:** `FAIL`  
**Decision authority:** Legacy only（Shadow = V69 Logic Form）  
**Restored signals n:** `240` / 285

## Prediction（Production 非変更・Δ0）

| Key | Value |
|---|---:|
| `Hit` | 218 |
| `Purchase` | 218 |
| `rank710` | 14 |
| `other_1_3` | 1 |
| `other_10_13` | 13 |
| `rank46` | 35 |
| `fingerprint` | d3c43162ebf143239c456521a745d4af12d9cd53c78c561d351d559d88f93f2a |

## World Intent Accuracy（V65 GT）

| Key | Value |
|---|---:|
| `legacy` | 0.2211 |
| `v69_shadow` | 0.0877 |
| `delta` | -0.1333 |

## Positive Match / Unsatisfied

| Key | Value |
|---|---:|
| `positive_match_n` | 109 |
| `positive_match_rate` | 0.3825 |
| `unsatisfied_n` | 176 |
| `unsatisfied_rate` | 0.6175 |

## World Distribution

### Legacy

| Key | Value |
|---|---:|
| `midupper_world` | 110 |
| `core_world` | 104 |
| `mixed_world` | 56 |
| `midhole_world` | 15 |

### V69 Shadow

| Key | Value |
|---|---:|
| `unsatisfied` | 176 |
| `midupper_world` | 6 |
| `mixed_world` | 6 |
| `midhole_world` | 24 |
| `rank7_world` | 65 |
| `core_world` | 8 |

## rank7 Recall

| Key | Value |
|---|---:|
| `legacy_recall` | 0.0 |
| `legacy_support` | 7 |
| `v69_recall` | 0.8571428571428571 |
| `v69_support` | 7 |

## core DEFAULT

| Key | Value |
|---|---:|
| `legacy_default_core_n` | 104 |
| `v69_default_core_n` | 0 |
| `legacy_difficulty_only_midupper_n` | 0 |
| `v69_difficulty_only_midupper_n` | 0 |

## Winner Alignment

### Legacy

| Key | Value |
|---|---:|
| `soft` | 67 |
| `aligned` | 167 |
| `misaligned` | 51 |

### V69

| Key | Value |
|---|---:|
| `unsatisfied` | 176 |
| `soft` | 20 |
| `aligned` | 32 |
| `misaligned` | 57 |

## Gate Checks

| Key | Value |
|---|---:|
| `production_legacy_authority` | True |
| `flag_off_compatible` | True |
| `prediction_fingerprint_stable` | True |
| `hit_non_worse` | True |
| `intent_accuracy_improved` | False |
| `rank7_recall_improved` | True |
| `core_default_decreased` | True |
| `v69_default_core_zero` | True |
| `v69_difficulty_only_midupper_zero` | True |
| `legacy_compat_intact` | True |

**next_stage_allowed:** `HOLD_SHADOW`
