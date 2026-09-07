# Version50 Governance — Canonical Prediction Contract ADR

## Verdict

**ADR-050: ACCEPTED (design only)**  
**Canonical Prediction Contract = CorePublicBundle (`evaluate_candidates`)**  
**Implementation: NOT AUTHORIZED**

---

## Decision Summary

| Item | Decision |
|---|---|
| 唯一の正本 | **C1 CorePublicBundle** |
| Product PredictionBundle | Public View（非正本） |
| predict_ranking | Compatibility Projection（非正本） |
| world=None in Bundle | View 欠陥；Canonical 真理ではない |
| 実装 | V50 では行わない |

---

## Why not PredictionBundle as Canonical?

1. Canonizes `evaluation.world = None` against V43/V44 World semantics.  
2. Contradicts facade’s existing Canonical declaration (`evaluate_candidates`).  
3. Real and Mock producers share the name but not the authority.  
4. Would deepen V49 contract split instead of resolving it.

---

## Relation to prior versions

| Version | Contribution |
|---|---|
| V47 | PE は World 非消費；順位は Rank で凍結 |
| V48 | CE は World 保持；公開経路が破棄 |
| V49 | Prediction 契約分裂（C） |
| **V50** | **正本を C1 に固定（設計 ADR）** |

---

## Governance Rules after ADR-050

1. Architecture discussions must treat **CorePublicBundle** as Prediction truth.  
2. HTTP/GUI evidence of `world=None` describes **Product View behavior**, not Core Canonical state.  
3. Future implementation stages (if any) require separate approval; V46-style migration may apply to Product lineage.  
4. No new parallel Canonical DTO without superseding this ADR.

---

## What V50 did NOT do

- Code / Mapper / HTTP / Production changes  
- Schema migration of PredictionBundle  
- Forcing Product path to call `evaluate_candidates` in runtime  

---

## Artifacts

- `docs/architecture/v50-canonical-contract-adr.md`
- `docs/architecture/v50-contract-ownership.md`
- `docs/architecture/v50-contract-boundary.md`
- `docs/architecture/v50-governance.md`

## Expected Next Action

ADR-050 受理後の次方針（Product View の再配線設計 / 実装承認など）の指示待ち。  
V50 自体は設計定義で停止する。
