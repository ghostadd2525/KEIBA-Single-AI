# Version99 — Governance（AI Core Completeness）

**Date:** 2026-07-28  
**ADR:** ADR-009 Accepted（Charter）

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | AI Core Completeness Charter |
| Implementation Required | **No**（憲章・評価フレームのみ） |
| Deployment Required | No |
| Core KPI | **Completeness**（Prediction / World / Near Miss） |
| Core KPI から除外 | ROI / 券種 / Skip / 資金配分 |
| Decision Owner | Single AI / Win5 AI（ADR-008） |
| Risk | Low（文書） |
| Expected Next Action | Completeness 測定 Shadow（観測のみ）。Core に Betting を戻さない |

---

## 硬制約

| ID | 制約 |
|---|---|
| G99-1 | AI Core 研究の主目的を利益最大化にしてはならない |
| G99-2 | ROI・券種・Skip・資金配分を Core の成功指標にしてはならない |
| G99-3 | Decision 最適化は Single / Win5 の Decision Layer に閉じる |
| G99-4 | Affinity / Near Miss は記述 Completeness の対象であり、購入ゲートの自動正当化に使わない（V97） |
| G99-5 | unsatisfied 件数削減を World Completeness の主目的にしない（V96） |
| G99-6 | 本フェーズで製品コードを変更しない |

---

## 成果物

| 成果物 | Path |
|---|---|
| ADR-009 | `docs/adr/ADR-009-ai-core-completeness.md` |
| Charter | `docs/research/v99-core-completeness-charter.md` |
| Evaluation Frame | `docs/research/v99-completeness-evaluation.md` |
| Governance | `docs/research/v99-governance.md` |

---

## 先行研究の再分類

| Version | 再分類 |
|---|---|
| V94–V96 | Core Completeness 資産（Taxonomy / Affinity） |
| V97–V98 | Decision 側研究（Core KPI 外） |
| V93 Betting | Decision 側研究（Core KPI 外） |
| V88–V92 Decision | Decision Layer（ADR-008）— Core 外 |

---

## 一文サマリ

**Core = 正確に記述する。Decision = 買いかどうかを決める。評価 = Completeness。**
