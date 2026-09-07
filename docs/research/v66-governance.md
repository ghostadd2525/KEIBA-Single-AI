# Version66 — Governance（Trigger Rule Attribution）

**Date:** 2026-07-28  
**Subject:** Trigger 起因 157 件は Rule 単位で説明できるか  
**Locks:** Trigger / Signal / Threshold / Polarity / Exclusion / PE / Prediction / World / Production — 変更禁止

---

## Governance scale

| Grade | Meaning |
|---|---|
| **A** | Rule 単位で原因が特定できた |
| **B** | 一部特定 |
| **C** | Rule では説明できず Signal / Data 側が主因 |

---

## Verdict

# **A（Rule 単位で原因が特定できた）**

| 証拠 | 値 |
|---|---|
| V65 Trigger 誤分類 | 157 |
| Rule 帰属できた件数 | **157（100%）** |
| classify ≡ first_match | **285/285** |
| Top3 Rule シェア | R7+R1+R8 = **97.5%** |
| 主因 Rule | R7 (57), R1 (50), R8 (46) |

**C にしない理由:** 157 件は Signal/Data 残差ではなく、具体的 R1–R8 発火に分解できた。  
**B にしない理由:** 帰属漏れなし。

---

## Binding rules

1. 本フェーズは **責任分解のみ** — Rule 改修・閾値変更・実装禁止。  
2. Priority Ranking は将来 Decision の入力候補であり、**改修許可ではない**。  
3. R5/R6 発火 0 は「無関係」ではなく **未発火ギャップ**として記録（改修は別 Decision）。  
4. V65 Governance C（Intent 不一致）は維持。本 A は「Trigger バケット内の分解可能性」の A。

---

## Decision Gate

```
【Decision】
Action Type: Research — Trigger Rule Attribution Audit (V66)
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書・集計のみ）
Expected Next Action: 改修する場合は別 Decision で Top3（R7/R1/R8）を対象候補にできるが、本フェーズは改修を許可しない。
```

---

## 成果物

| File | Role |
|---|---|
| `v66-trigger-rule-attribution.md` | 帰属総論 |
| `v66-rule-precision.md` | Precision |
| `v66-rule-recall.md` | Recall / FP / FN |
| `v66-confusion-matrix.md` | Rule→Intent 行列 |
| `v66-priority-ranking.md` | 影響順位 |
| `v66-governance.md` | 本判定 |
| `_v66-rule-attribution.json` | 数値正本 |
