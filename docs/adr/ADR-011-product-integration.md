# ADR-011 — Product Integration（Core Platform → Single / Win5）

**Status:** Accepted（Architecture Design） · **Platform Version1 Contract（FROZEN · V109）** · Consumer 実装は V109 で認可  
**Date:** 2026-07-28  
**Version tag:** Version107  
**Parents:** ADR-003 · ADR-008 · ADR-009 · ADR-010 · V103 · V105 · V106  
**Locks:** Prediction / World / Near Miss / Affinity / Explanation Confidence / Core Contract / Evidence Governance — **変更禁止**  
**凍結:** `docs/adr/PLATFORM-V1-CONTRACT.md` — 境界改訂は例外三条件の証明後のみ。Consumer 実装は契約内で進行。

---

## Context

V106 により Consumer Readiness は **PARTIAL_READY**、**GAP-SEM = 0** と確定した。  
不足は Core 意味ではなく **配線（GAP-WIRE）・Decision Registry（GAP-REG）・Market/Race Card（GAP-EXT）** である。

混同リスク:

| 誤解 | 問題 |
|---|---|
| Core を Single/Win5 ごとに改変する | Platform 固定（ADR-009）に反する |
| Consumer 不足を新 Semantic で埋める | V103/V106 禁止 |
| Core API に Ticket/Skip を載せる | V103 PCS-7 |
| Evidence（Miss）を Consumer 入力の正本にする | V105 混線禁止 |

---

## Decision

### 1. Core は Product Platform（MUST）

```text
┌─────────────────────────────────────────────┐
│ Core Platform（固定）                         │
│  Prediction Rank/Score（読取）                │
│  World / Trace / Transition                   │
│  Near Miss / Affinity / Exclusion / EC        │
│  ※ Ticket · Skip · stake · 自然文 を出さない   │
└───────────────────┬─────────────────────────┘
                    │ Core API（read-only payload）
                    ▼
┌─────────────────────────────────────────────┐
│ Consumer API（Single / Win5 アダプタ）         │
│  + Decision Registry / Market / Race Card     │
└───────────────────┬─────────────────────────┘
          ┌─────────┴─────────┐
          ▼                   ▼
   Single AI Product     Win5 AI Product
```

Core の意味・Contract・Evidence Governance は **Product 統合でも改変しない**。

### 2. 層責務（MUST）

| 層 | MUST | MUST NOT |
|---|---|---|
| **Core Platform** | V103 `CoreRaceSemanticPayload` を版付きで供給 | Ticket/保険/候補数定数/難易度スカラー/NL why を新造 |
| **Consumer API** | Core＋EXT＋Registry を合成し Product DTO を返す | Core フィールドを書き換え・CEW 改変 |
| **Single Product** | Decision Registry / Ticket Policy / Presentation | Affinity→自動 Skip; EC→勝率表示 |
| **Win5 Product** | Candidate Expansion / Coverage Strategy / Race Selection | Near Miss Positive Ticket 化; difficulty Semantic 追加 |
| **Evidence** | V105 分類を維持（EV-P/S/D 分離） | Miss を Semantic 昇格に使う |

### 3. Single AI 統合対象（設計）

| モジュール | 入力 | 出力 | 根拠 |
|---|---|---|---|
| **Decision Registry** | `world_id`, Near Miss Class / near_world | policy_id（V88/V95 表） | V106 S-CC; GAP-REG |
| **Ticket Policy** | policy_id + prediction ranks + EXT(odds/budget) | ticket plan（券種・買い目案） | ADR-008; PCS-7（Core 外） |
| **Presentation** | World, Exclusion, NM, Affinity, EC, Transition, Must Gaps + strategy_ref | 説明文・警告（NL は本層） | V103 MS-6; ADR-010 |

### 4. Win5 AI 統合対象（設計）

| モジュール | 入力 | 出力 | 根拠 |
|---|---|---|---|
| **Candidate Expansion** | World/NM + ranks + Registry(PoolN) | candidate set（順位不変） | V88 Pool; V92 TopK/PoolN; V106 W-CC-1 |
| **Coverage Strategy** | World/NM Risk profile + EXT | 保険・分散・保守カバレッジ案 | V95 Risk; V106 保険=Decision |
| **Race Selection** | EC（説明確定度）+ World/NM + EXT(field_size 等) + Product ルール | 採用/見送りレース集合 | V106 難易度=KEEP_DERIVED; V101 EC≠自動 Skip 単独閾値 |

### 5. API 境界（MUST）

| API | Owner | 契約 |
|---|---|---|
| **Core API** | Core Platform | `GET` 相当の read-only Semantic Payload。版: `core-semantic-payload/*` |
| **Consumer API** | Single / Win5 各 Product | Core を呼び、Registry+EXT を合成。版: `consumer-api/single/*` · `consumer-api/win5/*` |

詳細: `docs/research/v107-consumer-api.md`

### 6. Versioning（MUST）

| 対象 | 規則 |
|---|---|
| Core schema | 破壊的変更はメジャー。意味変更は **禁止**（本 ADR 期間）。フィールド追加のみ別 Gate |
| Consumer DTO | Core と独立版。Consumer 独自フィールドは Core に逆流させない |
| Registry | `v75-expected-strategy` / `v88-decision-policy` / `v95-residual-policy` / `v92-pool` を **参照キー**で固定 |

### 7. Feature Flags（設計・既定 OFF）

既存 ADR-008 フラグを維持し、統合用を **追加設計**する（実装は別承認）:

| Flag | 既定 | 意味 |
|---|---|---|
| `W_DECISION_LAYER_ENABLED` ほか | OFF | ADR-008 既存（変更しない） |
| `W_CORE_PAYLOAD_V103` | OFF | PROMOTE フィールド serialize 公開 |
| `W_CONSUMER_SINGLE_ENABLED` | OFF | Single Consumer API 経路 |
| `W_CONSUMER_WIN5_ENABLED` | OFF | Win5 Consumer API 経路 |
| `W_CONSUMER_PRESENTATION_NL` | OFF | Presentation 自然文生成 |
| `W_CONSUMER_CANDIDATE_EXPAND` | OFF | Win5 Candidate Expansion |
| `W_CONSUMER_COVERAGE` | OFF | Win5 Coverage Strategy |
| `W_CONSUMER_RACE_SELECT` | OFF | Win5 Race Selection |

**禁止:** PE Pilot Flag と本系統を归因なし同時 ON（ADR-008 M-I3 継承）。

### 8. Migration

`docs/research/v107-migration-plan.md`（V90 Decision Migration と並走・非干渉）。

---

## Consequences

### Positive

- Core Platform 固定のまま Product 利用経路が明確化  
- V106 PARTIAL_READY のギャップを正しい層で解消する設計  
- Evidence / Semantic / Decision の混線を API 境界で防止  

### Negative / Trade-off

- Consumer API・Registry の運用コスト  
- Flag が増える（既定 OFF で緩和）  

### Rollback

| レベル | 操作 |
|---|---|
| L0 | 全 `W_CONSUMER_*` / `W_CORE_PAYLOAD_V103` OFF |
| L1 | ADR-008 Decision フラグ OFF（既存） |
| L2 | Consumer アダプタ未デプロイ — Core / Prediction 非影響 |

---

## Related

- `docs/research/v107-consumer-api.md`
- `docs/research/v107-architecture-diagram.md`
- `docs/research/v107-migration-plan.md`
- `docs/research/v107-governance.md`
- ADR-008 · ADR-009 · ADR-010 · V103 · V105 · V106
