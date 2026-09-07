# V54 — Stage Plan（Flags / PASS / Rollback）

**Date:** 2026-07-28  
**Status:** Blueprint only — **does not implement**  
**Parent:** `v54-blueprint.md`  
**Merges:** V46 Stages + V50/V53 Assembly migration stages

---

## ③ Feature Flag Plan

### Modes

| Mode | Meaning |
|---|---|
| **Shadow** | New path evaluates; Production decision / HTTP truth unchanged |
| **Dual** | Both paths published or selectable; Legacy remains default authority |
| **Soft Cutover** | Flag ON → new path is default in limited env; Legacy instant rollback |
| **Cutover** | New path is Production authority; Legacy retained only as emergency rollback until removed |

### Flag placement（design names — not implemented here）

| Flag (design id) | Protects | Shadow | Dual | Soft | Cutover |
|---|---|---|---|---|---|
| `W_TRIGGER_SHADOW` | V44 Dual-Eval vs Legacy | **Yes** | — | — | — |
| `W_TRIGGER_PATH` | Production `classify_world_line_type` route | — | compare | **S6** | **S7** |
| `W_DEFAULT_CORE` | R8/core DEFAULT residual | observe | — | disable candidates | **remove S7** |
| `P_CE_DUAL_PUBLISH` | Emit CE alongside Bundle（meta/debug/parallel） | **Yes** | **Yes** | — | optional public CE |
| `P_ASSEMBLY_CE_INPUT` | Assembly input = CE vs ranking views | Shadow assemble | Dual | **Soft** | default |
| `P_PROJECT_WORLD` | Bundle `evaluation.world` from CE（stop None） | log-only | Dual | **Soft** | default |
| `P_MOCK_LABEL` | Mock/catalog marked non-canonical | — | — | **Soft** | default |

### Where Shadow / Dual / Cutover apply

| Area | Shadow | Dual | Cutover |
|---|---|---|---|
| Trigger decision (Track W) | S1–S5 | S6 | S7 |
| Must readiness | S2 ledger | — | — |
| Polarity ADR | S3 doc | — | values only after ADR+impl gate |
| CE publish (Track P) | C1 | C1–C2 | C7 optional endpoint |
| Assembly CE input | C2 shadow | C2–C3 | C4–C7 |
| Product world field | C3 log | C3 Dual | D1 after W Soft |
| PredictionBundle schema kill | **Forbidden** in this Blueprint | — | needs new ADR |
| PE / Scorer | Out of scope | — | — |

---

## Unified Stage Table

### Track W（from V46）

| Stage | Mode | PASS（要約） | Rollback |
|---|---|---|---|
| **W-S0** Baseline Freeze | Freeze | Legacy/Target/Gap locked | Cancel program |
| **W-S1** Shadow Dual-Eval | Shadow | N races dual-eval; Legacy distribution unchanged | Stop shadow jobs |
| **W-S2** Must Readiness | Shadow | All Must Ready/Proxy/Missing; Missing→Blocked | Revert ledger |
| **W-S3** Polarity ADR | Design | ADR Accepted; S4 rules documented | ADR → Draft/Reject |
| **W-S4** Per-World Shadow | Shadow | Per-world compliance gates; Forbidden rate OK | Disable world profile |
| **W-S5** Unsatisfied Shadow | Shadow | unsatisfied≠silent core; mixed separated | Flag off unsatisfied |
| **W-S6** Soft Cutover | Soft Dual | Flagged env uses V44 path; rollback drill OK | `W_TRIGGER_PATH=legacy` |
| **W-S7** DEFAULT Removal | Cutover | core Positive Match only; no DEFAULT residual | Restore DEFAULT path + flag |
| **W-S8** Downstream | Separate | Own plan PASS | Own rollback |

Recommended S4 order: rank7 → bug → mixed → midupper → midhole → core（V46）.

### Track P（V50 + V53; V52 constraints）

