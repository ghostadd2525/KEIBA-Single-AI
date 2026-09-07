# ADR-008 — Decision Layer（World 専属）

**Status:** Accepted（Architecture） · **Implementation: M1 Shadow authorized (V91)** · Production **not** authorized  
**Date:** 2026-07-28  
**Version tag:** Version90（ADR） / Version91（M1 Shadow）  
**Deciders:** Research Arc V43–V89 → Architecture · V91 M1 Shadow  
**Related:** ADR-003（Prediction Read-Only） · ADR-009（AI Core Completeness） · `docs/architecture/v32-world-adr.md` · V88/V89 Decision Policy/Shadow · V91 M1

---

## Context

V43–V89 の実証により、次が確定した。

| 主張 | 結果 | 根拠 |
|---|---|---|
| World で Prediction 順位/Score を改善 | **不成立** | V80（Strategy Hit−133）ほか |
| World / Interaction で Confidence 主改善 | **不成立** | V84（constant-shift 主因） |
| World Prior が Global Calibration より有意 | **未証明** | V87 INCONCLUSIVE |
| World を Decision Layer に置く | **有望** | V88 設計 · V89 Shadow（Coverage/PurchaseHit↑、Rank 非変更） |

旧 Implicit 契約「World = 勝ち筋 → PE 重み」は、Prediction / Calibration では実証失敗した。  
World の正式責務を **Decision Layer 専属**へ再配置する。

---

## Decision

### 層アーキテクチャ（確定）

```text
┌─────────────────────────────────────────────┐
│ Prediction Engine（World 非依存）              │
│  Rank / Score の唯一の生成者                   │
└──────────────────┬──────────────────────────┘
                   │ read-only ranks/scores
                   ▼
┌─────────────────────────────────────────────┐
│ Confidence（Global Calibration）             │
│  p_base 再スケール等。World を主エンジンにしない │
└──────────────────┬──────────────────────────┘
                   │ calibrated display values（任意）
                   ▼
┌─────────────────────────────────────────────┐
│ World Label（CEW / Trigger 出力・読取）         │
│  ※本 ADR は Trigger 契約を変更しない            │
└──────────────────┬──────────────────────────┘
                   │ world_id only
                   ▼
┌─────────────────────────────────────────────┐
│ Decision Layer（World 専属）                   │
│  Ticket · Pool · Explanation · Risk           │
│  （+ Confidence 表示ポリシー。順位非連動）        │
└─────────────────────────────────────────────┘
```

### 責務（MUST）

| 層 | MUST | MUST NOT |
|---|---|---|
| **Prediction Engine** | Rank/Score を生成 | World 係数で順位変更 · Decision 券種の生成 |
| **Confidence** | Global Calibration を基本とする | World Prior を未証明のまま主エンジン化 |
| **World** | Decision の Selector 入力 | PE 内部の加点表 · Rank swap の根拠 |
| **Decision Layer** | Ticket/Pool/Explanation/Risk（＋表示 Confidence） | Prediction Rank/Score の改変 |

### Owner

| コンポーネント | Owner | 備考 |
|---|---|---|
| Prediction Engine | Prediction / PE チーム | ADR-003 と整合。World 非依存 |
| Confidence（Global） | PE / Calibration Owner | World 非依存が既定 |
| World Label（Trigger→CEW） | World / Trigger Owner | 本 ADR はラベル**利用**側。生成契約は既存 ADR |
| Decision Layer | **Decision Owner（新設・論理）** | Ticket/Pool/Explain/Risk の唯一の変更点 |
| Feature Flags | Platform / Ops | 下記フラグ。Production 既定 OFF |

### Contract（Decision Layer）

