# Version109 — Win5 AI Architecture

**Date:** 2026-07-28  
**Status:** Consumer Development Design · Core **読取のみ**  
**Parents:** ADR-011 · V107 · V106 Win5 Contract · V109 Roadmap

---

## 一文

**Win5 AI は Core v1 Selector 上に Candidate / Coverage / Race Selection を積む。難易度スカラーは作らない。**

---

## 1. 構成

```text
┌──────────────────────────────────────────────┐
│ Core Platform v1（FROZEN）                      │
│  Core API（race ごと payload）                   │
└────────────────────┬─────────────────────────┘
                     │ read-only
                     ▼
┌──────────────────────────────────────────────┐
│ Win5 Consumer API (`consumer-api/win5/v1`)     │
│  race_ids[] + EXT(field_size, …)               │
└─────┬──────────────┬──────────────┬──────────┘
      ▼              ▼              ▼
 Candidate       Coverage        Race
 Expansion       Strategy        Selection
 (CandidateSet)  (CoveragePlan)  (include/reasons)
```

---

## 2. モジュール

### 2.1 Candidate Expansion

| 項目 | 定義 |
|---|---|
| 入力 | World/NM + ranks + V92 Pool 表 |
| 出力 | `CandidateSet`（公式順位配列は不変） |
| Flag | `W_CONSUMER_CANDIDATE_EXPAND` / `W_DECISION_POOL` |
| MUST NOT | Rank swap · Near Miss で本採用 Pool7 を無条件起動 |

### 2.2 Coverage Strategy

| 項目 | 定義 |
|---|---|
| 入力 | World/NM Risk プロファイル + EXT |
| 出力 | `CoveragePlan`（保険・分散・保守方針） |
| Flag | `W_CONSUMER_COVERAGE` / `W_DECISION_RISK` |
| MUST NOT | Affinity 単独で保険閾値（V97）· Ticket を Core に載せる |

### 2.3 Race Selection

| 項目 | 定義 |
|---|---|
| 入力 | World/NM/EC + EXT + Product ルール |
| 出力 | `include` + `reason_codes[]` |
| Flag | `W_CONSUMER_RACE_SELECT` |
| MUST NOT | `race_difficulty` Core/Semantic 新設 · EC 単独自動 Skip 確定（V101） |

### 2.4 Consumer API

| 項目 | 定義 |
|---|---|
| Schema | `consumer-api/win5/v1` |
| Flag | `W_CONSUMER_WIN5_ENABLED` |
| 契約 | V107 · V106 W-CC-* |

---

## 3. Single との関係

| 共有 | 非共有 |
|---|---|
| Core API 読取 · Registry キー空間 · Flag スナップショット | TicketPlan 形状 · Presentation NL（Win5 は監査 codes 優先可） |

推奨: Single Consumer API 安定後に Win5 本実装（Roadmap Track W）。

---

## 4. Core 不足時の解決順序（MUST）

1. Pool/Risk Registry · Product ルール · EXT  
2. Consumer DTO / reason_codes 拡張  
3. 例外ゲート（Contract Violation / Semantic Gap / Compat Failure）  
4. または **Version2 Platform Research** 正式開始（V1 と分離）  

---

## Related

- `v109-consumer-api-integration.md`
- `v106-win5-consumer-contract.md`
- ADR-011