| Stage | Mode | PASS（要約） | Rollback |
|---|---|---|---|
| **P-C0** Assembly Charter freeze | Freeze | Inputs/owners documented（V53） | Charter draft |
| **P-C1** CE Dual-publish | Shadow/Dual | CE available without changing Bundle authority; no Consumer break | Disable publish flag |
| **P-C2** Assembly CE input (Dual) | Dual | Shadow Bundle from CE+RaceData+Bet ≡ or explained-diff vs legacy Bundle on Rank/Conf; World retained in shadow | Flag off CE input |
| **P-C3** Project world/sub_world | Dual→Soft | Bundle world matches CE when Real path; Mock labeled | Revert mapper flag（None allowed only as non-authoritative Dual off） |
| **P-C4** Assembly ownership soft | Soft | Rank/Conf/World pass-through; RaceInfo/Bet still Assembly; no rescoring | Previous Assembly path |
| **P-C5** Mock non-canonical | Soft | Provenance shows mock/fallback; ops Ready rules unchanged or documented | Label flag off |
| **P-C6** Docs/ops: ranking not truth | Soft | Runbooks cite CE as Canonical | Doc revert |
| **P-C7** Cutover Core-fact authority | Cutover | Product/ops treat CE (via Assembly projection) as Core-fact authority; Bundle remains View | Re-enable Dual; Legacy views |

### Cross

| Stage | Mode | PASS | Rollback |
|---|---|---|---|
| **X-D1** GUI world visible as truth | Soft | W-S6+ and P-C3 Soft PASS; Guard still Bundle schema | Hide world / Dual |
| **X-D2** Remove Dual flags | Cutover | W-S7 and P-C7 PASS; soak period | Re-enable Dual flags |

---

## ④ Acceptance Criteria（詳細テンプレ）

### Common PASS gates（all mutating stages）

1. **Decision Gate recorded**（Implementation Required: Yes の別承認）  
2. **Flag exists** and default keeps Legacy authority until Soft/Cutover  
3. **Rollback drill** executed once in non-prod or limited env  
4. **No silent PE/Trigger cross-cut** in same change set（W vs P isolation）

### Track W PASS references

Full checklists: `docs/architecture/v46-stage-design.md`

### Track P PASS details

| Stage | PASS criteria | Fail / Rollback criteria |
|---|---|---|
| P-C1 | Dual payload present; HTTP Bundle schema unchanged; GUI Guard still PASS | Consumer errors → disable `P_CE_DUAL_PUBLISH` |
| P-C2 | Assembly from CE produces runners; Bet+RaceInfo still populated; Rank order matches CE | Missing bets/race_info or rank drift → Dual off |
| P-C3 | Real path `evaluation.world` == CE.world; not presented as Mock truth | Mismatch or Guard fail → flag off |
| P-C4 | Ownership audit: no Core rescoring in Mapper; marks remain Product overlay | Rescoring detected → Soft revert |
| P-C5 | `engine_source` mock/fallback distinct from real_ai | Mislabel → Soft revert |
| P-C7 | Ops/runbook + API meta declare Canonical=CE; Bundle=View | Confusion incidents → return to Dual |

### Global Rollback Points（emergency）

| Boundary | Action |
|---|---|
| R-W | `W_TRIGGER_PATH=legacy`；Shadow jobs stop |
| R-P | All `P_*` flags → Legacy Assembly（ranking views + world None behavior as pre-stage） |
| R-X | GUI hides authoritative world; Dual re-enabled |
| R-Never | Do not “fix Bundle schema kill” as rollback of CE publish — restore Dual instead |

---

## Parallelism matrix

| | W Shadow S1–S5 | W Soft S6 | W Cutover S7 | P Dual C1–C3 | P Soft C4–C6 | P Cutover C7 |
|---|---|---|---|---|---|---|
| W Shadow | — | after | after | **OK parallel** | avoid same release | avoid |
| W Soft | — | — | after | OK Dual only | **serialize** | after W Soft |
| P Dual | OK | OK | OK | — | after | after |
| P Soft | OK if no world UX claim | serialize w/ W Soft | after W Soft preferred | after Dual | — | after |

---

*V54 Stage Plan — blueprint only.*
