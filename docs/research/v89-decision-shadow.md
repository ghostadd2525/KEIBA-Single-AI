# Version89 — Decision Shadow

**Generated:** `2026-07-28T10:55:50+00:00`  
**Layer:** Decision only（Ticket / Pool / Explanation / Confidence表示 / Risk表示）  
**Locks:** Prediction / Rank / PE / Trigger / Blueprint / Interaction / Production — 非変更  
**Audit:** rank=True score=True n=285

## Verdict: **A**

Decision ON improves Coverage/Explainability and Ticket metric(s); ranks unchanged

## OFF vs ON（全体）

| Metric | Decision OFF | Decision ON | Δ (ON−OFF) |
|---|---:|---:|---:|
| Ticket ROI | 0.0246 | 0.0192 | -0.0054 |
| Ticket PnL | 700.0 | 495.0 | -205.0 |
| Purchase Hit | 0.2070 | 0.2679 | 0.0609 |
| Coverage (winner∈Pool) | 0.2070 | 0.3544 | 0.1474 |
| Buy rate | 1.0000 | 0.9298 | -0.0702 |
| Skip rate | 0.0000 | 0.0702 | — |
| Explainability | 1.0000 | 1.0000 | 0.0000 |
| Mean pool size | 1.0000 | 2.1614 | — |

### User Decision

- OFF: BUY=285 / SKIP=0
- ON: BUY=265 / SKIP=20

### Value flags

- `coverage_improved`: **True**
- `explainability_improved`: **False**
- `purchase_hit_improved`: **True**
- `roi_improved`: **False**

## 方法（Shadow）

- OFF: `Top1 win UNIT; pool=Top1; generic explanation; standard conf/risk`
- ON rank7: `win stakes 50/30/20 on Top1-3; pool Top5; melee explanation; conf suppressed`
- ON unsatisfied: `same ticket as OFF; residual explanation`
- ON midhole: `0.7*UNIT Top1; pool Top3∪history Top2; midhole explanation`
- ON blocked: `SKIP`

## 関連

- `v89-decision-evaluation.md`
- `v89-governance.md`
