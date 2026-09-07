# Version109 — Consumer API Integration

**Date:** 2026-07-28  
**Status:** Integration Design · **Core 非改変** · Consumer 実装を許可する契約面  
**Parents:** ADR-011 · V107 Consumer API · V109 Architectures

---

## 1. 統合原則

| ID | 原則 |
|---|---|
| I0 | Core API は read-only。版 `core-semantic-payload/v1` |
| I1 | Consumer schema は独立（`single/v1` · `win5/v1`） |
| I2 | EXT は Consumer リクエスト/ストア。Core に埋め込まない |
| I3 | PROMOTE フィールドは `W_CORE_PAYLOAD_V103`（別 Gate） |
| I4 | 全レスポンスに `core_ref` + `flags_snapshot` + fingerprint |

---

## 2. 統合シーケンス（Single）

```text
Client → ConsumerSingleAPI
           │
           ├─(1) CoreAPI.get(race_id)     【読取】
           ├─(2) Registry.resolve(world, nm)
           ├─(3) optional TicketPolicy    【Decision Flag】
           ├─(4) optional Presentation    【Explain/NL Flag】
           └─(5) assemble ConsumerSingleResponse
```

欠落 PROMOTE（Flag OFF）時: Presentation は最小 structured。**Core を拡張して埋めない。**

---

## 3. 統合シーケンス（Win5）

```text
Client → ConsumerWin5API(race_ids)
           │
           ├─ for each race: CoreAPI.get
           ├─ CandidateExpansion?
           ├─ CoverageStrategy?
           ├─ RaceSelection?
           └─ assemble ConsumerWin5Response
```

---

## 4. 依存と実装単位（推奨パッケージ境界）

| パッケージ（論理） | 責務 | Core 依存 |
|---|---|---|
| `core_client` | Payload 取得・版検証 | 読取のみ |
| `decision_registry` | policy_id 解決 | world/nm キーのみ |
| `consumer_single` | Single DTO 組立 | core_client |
| `consumer_win5` | Win5 DTO 組立 | core_client |
| `presentation` | 説明 | core fields + registry |
| `ticket_policy` | TicketPlan | prediction + registry + EXT |
| `win5_candidate` / `coverage` / `selection` | Win5 三モジュール | 同上 |

物理パスは実装 Gate で既存 `app/decision/` 配下へ配置してよい（PE 非侵入）。

---

## 5. Flag 統合表

| Flag | Single | Win5 | Core |
|---|---|---|---|
| `W_CORE_PAYLOAD_V103` | PROMOTE 利用 | 同左 | serialize のみ（別 Gate） |
| `W_CONSUMER_SINGLE_ENABLED` | API ON | — | — |
| `W_CONSUMER_WIN5_ENABLED` | — | API ON | — |
| `W_DECISION_*` | Ticket/Explain/… | Pool/Risk 整合 | — |
| `W_CONSUMER_PRESENTATION_NL` | NL | 任意 | — |
| `W_CONSUMER_CANDIDATE_EXPAND` | — | ON | — |
| `W_CONSUMER_COVERAGE` | — | ON | — |
| `W_CONSUMER_RACE_SELECT` | — | ON | — |

既定: **全て OFF**。ON は Staging 承認後。

---

## 6. テスト観点（Consumer・非 Core）

| 観点 | 合格条件 |
|---|---|
| Rank 非劣化 | Consumer ON/OFF で公式 ranks 一致 |
| 逆流なし | Core payload 書込ゼロ |
| 禁止用途 | Affinity→Skip / EC→勝率 がコードパスに無い |
| 版 | `core_ref.schema == v1` |

---

## Related

- `v107-consumer-api.md`
- `v109-migration-plan.md`
