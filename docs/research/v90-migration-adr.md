# Version90 — Migration ADR（Decision Layer）

**Status:** Accepted（Migration Plan） · **実行・実装: Not authorized**  
**Date:** 2026-07-28  
**Parent:** ADR-008  
**関連:** V78 Pilot Migration 思想 · V89 Decision Shadow

---

## Context

Decision Layer を導入しても Prediction を動かさない。  
移行は **Flag 段階**で行い、各段階で Prediction 非劣化を証明する。

---

## Decision — Migration Phases

### Phase M0 — Document Freeze（現在）

| 項目 | 内容 |
|---|---|
| 状態 | ADR-008 Accepted / 実装なし |
| Flag | 全て OFF（未実装でも設計上 OFF） |
| 出口条件 | 本 ADR + Responsibility Matrix レビュー完了 |

### Phase M1 — Shadow（研究継続可）

| 項目 | 内容 |
|---|---|
| 内容 | V89 型 OFF/ON 対照を定期実行 |
| Production | 非接続 |
| 出口条件 | Coverage / Explainability / PurchaseHit の再現、Rank audit PASS |

### Phase M2 — Flagged Staging（将来・要別承認）

| 項目 | 内容 |
|---|---|
| Flag | `W_DECISION_LAYER_ENABLED=true`（staging のみ） |
| サブフラグ | Explain → Pool → Risk → Ticket の順で段階 ON 推奨 |
| ゲート | Prediction Rank/Hit が Flag OFF と一致（許容差=0 を目標） |
| Rollback | 総スイッチ OFF |

### Phase M3 — Production Canary（将来・要別承認）

| 項目 | 内容 |
|---|---|
| 対象 | Ready World（rank7 / unsatisfied）のみ |
| Blocked | 常時 SKIP / デフォルト |
| 監視 | Ticket ROI、Skip 率、Coverage、苦情/説明監査 |
| Rollback | L0 Flag OFF（即時） |

### Phase M4 — Expansion（将来）

| 項目 | 内容 |
|---|---|
| midhole | Partial 解除後のみ Ticket 拡張 |
| その他 | 標本・Gate 再通過後 |

---

## Migration 不変条件

| ID | 条件 |
|---|---|
| M-I0 | Prediction Rank/Score は全 Phase で非変更 |
| M-I1 | World → PE Weight 経路を新設しない |
| M-I2 | Confidence 主エンジンは Global のまま（World Prior 単独本番化しない） |
| M-I3 | Decision Flag と PE Pilot Flag を同時に归因なしで ON にしない |
| M-I4 | Rollback は Prediction に副作用を残さない |

---

## Feature Flag 移行表

| Phase | LAYER | EXPLAIN | POOL | RISK | TICKET | CONF_DISPLAY |
|---|---|---|---|---|---|---|
| M0 | OFF | OFF | OFF | OFF | OFF | OFF |
| M1 Shadow | n/a | n/a | n/a | n/a | n/a | n/a |
| M2a | ON | ON | OFF | OFF | OFF | OFF |
| M2b | ON | ON | ON | OFF | OFF | OFF |
| M2c | ON | ON | ON | ON | OFF | OFF |
| M2d / M3 | ON | ON | ON | ON | ON | ON（任意） |

---

## Rollback Runbook（設計）

1. `W_DECISION_LAYER_ENABLED=false`
2. 購入/表示が Legacy デフォルトに戻ることを確認
3. Prediction 出力ハッシュまたは Rank 一致を確認
4. インシデント記録（Decision 側のみ）

---

## Authorization

| 行為 | 本 ADR |
|---|---|
| M0 文書 | **承認** |
| M1 Shadow 研究 | 研究 Decision で可 |
| M2+ 実装・Staging・Production | **未承認**（別 Decision 必須） |
