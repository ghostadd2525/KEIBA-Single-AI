# Version109 Phase C7 — Operational Guideline（Canary）

**Date:** 2026-07-29  
**Scope:** Single AI Version1 Consumer · Flag ベース運用  
**前提:** C6 Staging PASS · Core Version1 凍結

---

## 1. 役割境界（Canary 中も不変）

| 層 | やってよい | やってはいけない |
|---|---|---|
| Core | read-only 供給 | 意味変更・書込 |
| Consumer | Presentation / Ticket 組立 | Rank 改変・Reason 新造 |
| Decision Service | Compose | Reasoner 化・Ticket 再発明 |

---

## 2. Feature Flag

| Flag | 既定 | Canary 時 |
|---|---|---|
| `W_CONSUMER_SINGLE_ENABLED` | OFF | 対象環境のみ ON |
| `W_CONSUMER_PRESENTATION_ENABLED` | OFF | 段階 ON 可 |
| `W_CONSUMER_TICKET_ENABLED` | OFF | Presentation 安定後 |
| `W_CORE_PAYLOAD_V103` | OFF | 別 Gate |

**Rollback:** 全 `W_CONSUMER_*` OFF → 即時 LEGACY（C6 実証済み）。

---

## 3. Logging（必須フィールド）

毎回出力すること:

- Consumer: event / mode / flags_snapshot  
- Core: race_id / payload_fingerprint / mutated=false  
- Version: `version` ブロック（PLATFORM-V1-CONTRACT）  
- Feature Flag: `snapshot_all_flags()`

---

## 4. Monitoring（Canary 開始前に埋める GAP）

| 指標 | 用途 |
|---|---|
| Consumer 例外率 vs Legacy | 自動 Rollback 判断 |
| p95 latency delta | C6 予算の本番拡張 |
| Flag snapshot drift | 意図せぬ ON 検知 |
| fingerprint mismatch count | Core 改変事故検知（0 であるべき） |

---

## 5. 障害時手順

1. `W_CONSUMER_*` すべて OFF  
2. Legacy 応答を確認（presentation/ticket null）  
3. fingerprint / policy_id が Staging 基準と一致するか確認  
4. 事後: Consumer ログのみ解析（Core を触らない）

---

## 6. 禁止

Prediction / Semantic / Core / Contract / Feature 追加で「直す」こと。  
不足は Checklist GAP を別 Gate で閉じる。
