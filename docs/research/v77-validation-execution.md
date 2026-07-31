# Version77 — Validation Execution（E1/E2）

**Generated:** `2026-07-28T08:35:42+00:00`  
**Plan:** V76 E1/E2 — データ分割①/② + Gate 判定  
**Split:** race_id 時系列 half（n=142 / 143）  
**変更なし:** Trigger / Blueprint / Signal / Threshold / PE / Prediction / Production / World Contract

## 分割分布（CEW）

| World | full | split1 | split2 |
|---|---:|---:|---:|
| `core_world` | 8 | 8 | 0 |
| `midupper_world` | 6 | 5 | 1 |
| `midhole_world` | 24 | 14 | 10 |
| `rank7_world` | 65 | 27 | 38 |
| `mixed_world` | 6 | 3 | 3 |
| `bug_world` | 0 | 0 | 0 |
| `unsatisfied` | 176 | 85 | 91 |

## E1 — Split1 Gate（要点）

- rank7 n=27, midhole n=14
- rank7 field_size r=-0.1181
- midhole history−win_prob gap (split1) = see JSON effects

## E2 — Split2 Gate（要点）

- rank7 n=38, midhole n=10
- rank7 field_size r=-0.1132
- midhole history−win_prob gap (split2) = see JSON effects

## Ready 再判定（要約）

| World | Before (V75) | After (V77) |
|---|---|---|
| `core_world` | Blocked | **Blocked** |
| `midupper_world` | Blocked | **Blocked** |
| `midhole_world` | Partial | **Partial** |
| `rank7_world` | Partial | **Ready** |
| `mixed_world` | Blocked | **Blocked** |
| `bug_world` | Blocked | **Blocked** |
| `unsatisfied` | Partial | **Ready** |

## 数値正本

`docs/research/_v77-validation-execution.json`
