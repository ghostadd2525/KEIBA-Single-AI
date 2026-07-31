# Version33 — World Input Contract (Definition)

**Status:** Defined (design only — **not implemented**)  
**Date:** 2026-07-27  
**Parent ADR:** `docs/architecture/v32-world-adr.md` (P4 accepted)  
**Scope:** World が必要とする Signal 契約の定義のみ。実装・Trigger/World/CSV/Prediction/ADR 変更禁止。

---

## Purpose

World は **AI 最上流の勝ち筋分類**である。  
その入力は「Feature CSV の列数」ではなく、本契約が定める **Signal 集合**である。

```text
[Signal Service — future binding]
        │
        ▼
 World Input Contract   ← 本ドキュメントが正本
        │
        ▼
 World Trigger / WorldClassifier
        │
        ▼
 SubWorld / Role / Pool / Purchase
```

Production と Research は **同一の World Input Contract** を共有する（V32: P3 却下）。

---

## Contract layers

| Layer | Role | Examples |
|-------|------|----------|
| **L0 Prerequisite** | 設計 difficulty / chaos 等の原材料 | `win5_leg`, `style_entropy`, `pace_collapse_risk`, `horse_count`, style counts |
| **L1 Primary** | Trigger が直接読む（または同等） | `race_leg_difficulty`, `chaos_score`, `short_field_pressure` |
| **L2 Derived** | meta/candidate から Trigger 内で合成 | `phase_transition`, `late_stop`, `sustained`, `high_pace`, `world_line_score` |
| **L3 Observability** | 分類本体ではないが契約監査に必要 | component `leg_*`, Research aliases |

本契約の **必須充足対象**は主に **L1 + L2 の入力前提（L0 のうち設計必須）**。  
L2 の合成式自体は現行 Trigger 実装の観測仕様であり、本フェーズでは変更しない。

---

## Canonical naming

| Contract name (short) | Canonical key | Notes |
|-----------------------|---------------|-------|
| `difficulty` | `race_leg_difficulty` | Research alias `difficulty` は同一信号 |
| `chaos` | `chaos_score` | |
| `field_pressure` | `short_field_pressure` | Trigger 直接。pace の `leg_field_pressure` は L0 |
| `phase` | `phase_transition` | L2 derived |
| `late_stop` | `late_stop` | from `late_stop_risk_score` |
| `sustained` | `sustained` | from `sustained_run_possible_score` |
| `high_pace` | `high_pace` | L2 composite（collapse / high_pace_score / pace fit） |
| `pace_collapse` | `pace_collapse_risk` | L0/L1 meta；`*_v2` は未契約別名 |
| `style_entropy` | `style_entropy` | L0 |
| `world_line` | `world_line_score` + component set | L2 bundle |

---

## Design principles

1. **Signal 正本** — 列数（116/72）は Transport 詳細。  
2. **単一真理** — Production = Research 同一契約。  
3. **DEFAULT ≠ World policy** — 欠落フォールバックの恒常化を World 仕様として認めない（V32）。  
4. **欠落は明示** — Required 信号が欠ける場合、契約上は *unsatisfied*（実装の挙動変更は本フェーズ対象外）。  
5. **chaos は契約内** — 現状パイプライン断絶（V26）は既知。契約上は Required；修復は別実装承認。

---

## Document index

| Doc | Content |
|-----|---------|
| `v33-world-input-contract.md` | 本ファイル（契約概要） |
| `v33-signal-contract.md` | 各 Signal の型・値域・必須・DEFAULT |
| `v33-signal-ownership.md` | Owner / Producer / Transport / Consumer |
| `v33-default-policy.md` | DEFAULT 可否ポリシー |

## Guardrails

- Contract Definition only. No implementation.
