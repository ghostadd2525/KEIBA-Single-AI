# Version90 — Governance（Decision Layer ADR）

**Date:** 2026-07-28  
**Verdict:** **A**（ADR-008 Accepted / 実装未承認）  
**Type:** Architecture Decision Record

【Decision】

| Item | Value |
|---|---|
| Action Type | Decision Layer ADR Freeze |
| Implementation Required | **No** |
| Deployment Required | No |
| Production Required | **No** |
| Configuration Required | No（Flag は設計のみ） |
| Rollback Required | No（未実装） |
| Risk | None（文書） |
| Expected Next Action | 実装する場合は別 Decision で M1/M2 承認。それまで Prediction/World→PE 経路の復活は禁止 |

## 確定サマリ

| 層 | 確定 |
|---|---|
| Prediction Engine | World 非依存 |
| Confidence | Global Calibration |
| World | Decision Layer 専属 |
| Decision | Ticket / Pool / Explanation / Risk |

## 遵守

| 制約 | 結果 |
|---|---|
| 実装禁止 | PASS |
| ADR として責務/Owner/Contract/Rollback/Migration/Flag 定義 | PASS |
| V43–V89 反映 | PASS |

## 成果物

| 成果物 | Path |
|---|---|
| Decision Layer ADR（正式） | `docs/adr/ADR-008-decision-layer.md` |
| Decision Layer ADR（V90 入口） | `docs/research/v90-decision-layer-adr.md` |
| Responsibility Matrix | `docs/research/v90-responsibility-matrix.md` |
| Migration ADR | `docs/research/v90-migration-adr.md` |
| Governance | `docs/research/v90-governance.md` |

## ADR Index 更新

`docs/adr/README.md` に ADR-008 を追加する。
