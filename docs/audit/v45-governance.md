# Version45 Governance — Trigger Specification Gap Audit

## Verdict

**Production ↔ V44 Compliance: LOW**  
**Mean Specification Compliance: 37%**  
**Structural finding: core = 0%（DEFAULT のみ）が最大乖離**

本フェーズは適合率の観測のみ。実装・修正は行わない。

---

## Compliance Summary

| World | Compliance |
|---|---:|
| rank7_world | 64% |
| bug_world | 50% |
| midupper_world | 36% |
| midhole_world | 36% |
| mixed_world | 36% |
| core_world | **0%** |
| **平均** | **37%** |

---

## Key Evidence

1. Production `classify_world_line_type` は first-match + 最終 `return "core_world"`（DEFAULT）。
2. V44 Must の多数（top_gap、能力帯、適性、中位帯、multi_path、exception_flag）は classify 内で **未使用**。
3. V44 Forbidden に抵触する経路が実在: core DEFAULT、midupper=difficulty のみ、mixed=phase のみ、midhole=late∧sust 本体。
4. V44 未充足 = unsatisfied に対し、Production 未充足 = core（V41/V42 と整合）。

---

## Relation to prior versions

| Version | 寄与 |
|---|---|
| V43 | Semantic Contract |
| V44 | Trigger Specification（比較正本） |
| V41/V42 | core DEFAULT / 意味乖離の先行証拠 |
| **V45** | **Production の仕様適合率を定量化** |

---

## What this phase did NOT do

- 実装 / 修正 / Threshold 変更
- Production / Trigger / Signal 変更
- 改善提案

---

## Artifacts

- `docs/audit/v45-trigger-spec-gap.md`
- `docs/audit/v45-world-compliance.md`
- `docs/audit/v45-production-vs-spec.md`
- `docs/audit/v45-governance.md`

## Expected Next Action

適合率 37%（core 0%）を前提にした次方針の指示待ち。本監査はここで停止する。