| ID | 規則 |
|---|---|
| DL-C0 | Decision の入力は `(official_prediction_read_only, world_label, optional_global_confidence)` |
| DL-C1 | Decision は **Rank 配列・Score 配列を mutate しない**（ADR-003 拡張） |
| DL-C2 | World は Decision のみを切替える。PE 呼び出しに World weight を渡さない |
| DL-C3 | Ticket / Pool / Explanation / Risk の変更は Decision モジュール境界内に閉じる |
| DL-C4 | Confidence **表示**ポリシーは Decision 可。Confidence を再計算して **再ランキング**してはならない |
| DL-C5 | Blocked / PROVISIONAL World は自動 Ticket を禁止（見送りまたはデフォルト） |
| DL-C6 | `unsatisfied` は勝ち筋 Ticket 化禁止（Residual） |
| DL-C7 | Production 接続は **Feature Flag 既定 OFF** かつ別 Decision 承認後のみ |

### Rollback

| レベル | 操作 | 効果 |
|---|---|---|
| L0 Flag OFF | `W_DECISION_LAYER_ENABLED=false` | Decision 全バイパス → Legacy デフォルト Ticket/説明 |
| L1 部分 OFF | サブフラグ OFF | Ticket のみ戻す等 |
| L2 コード Rollback | Decision アダプタ削除/未デプロイ | Prediction に影響しない（非侵入設計が前提） |

Rollback 成功条件: Prediction Hit/Rank 分布が Flag OFF 前後で一致（許容誤差ゼロを目標）。

### Feature Flag（V91 コード化・既定 OFF）

| Flag | 既定 | 意味 |
|---|---|---|
| `W_DECISION_LAYER_ENABLED` | **OFF** | Decision Layer 総スイッチ |
| `W_DECISION_TICKET` | OFF | Ticket Strategy |
| `W_DECISION_POOL` | OFF | Candidate Pool 表示拡張 |
| `W_DECISION_EXPLAIN` | OFF | Explanation 切替 |
| `W_DECISION_RISK` | OFF | Risk 表示・見送り |
| `W_DECISION_CONF_DISPLAY` | OFF | Confidence 表示ポリシー（再ランク禁止） |

実装: `app/decision/flags.py`  
依存: サブフラグは総スイッチ ON 時のみ有効。  
**禁止:** PE Pilot フラグと Decision フラグの結合（归因不能）。

### Migration

別紙: `docs/research/v90-migration-adr.md`（および本リポジトリ `docs/adr` 索引）。  
原則: Shadow → Flagged Staging → Production。各段階で Prediction 非劣化ゲート。

---

## Consequences

### Positive

- World の语义価値を、実証済みの Decision 軸（V89 Coverage/PurchaseHit）に接続できる
- Prediction / ADR-003 を侵食しない
- Flag OFF で即時 Rollback 可能

### Negative / Risks

- Decision と PE の二重管理コスト
- Ticket 分散は ROI を下げ得る（V89: ROI 微減トレードオフ）
- World Label 品質に Decision が依存（Trigger 契約は別管理）

### Rejected alternatives

| 案 | 却下理由 |
|---|---|
| World → PE Weight | V80 失敗 |
| World → Confidence 主エンジン | V84/V87 |
| World → Rank Swap 本番 | Prediction 非依存原則違反・未承認 |
| Decision なしで World 廃止 | Explanation/语义・V89 価値を捨てる |

---

## Implementation authorization

| Phase | Status |
|---|---|
| Architecture（本 ADR） | **Accepted / Frozen** |
| M1 Shadow（V91） | **Authorized & implemented**（`app/decision/` + Dual Shadow）。Production 非接続 |
| M2+ Staging / Production | **Not authorized**（別 Decision 必須） |

**Architecture を再設計しない。World を PE に戻さない。Prediction を変更しない。**

---

## Evidence index

| 領域 | 版 |
|---|---|
| Semantic / CEW | V43, V72–V73 |
| Strategy / Ready | V74–V78 |
| Attribution / Interaction | V79–V82 |
| Confidence / Prior | V83–V87 |
| Decision | V88–V89 |
