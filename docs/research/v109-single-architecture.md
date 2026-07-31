# Version109 — Single AI Architecture

**Date:** 2026-07-28  
**Status:** Consumer Development Design · Core **読取のみ**  
**Parents:** ADR-011 · V107 · V106 Single Contract · V109 Roadmap

---

## 一文

**Single AI は Core Platform v1 を消費し、Registry / Ticket / Presentation で Product を完成させる。**

---

## 1. 構成

```text
┌──────────────────────────────────────────────┐
│ Core Platform v1（FROZEN）                      │
│  Core API → CoreRaceSemanticPayload            │
└────────────────────┬─────────────────────────┘
                     │ read-only
                     ▼
┌──────────────────────────────────────────────┐
│ Single Consumer API (`consumer-api/single/v1`) │
│  + EXT(odds, budget) + flags_snapshot          │
└─────┬──────────────┬──────────────┬──────────┘
      ▼              ▼              ▼
 Decision        Ticket         Presentation
 Registry        Policy
 (policy_id)     (TicketPlan)   (structured±NL)
```

---

## 2. モジュール

### 2.1 Decision Registry

| 項目 | 定義 |
|---|---|
| 入力 | `world_id`, `near_miss.residual_class`, `near_world` |
| 出力 | `policy_id`, `registry_versions[]` |
| 正本 | V88 Decision Policy · V95 Residual Policy（表データ） |
| MUST NOT | CEW 書換 · 未知 World を勝手に新意味化（Legacy/保守フォールバック） |

### 2.2 Ticket Policy

| 項目 | 定義 |
|---|---|
| 入力 | `policy_id` + Core.prediction + EXT |
| 出力 | `TicketPlan`（券種・買い目案） |
| Flag | `W_DECISION_LAYER_ENABLED` / `W_DECISION_TICKET` |
| MUST NOT | Rank mutate · Near Miss の本採用 Ticket コピー · Affinity 自動 Skip |

### 2.3 Presentation

| 項目 | 定義 |
|---|---|
| 入力 | World, Exclusion, NM, Affinity, EC, Transition, Must Gaps, strategy_ref |
| 出力 | structured bundle + optional NL |
| Flag | `W_DECISION_EXPLAIN` / `W_CONSUMER_PRESENTATION_NL` |
| MUST NOT | EC を勝率表示 · NL を Core に要求 · MS-6 を Core へ逆流 |

### 2.4 Consumer API

| 項目 | 定義 |
|---|---|
| Schema | `consumer-api/single/v1` |
| Flag | `W_CONSUMER_SINGLE_ENABLED` |
| 契約 | V107 Consumer API · V106 S-CC-* |

---

## 3. Core 不足時の解決順序（MUST）

1. Presentation テンプレ / Registry 行 / EXT で足りるか  
2. Consumer DTO 拡張（Core 非逆流）  
3. 例外ゲート（Contract Violation / Semantic Gap / Compat Failure）— Version1 緊急修復のみ  
4. または **Version2 Platform Research** の正式開始（V1 安定運用と分離）  

---

## 4. 実装スコープ（本 Architecture が許可する範囲）

| 許可 | 禁止 |
|---|---|
| `app/decision/*` 拡張 · Consumer アダプタ新設 | PE / Trigger / World 定義変更 |
| Registry JSON/YAML 化 | Affinity/EC 定義変更 |
| Flag 配線（既定 OFF） | Evidence を Ticket 必須入力化 |

---

## Related

- `v109-consumer-api-integration.md`
- `v106-single-consumer-contract.md`
- ADR-008 · ADR-011
