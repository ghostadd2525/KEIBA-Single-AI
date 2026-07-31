# Version45 — Trigger Specification Gap Audit

**Date:** 2026-07-28  
**Type:** Audit only（実装・修正・Threshold・Production 変更禁止）  
**Compare:**

```text
Current Production Trigger
  = demo_ticket_optimizer_core.classify_world_line_type
  = research mirror TRIGGER_RULES R1–R8
vs
V44 World Trigger Specification
```

## Production 実装の事実（根拠）

`classify_world_line_type` の評価順（first-match）:

| Order | Condition（信号） | Return |
|---:|---|---|
| 1 | sfp↑ AND (phase↑ OR chaos↑ OR difficulty↑) | mixed |
| 2 | sfp↑ AND difficulty↑ | midupper |
| 3 | phase↑ | mixed |
| 4 | late_stop↑ AND sustained↑ | midhole |
| 5 | chaos↑ AND high_pace↑ | rank7 |
| 6 | chaos↑ AND difficulty↑ | bug |
| 7 | difficulty↑ | midupper |
| 8 | else | **core** |

使用 Signal: `short_field_pressure`, `phase_transition`, `late_stop`, `sustained`, `high_pace`, `race_leg_difficulty`, `chaos_score`  
**未使用（classify 内）:** `top_gap`, 能力差, 上位能力帯, 中位評価帯, 適性, レース格, 例外標識, multi_path 競合カウント

---

## 採点規則

各 World × 監査項目①–⑦:

| 判定 | 点 |
|---|---:|
| PASS | 1.0 |
| PARTIAL | 0.5 |
| FAIL | 0.0 |

`Compliance% = round(100 × sum(points) / 7)`

---

## ①–⑦ 監査要約

詳細は `v45-world-compliance.md` / `v45-production-vs-spec.md`。

| World | ① Positive | ② DEFAULT経路 | ③ Must | ④ Aux | ⑤ Forbidden回避 | ⑥ Logic Form | ⑦ 未充足時 | **Compliance** |
|---|---|---|---|---|---|---|---|---:|
| core | FAIL | FAIL（DEFAULT存在） | FAIL | FAIL | FAIL | FAIL | FAIL | **0%** |
| midupper | PARTIAL | PASS | FAIL | PARTIAL | FAIL | FAIL | PARTIAL | **36%** |
| midhole | PARTIAL | PASS | FAIL | PARTIAL | FAIL | FAIL | PARTIAL | **36%** |
| rank7 | PASS | PASS | PARTIAL | FAIL | PASS | PARTIAL | PARTIAL | **64%** |
| mixed | PARTIAL | PASS | FAIL | PARTIAL | FAIL | FAIL | PARTIAL | **36%** |
| bug | PARTIAL | PASS | FAIL | PARTIAL | PASS | FAIL | PARTIAL | **50%** |
| **平均** | — | — | — | — | — | — | — | **37%** |

---

## 構造ギャップ（World 横断）

| V44 仕様 | Production | Gap |
|---|---|---|
| Positive Match（全 World） | core のみ DEFAULT | core が最大乖離 |
| Must 欠落 ⇒ unsatisfied | 常にいずれかの World を返す | ⑦ 全体 FAIL/PARTIAL |
| Exclusion 後に Must | first-match 優先度のみ | Exclusion 仕様なし |
| 複数 Must 充足 ⇒ mixed | 単一 first-match | mixed 意味不一致 |
| Aux は Must 非置換 | Aux 相当が本体条件化 | midhole/midupper/bug |

---

## Guardrails honored

- 実装禁止 / 修正禁止 / Threshold 禁止 / Production 変更禁止
- 改善案なし（適合率の観測のみ）
