# W-S4 Shadow Report — V69 Trigger Refactoring

**Generated:** `2026-07-28T07:39:36+00:00`

## Scope

- Blueprint: V69（R7 UPPER∧DEV∧APT / R1 multi_path / R8 Positive Match / Decision Tree）
- Migration: **Shadow only** — Production Decision = Legacy
- Corpus: 285R

## Structural Outcomes

| Key | Value |
|---|---:|
| `v69_default_core_n` | 0 |
| `legacy_default_core_n` | 104 |
| `v69_difficulty_only_midupper_n` | 0 |
| `unsatisfied_n` | 176 |
| `positive_match_n` | 109 |

### V69 World Distribution（285R）

| World | n |
|---|---:|
| unsatisfied | 176 |
| rank7_world | 65 |
| midhole_world | 24 |
| midupper_world | 6 |
| mixed_world | 6 |
| core_world | 8 |

### Top Legacy→V69 Transitions

| Transition | n |
|---|---:|
| core_world→unsatisfied | 86 |
| midupper_world→unsatisfied | 54 |
| midupper_world→rank7_world | 37 |
| mixed_world→unsatisfied | 26 |
| mixed_world→rank7_world | 24 |

## Intent vs Shadow

| Key | Value |
|---|---:|
| `intent_accuracy_legacy` | 0.22105263157894736 |
| `intent_accuracy_v69` | 0.08771929824561403 |
| `delta` | -0.13333333333333333 |

## Production Non-Interference

- `decision_authority` = `legacy` on all rows
- Prediction Fingerprint unchanged（Shadow 評価は Prediction 非実行）
- Feature flags default OFF / path=legacy（compat check）

**Gate:** `FAIL`
