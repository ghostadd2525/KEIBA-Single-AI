# W-S3 Governance（Polarity ADR — Version60）

**Date:** 2026-07-28  
**Subject:** Formal Signal Polarity Contract（ADR-W-S3）  
**Locks:** No Production / Prediction / PE / CE / Signal / Cutover / Trigger / Exclusion changes

---

## ADR Status

# **Accepted（design only）**

極性（Positive / Negative / Neutral / Forbidden-as-positive）を正式契約として固定した。  
実装・閾値・Exclusion 変更は含まない。

---

## Governance scale（本 ADR の性質）

| Grade | Meaning（本フェーズ） |
|---|---|
| **A** | 極性契約として確定可能（V43/V44 根拠十分） |
| **B** | 一部 Signal は供給 Missing だが極性定義は可能 |
| **C** | 極性を契約化できない |

## Verdict

# **A（極性契約として確定）＋供給面は B 併記**

| Layer | Grade | Note |
|---|---|---|
| Polarity contract completeness（対象11 Signal） | **A** | V43/V44 T3・Roles で方向を固定可能 |
| Supply readiness（W-S2） | **B** | aptitude / unexplained / exception は Missing のまま |

Missing でも極性定義は有効（V59 Ledger と矛盾しない）。

---

## Binding rules

1. World Mapping in `w-s3-polarity-adr.md` / `w-s3-world-polarity.md` が正本  
2. Conflict Matrix は境界の意図であり「バグ一覧」ではない  
3. 閾値・batch-median は本 ADR の代替にならない（仮観測）  
4. Exclusion 104 は **Polarity 確定後の評価対象**（本フェーズ未実施）  
5. Cutover / Trigger 実装は別 Decision  

---

## Decision Gate

```
【Decision】
Action Type: W-S3 Polarity ADR
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No（文書 ADR；Reject 時は Draft 差戻し）
Risk: Low（設計契約のみ）
Expected Next Action: Optional Shadow re-measure of Exclusion 104 under this polarity contract (still no Trigger change) OR W-S4 planning with bug Blocked — separate Decision
ADR Status: Accepted (design)
```

---

## Document Index

| Doc | Role |
|---|---|
| `w-s3-polarity-adr.md` | ADR 本文 |
| `w-s3-world-polarity.md` | World × Signal 極性 |
| `w-s3-conflict-matrix.md` | 衝突表 |
| `w-s3-governance.md` | 本ファイル |

---

## Stage chain

| Stage | Status |
|---|---|
| W-S2 Ledger | Complete |
| **W-S3 Polarity ADR** | **Accepted（design）** |
| Exclusion 104 re-eval | Not started |
| W-S4 | Blocked until Decision；bug Must Missing |

---

*Version60 — polarity ADR governance only.*
