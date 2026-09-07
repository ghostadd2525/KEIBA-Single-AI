# W-S0 — Baseline Freeze（移行正本ロック）

**Date:** 2026-07-28  
**Stage:** Track W / V46 S0 / Version55  
**Production Decision:** **変更なし**  
**S1+:** 禁止（本 Stage の範囲外）

---

## Purpose

V46 W-S0: Legacy / Target / Gap を移行契約として固定する。  
Feature Flag を追加するが **未使用（OFF / legacy）**。  
Shadow 配線を準備するが **Dual-Eval は実行しない**。

---

## Locked triad

| Role | Authority | Location |
|---|---|---|
| **Legacy** | Production Trigger baseline | `demo_ticket_optimizer_core.classify_world_line_type` + research `TRIGGER_RULES` R1–R8 |
| **Target** | V44 World Trigger Specification | `docs/architecture/v44-world-trigger-specification.md` (+ Logic Form / Must / Aux / Forbidden) |
| **Gap** | V45 Compliance KPI | `docs/audit/v45-trigger-spec-gap.md`（Mean Compliance 37% / core 0%） |

Semantic meaning authority remains **V43**（Target Spec の上流）。

---

## Declarations

1. 以降の Stage は Legacy を **無断変更しない**。  
2. Production Decision の切替は **S6 Soft / S7 Cutover** のみ（別ゲート）。  
3. Pure Dual-Eval 開始は **S1**（本 Stage では禁止）。  
4. Prediction / PE / CE / AI / Signal 生成は本 Stage の対象外。

---

## Code landed in W-S0（decision-neutral）

| Artifact | Role |
|---|---|
| `ai_platform/core/world/trigger_migration_flags.py` | Flags default OFF / legacy |
| `ai_platform/core/world/trigger_shadow.py` | Shadow sink + freeze log prep |
| `ai_platform/core/world/__init__.py` | Post-classify observation hook（結果不変） |
| `app/research/w_s0_baseline_freeze.py` | 285R eval + Gate |

`classify_world_line_type` 本体の規則・閾値は **未変更**。

---

## PASS / FAIL

See `w-s0-gate.md` and `w-s0-285r-evaluation.md`.

---

*W-S0 Freeze lock document.*
