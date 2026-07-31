# Version107 — Consumer API（設計）

**Date:** 2026-07-28  
**Status:** Design only · **実装禁止**  
**Parent:** ADR-011  
**Locks:** Core 意味・Contract 非変更。serialize / アダプタ配線のみが将来の実装範囲。

---

## 1. Core API

### 1.1 契約

| 項目 | 定義 |
|---|---|
| 名称 | Core Platform API |
| 语义 | read-only |
| Schema | `core-semantic-payload/v1`（V103 design を製品版名に昇格する **設計名**。実装未承認） |
| 入力 | `race_id`（必須）· 任意 `as_of` |
| 出力 | `CoreRaceSemanticPayload`（V103） |
| エラー | 未知 race / schema 不一致 / Flag OFF 時は legacy 最小 payload または 404 方針（実装時決定・意味非変更） |

### 1.2 Payload Mapping（Core）

| 論理フィールド | ソース | Flag |
|---|---|---|
| prediction.ranks/scores/top1 | 既存 prediction bundle | 常時（読取） |
| world_id / decision_trace / transition / trigger_path | 既存 CEW dual-eval | 常時（読取） |
| near_miss / affinity / exclusion_reasons / explanation_confidence | V103 PROMOTE 導出 | `W_CORE_PAYLOAD_V103` |
| expected_strategy_ref | world_id → V75 レジストリキー | 常時（参照のみ） |

**MUST NOT:** Ticket, Skip, stake, natural_language_why, race_difficulty, candidate_count。

### 1.3 版ルール

| 変更 | 版 |
|---|---|
| フィールド追加（導出 serialize） | minor（別 Gate） |
| 意味再定義 | **禁止**（ADR-009/010 期間） |
| 削除 | major + Consumer 移行完了後のみ |

---

## 2. Consumer API — Single AI

### 2.1 エンドポイント形状（論理）

```text
ConsumerSingleRequest
  race_id: string
  options: {
    include_tickets: bool
    include_presentation: bool
    locale: string
  }

ConsumerSingleResponse
  schema: "consumer-api/single/v1"
  core_ref: { schema, race_id, payload_fingerprint }
  registry: { policy_id, strategy_id, registry_versions[] }
  ticket: null | TicketPlan          # Decision 出力
  presentation: null | PresentationBundle
  flags_snapshot: { ... }
  warnings: string[]                 # 例: low_EC_explain_incomplete
```

### 2.2 Payload Mapping（Single）

| Consumer フィールド | 由来 | 層 |
|---|---|---|
| policy_id | Core.world_id + near_miss → V88/V95 Registry | Decision Registry |
| TicketPlan | policy_id + Core.prediction + EXT(odds,budget) | Ticket Policy |
| PresentationBundle.structured | Core Exclusion/NM/Affinity/EC/Transition/MustGaps | Presentation（構造） |
| PresentationBundle.prose | テンプレ + structured | Presentation（NL） |
| warnings[] | EC 低 / PROVISIONAL World 等 | Presentation / Risk 表示 |

### 2.3 Feature Flags

| Flag | 効果 |
|---|---|
| `W_CONSUMER_SINGLE_ENABLED` | 本 API 有効 |
| `W_DECISION_TICKET` | ticket 非 null 可（ADR-008） |
| `W_DECISION_EXPLAIN` / `W_CONSUMER_PRESENTATION_NL` | 説明・NL |
| `W_CORE_PAYLOAD_V103` | PROMOTE フィールド利用 |

OFF 時: legacy 説明/デフォルト券（既存製品経路）。Core 非改変。

---

## 3. Consumer API — Win5 AI

### 3.1 エンドポイント形状（論理）

```text
ConsumerWin5Request
  race_ids: string[]                 # カードまたは候補日
  options: {
    expand_candidates: bool
    coverage: bool
    race_select: bool
  }

ConsumerWin5Response
  schema: "consumer-api/win5/v1"
  races: [{
    race_id
    core_ref
    candidates: null | CandidateSet  # 順位配列は不変。表示/採用集合のみ
    coverage: null | CoveragePlan    # 保険・分散方針（券は Decision）
    selection: null | { include: bool, reason_codes[] }
  }]
  flags_snapshot: { ... }
```

### 3.2 Payload Mapping（Win5）

| Consumer フィールド | 由来 | 層 |
|---|---|---|
| CandidateSet.size / members | World/NM → V92 Pool 表 + ranks | Candidate Expansion |
| CoveragePlan | V95 Risk profile + EXT | Coverage Strategy |
| selection.include | Product ルール + World/NM + EC警告 + EXT(field_size) | Race Selection（KD） |
| reason_codes | Exclusion / NM class / EC axes（勝率化禁止） | 監査 |

**MUST NOT:** Affinity 単独で include=false を正当化して再最適化（V97）。  
**MUST NOT:** EC 単独閾値で Skip を自動確定（V101 — 別契約なし）。

### 3.3 Feature Flags

| Flag | 効果 |
|---|---|
| `W_CONSUMER_WIN5_ENABLED` | 本 API 有効 |
| `W_CONSUMER_CANDIDATE_EXPAND` | candidates 生成 |
| `W_CONSUMER_COVERAGE` | coverage 生成 |
| `W_CONSUMER_RACE_SELECT` | selection 生成 |
| `W_CORE_PAYLOAD_V103` | PROMOTE 利用 |
| `W_DECISION_POOL` / `W_DECISION_RISK` | ADR-008 と整合する表示/抑制 |

---

## 4. 共通規則

| ID | 規則 |
|---|---|
| CA-0 | Consumer は Core を mutate しない |
| CA-1 | Core schema と Consumer schema は独立版 |
| CA-2 | EXT（odds, budget, field_size）はリクエストまたは Product ストアから。Core に埋め込まない |
| CA-3 | Evidence 種別をレスポンスに載せる場合は V105 ラベル必須（EV-P/S/D） |
| CA-4 | fingerprint / flags_snapshot を必ず返し再現可能にする |

---

## Related

- ADR-011
- `v107-architecture-diagram.md`
- `v103-payload-contract.md`
- `v106-payload-requirement-matrix.md`
