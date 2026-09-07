# Version33 — DEFAULT Policy (World Input Contract)

**Date:** 2026-07-27  
**Parent:** `v33-world-input-contract.md`  
**Status:** Design policy only  

本ポリシーは **World Input Contract 上の DEFAULT 可否**を定義する。  
`enrich_stable_features` 等の **技術的欠落補完**の存在事実（V29）を否定しないが、それを **World 正式仕様として追認しない**（V32）。

---

## Definitions

| Term | Meaning |
|------|---------|
| **Technical fallback** | パイプラインが落ちないための数値埋め（例: 0.5, 0.0） |
| **World policy DEFAULT** | 「この値で勝ち筋分類してよい」と契約が認める中立値 |
| **Unsatisfied** | Required 信号が設計どおり供給されていない状態 |

本契約: **Technical fallback ≠ World policy DEFAULT**（原則）。

---

## Policy classes

| Class | Meaning | World classification use |
|-------|---------|--------------------------|
| **D0 Forbidden** | World 正式値としての DEFAULT 禁止 | 使用不可（契約上 unsatisfied） |
| **D1 Conditional** | 明示条件付きのみ | 条件外は Forbidden |
| **D2 Allowed** | 観測・Optional のみ | 分類必須経路に使わない |
| **D3 Runtime nz** | 現行コードの `nz(...,0)` 等 | **契約上の許可ではない**（実装事実） |

---

## Per-signal DEFAULT rules

### D0 — Forbidden（World policy）

| Signal | Forbidden DEFAULT examples | Why |
|--------|---------------------------|-----|
| `race_leg_difficulty` | `0.5` as designed mid / always-pass | V28 飽和・R7 常時通過の主因 |
| `chaos_score` | `0.0` via missing→nz | bug/rank7/mixed 不通の主因の一つ |
| `pace_collapse_risk` | `0.0` fill as “designed collapse” | difficulty/high_pace を歪める |
| `style_entropy` | `0.0` fill as “designed entropy” | 部分式（設計不適合） |
| `late_stop` / `sustained` / `high_pace` / `phase_transition` | 構成欠落由来の擬似低値を正式採用 | midhole/mixed/rank7 誤分類 |
| `win5_leg` missing → base 0.50 as complete difficulty | — | 部分式 |

### D1 — Conditional

| Signal | Condition | Allowed? |
|--------|-----------|----------|
| `short_field_pressure` | 全入力が契約充足した上での計算結果が低い | Yes（真の低圧力） |
| `short_field_pressure` | chaos/collapse 欠落で機械的に潰れた値 | **No**（unsatisfied） |
| `horse_count` internal 12 in formula | 一時的計算継続のみ | Technical only；契約充足には `horse_count` 供給が必要 |
| `field_size` as `horse_count` | **明示 Alias Contract がある場合のみ** | 現状 Alias Contract **なし** → No |

### D2 — Allowed（Optional / observability）

| Signal | Allowed DEFAULT | Notes |
|--------|-----------------|-------|
| `world_line_score` bundle gaps | 0 for missing optional components in **logs only** | 分類必須にしない |
| Research-only display aliases | null 表示 | Production とキーを一致させる |
| Ranker matrix padding | STABLE defaults | **PE 技術領域**；World policy とは分離して記録 |

### D3 — Runtime fact（not endorsed）

現行実装（変更禁止の本フェーズ）:

| Location | Behavior | Contract stance |
|----------|----------|-----------------|
| `STABLE_FEATURE_DEFAULTS['race_leg_difficulty']=0.5` | Technical fallback | **Not World policy** |
| `nz(meta.get('chaos_score',0.0),0.0)` | Missing → 0.0 | **Not World policy** |
| `nz(meta.get('race_leg_difficulty',0.0),0.0)` | Missing key → 0.0（列がある場合は frame 値） | Key 欠落と DEFAULT 0.5 は別経路 |

---

## Satisfaction rules（design）

```text
IF Required signal missing OR only Technical fallback present
THEN World Input Contract status = UNSATISFIED
AND value MUST NOT be treated as designed World evidence
```

実装での「停止 / フォールバック World / エラー」は **本フェーズで規定しない**（Trigger 変更禁止）。

---

## Ranker vs World DEFAULT（境界）

| Domain | DEFAULT 0.5 on difficulty | Allowed? |
|--------|---------------------------|----------|
| Ranker crash avoidance | Technical fallback | PE 領域として事実上存在しうる |
| World Trigger classification | World policy | **Forbidden** |
| Research claiming designed difficulty | — | **Forbidden** if fallback |

同一数値が両ドメインを流れる現状は **契約違反状態**（V29）として記録する。修復は別承認。

---

## Quick reference

| Signal | World DEFAULT |
|--------|:-------------:|
| difficulty | **Forbidden** |
| chaos | **Forbidden** |
| phase | **Forbidden**（欠落由来） |
| late_stop | **Forbidden** |
| sustained | **Forbidden** |
| high_pace | **Forbidden**（欠落由来） |
| short_field_pressure | **Conditional** |
| style_entropy | **Forbidden** |
| pace_collapse | **Forbidden** |
| world_line (obs) | **Allowed (D2)** |
| leg_* intermediates | N/A if difficulty Required satisfied |
| `pace_collapse_risk_v2` alone | **Not an approved DEFAULT/alias** |

---

## Guardrails

- Policy definition only. No code, Trigger, or DEFAULT constant changes.
