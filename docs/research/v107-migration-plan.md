# Version107 — Migration Plan（Product Integration）

**Date:** 2026-07-28  
**Status:** Design only · **実行・実装: Not authorized**  
**Parent:** ADR-011  
**並走:** V90 Decision Layer Migration（非干渉・フラグ分離）

---

## 原則

| ID | 条件 |
|---|---|
| PI-I0 | Prediction Rank/Score 非変更（全 Phase） |
| PI-I1 | World / Near Miss / Affinity / EC **定義**非変更 |
| PI-I2 | Core Contract / Evidence Governance 非変更 |
| PI-I3 | 新 Semantic / Feature で Gap を埋めない（V106） |
| PI-I4 | Rollback は Consumer/Core-payload Flag OFF のみ。PE 副作用なし |
| PI-I5 | Decision Flag と PE Pilot を归因なし同時 ON にしない（ADR-008 継承） |

---

## Phases

### P0 — Document Freeze（現在）

| 項目 | 内容 |
|---|---|
| 状態 | ADR-011 Accepted（設計）/ 実装なし |
| Flag | 全て設計上 OFF |
| 出口 | ADR-011 + Consumer API + Diagram + 本票レビュー |

### P1 — Core Payload Shadow Emit

| 項目 | 内容 |
|---|---|
| 内容 | V103 PROMOTE の **Shadow serialize**（研究/ログ）。Product API 非公開可 |
| Flag | `W_CORE_PAYLOAD_V103` は staging/shadow のみ検討 |
| 出口 | fingerprint 再現・意味非変更監査 PASS |
| 禁止 | Trigger/Logic 変更 |

### P2 — Consumer API Shadow（Single → Win5）

| 項目 | 内容 |
|---|---|
| 順 | Presentation 構造化 → Single Registry 解決 → Ticket（Decision Flag 依存）→ Win5 Candidate → Coverage → Race Select |
| Production | 非接続 |
| 出口 | V106 契約（S-CC / W-CC）準拠の Shadow 差分レポート |

### P3 — Flagged Staging

| 項目 | 内容 |
|---|---|
| Flag | `W_CONSUMER_SINGLE_ENABLED` を staging ON（説明優先） |
| 次 | `W_CORE_PAYLOAD_V103` → Presentation NL → Ticket（`W_DECISION_*`） |
| Win5 | Single 安定後に `W_CONSUMER_WIN5_*` 段階 ON |
| ゲート | Rank/Hit 分布が Flag OFF と一致（目標差 0） |

### P4 — Production Canary

| 項目 | 内容 |
|---|---|
| 対象 | Ready 経路・説明系を先行。Ticket/Coverage は別承認 |
| 監視 | 説明監査・Flag スナップショット・Consumer schema 版 |
| Rollback | L0 全 Consumer/Core-payload Flag OFF |

### P5 — Expansion

| 項目 | 内容 |
|---|---|
| Win5 Race Selection / Coverage | Canary 指標と V95/V97 制約再確認後 |
| Registry 版上げ | Consumer minor。Core 意味不変 |

---

## Flag 移行表（設計）

| Phase | CORE_V103 | SINGLE | WIN5 | PRESENTATION_NL | CANDIDATE | COVERAGE | RACE_SELECT |
|---|---|---|---|---|---|---|---|
| P0 | OFF | OFF | OFF | OFF | OFF | OFF | OFF |
| P1 Shadow | shadow | OFF | OFF | OFF | OFF | OFF | OFF |
| P2 Shadow | ON* | shadow | shadow | shadow | shadow | shadow | shadow |
| P3a Staging | ON | ON | OFF | ON | OFF | OFF | OFF |
| P3b Staging | ON | ON | ON | ON | ON | OFF | OFF |
| P3c Staging | ON | ON | ON | ON | ON | ON | ON |
| P4 Canary | 承認後 | 段階 | 段階 | 段階 | 段階 | 段階 | 段階 |

\* Shadow 環境限定。Production 既定は OFF 維持。

ADR-008 `W_DECISION_*` は V90 表に従い **別管理**（本表に混在させない）。

---

## V106 Gap への対応マップ

| Gap | Migration での解消層 |
|---|---|
| G106-01 GAP-WIRE | P1 Core Payload Shadow → P3 Flag |
| G106-02 NL | P2/P3 Presentation（Core 非追加） |
| G106-03 Ticket/stake | P2/P3 Ticket Policy + EXT + ADR-008 |
| G106-04 候補数 | P2/P3 Candidate Expansion + V92 Registry |
| G106-05 保険 | P2/P3 Coverage Strategy |
| G106-06 難易度 | Race Selection KEEP_DERIVED（フィールド新設なし） |
| G106-07/08 NON-GAP | 移行対象外（復活禁止） |

---

## Related

- ADR-011
- `v90-migration-adr.md`
- `v106-contract-gap-report.md`
- `v107-governance.md`
