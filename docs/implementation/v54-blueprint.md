# V54 — ADR Implementation Blueprint

**Date:** 2026-07-28  
**Status:** Blueprint ONLY — **コード変更・実装・改善は禁止**（本フェーズ）  
**Purpose:** V43–V53 で確定した Architecture / ADR を、実装者が着手可能な順序・Flag・PASS に落とす。  
**Does not authorize:** any Production / Prediction / PE / CE / Trigger / Signal mutation. Each Stage needs a **separate Decision Gate**.

---

## Source ADR set（本 Blueprint の対象）

| ID | Title | Role in Blueprint |
|---|---|---|
| **V43** | World Semantic Contract | 意味の正本（勝ち筋） |
| **V44** | World Trigger Specification | Semantic→Trigger Logic Form |
| **V46** | World Trigger Migration Plan | Trigger 段階移行 S0–S8 |
| **V50** | ADR-050 Canonical Contract | CorePublicBundle = Canonical |
| **V53** | Prediction Assembly Boundary | Core↔Product 合成境界 |

**Supporting（順序制約の根拠・実装対象外の監査）:** V45 Gap, V47–V49, V51 Impact, V52 Adapter≠sufficient

---

## ① Implementation Order（ADR 依存）

### Dependency graph

```text
V43 World Semantic Contract          [Design frozen — prerequisite]
        │
        ▼
V44 Trigger Specification            [Design frozen — prerequisite]
        │
        ▼
V46 Trigger Migration S0──►S7        [Track W — World decision path]
        │                    └──► S8 Downstream（別ゲート）
        │
        │  ※ V46 Principle 4: Trigger と Prediction 同時切替禁止
        │
V50 ADR-050 Canonical                [Design frozen — prerequisite]
        │
        ▼
V53 Assembly as Product boundary     [Design frozen — prerequisite]
        │
        ▼
V50+V53 Prediction Assembly Migration [Track P — Contract/Assembly path]
        │
        └── Hard Product world exposure は Track W Soft/Hard 後を推奨
```

### Ordered workstreams

| Order | Workstream | ADR | May start when |
|---|---|---|---|
| **0** | Prerequisites lock | V43, V44, V50, V53 | Already design-accepted |
| **1** | **Track W** Trigger Shadow→Cutover | V46 S0→S7 | V43+V44 locked |
| **2** | **Track P** Assembly Dual/Shadow | V50+V53 (+V51/V52 constraints) | V50+V53 locked; **parallel with W Shadow OK** |
| **3** | **Cross** Product world authoritative | V50∩V46 | Track P Dual PASS **and** Track W ≥ S6 recommended |
| **4** | **Track W S8** Downstream binding | V46 S8 | S7 PASS |
| **5** | Optional Bundle schema / CE public endpoint | Post-ADR | Separate ADR — not in this Blueprint mandatory path |

### Hard rules（実装順）

1. **V43 → V44 → V46** は直列。V44 なしに Trigger 実装しない。  
2. **V50 → V53 → Track P** は直列。Pure View Adapter 単独 cutover 禁止（V52）。  
3. **Track W Soft/Hard Cutover と Track P Soft Cutover を同一リリースに混ぜない**（V46 Downstream Isolation）。  
4. Track P の Shadow Dual-publish（CE 併記・決定非変更）は Track W Shadow と **並列可**。  
5. `evaluation.world` を Product の権威ある表示にする切替は、Track W が Legacy DEFAULT 依存のままなら **Dual のみ**（Hard は S6+ 後）。

詳細 Stage: `v54-stage-plan.md`  
Module: `v54-module-map.md`  
Governance: `v54-governance.md`

---

## ⑤ Final Blueprint（着手用要約）

実装者は次の順で **Stage ゲートごとに**着手する（本文書は許可証ではない）。

### Phase A — Document / Research locks（実装コードなしでも可）

| Step | Action | Exit |
|---|---|---|
| A1 | Confirm V43/V44/V50/V53 as authority | Checklist signed |
| A2 | V46 S0 Baseline Freeze | Legacy vs Target named |
| A3 | Assembly Input Contract freeze（V53） | CE + RaceData + Bet + Catalog listed |

### Phase B — Track W（Trigger）

| Step | V46 | Mode |
|---|---|---|
| B1 | S1 Shadow Dual-Eval | Shadow |
| B2 | S2 Must Readiness | Shadow / Research |
| B3 | S3 Polarity ADR | Design ADR |
| B4 | S4 Per-World Shadow | Shadow |
| B5 | S5 Unsatisfied Shadow | Shadow |
| B6 | S6 Flagged Soft Cutover | Dual→Soft |
| B7 | S7 DEFAULT Removal | Cutover |
| B8 | S8 Downstream | Separate plan |

### Phase C — Track P（Canonical + Assembly）

| Step | Name | Mode |
|---|---|---|
| C1 | CE Dual-publish（meta/debug or parallel field） | Shadow/Dual |
| C2 | Assembly reads Canonical CE（or world-preserving equivalent） | Dual |
| C3 | Stop nulling world/sub_world in Product View | Dual→Soft |
| C4 | Keep PredictionBundle as Product View; RaceData+Bet stay in Assembly | Soft |
| C5 | Label Mock non-canonical | Soft |
| C6 | Optional: deprecate ranking-as-truth in docs/ops | Soft |
| C7 | Hard: Product cites CE as authority for Core facts | Cutover（after gates） |

### Phase D — Cross（任意・高リスク）

| Step | Action | Mode |
|---|---|---|
| D1 | GUI/Functions treat projected world as user-visible truth | Soft only if W≥S6 |
| D2 | Remove Dual / Shadow flags | Cutover after C7+W S6/S7 PASS |

---

## Non-Goals（本 Blueprint）

- 本フェーズでのコード変更  
- Threshold 数値の決定（V46 S3 の別 ADR）  
- PE / Scorer / Ranker ロジック変更  
- PredictionBundle スキーマ破壊的置換（V52: Adapter alone 不可）  
- Win5 Optimizer と Trigger の同時全面書換（S8 分離）

---

## Document Index

| Doc | Content |
|---|---|
| `v54-blueprint.md` | 本ファイル（順序 + Final Blueprint） |
| `v54-module-map.md` | ADR→Module 対応 |
| `v54-stage-plan.md` | Flag / PASS / Rollback |
| `v54-governance.md` | 統治・承認 |

---

*V54 Blueprint — design packaging only. No implementation in this phase.*
