# V52 — Governance（View Adapter Feasibility）

**Date:** 2026-07-28  
**Subject:** Can ADR-050 migration rely on View Adapter alone (`CE → PredictionBundle`)?  
**Method:** Code + contract evidence (V52 feasibility / compatibility / projection)

---

## Scale Definitions

| Grade | Meaning |
|---|---|
| **A** | Adapterのみで実現可能 — 全対象 Consumer が CE→Bundle 一方向で充足 |
| **B** | 一部 Consumer で追加対応必要 — 大半は Adapter、例外のみ RaceData/Bet 等 |
| **C** | Adapterだけでは成立しない — 契約または主要 Consumer が CE 外情報に構造依存 |

---

## Verdict

# **C — Adapterだけでは成立しない**

---

## Evidence（硬）

### 1. 現行「Mapper」は View Adapter ではない

`prediction_response_to_bundle` の入力は `prediction_response`。  
`prediction_response` は `predict_ranking/confidence` **に加え** `build_bet_plan` / `build_bets` を含む（`single/prediction/__init__.py`）。

→ 今日動いている Product 経路は **CE View Adapter ではなく Product Assembly**。

### 2. Bundle 必須ブロックが CE に存在しない

| Bundle block | In CorePublicBundle? |
|---|---|
| `race_info`（date/venue/race_no/…） | **No**（`get_race` + catalog） |
| `betting_recommendations` | **No**（Bet Builder） |
| `schema_version` / product stamps | **No**（constants / Product） |

TypeScript 上 `race_info` / `evaluation` / `ai_confidence` / `explain` / `betting_recommendations` が Bundle インターフェースに並ぶ。  
CE だけでは型・実 Consumer の両方を満たせない。

### 3. 主要 Consumer が Bundle-only フィールドを参照

| Consumer | Non-CE dependency |
|---|---|
| GUI | mark, race_info, bets, explain |
| Functions / Kaoba | mark, race_info |
| Conversation | race_info, explain, ai_confidence |
| HTTP list / Mock | catalog / fixtures — CE 非経由 |
| Single / CLI | bets 段 |

「一部例外」ではなく **Product 主経路の複数系統** が同時に欠落情報に依存 → B ではなく **C**。

### 4. 一方向完全投影が不成立

Projection audit: ranking/world/confidence 部分集合のみ one-way。  
完全 Bundle は **追加生成必須** = pure Adapter の定義を破る。

### 5. Adapter で解ける問題は局所

解ける: `evaluation.world=None` の修正、runners への Rank/Confidence 写像。  
解けない: Mock、list projection、bets、完全 race_info、履歴 Challenge、Single 同等 CLI。

局所修正可能性があっても、**移行戦略としての Adapter 単体**は不成立。

---

## Why not A / B

| Grade | Reject |
|---|---|
| **A** | 全 Consumer Yes ではない; Bundle 契約が CE 超集合 |
| **B** | 「大半 OK・一部追加」は過大評価。HTTP detail / GUI / Functions / Conversation / Single が同時に追加依存。追加なしでは主経路が壊れる |

B が成立するには、事前に Bundle 契約から bets/race_info を外すか、Adapter 定義に RaceData+BetBuilder を含める **再定義** が必要。それは本監査の Adapter 定義外であり、別 ADR 対象。

---

## What this does *not* mean

- Dual-publish が無意味 → **否**（V51 の段階的公開には有効）  
- CE を Canonical にする ADR-050 が誤り → **否**（契約の正本問題は別）  
- Assembly Pipeline（CE+RaceData+BetBuilder→Bundle）が不可能 → **未監査**（本フェーズ外）

本判定は狭い命題のみ:

> **Pure View Adapter alone cannot migrate/satisfy all Consumers.**

---

## Decision Gate（参照）

```
【Decision】※分析のみ
Action Type: View Adapter Feasibility Audit
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Treating Adapter-alone as migration plan = High (hidden RaceData/Bet/Mock deps)
Expected Next Action: If migration continues, design Product Assembly + Dual-publish (new Decision) — do not implement Adapter-only cutover
```

---

## Grade chain

| Phase | Topic | Grade |
|---|---|---|
| V50 | ADR-050 Canonical = CE | Accepted (design) |
| V51 | Implementation impact scope | C（広範囲） |
| **V52** | **Adapter-alone feasibility** | **C（成立しない）** |

---

*V52 Governance — research only. Grade C.*
