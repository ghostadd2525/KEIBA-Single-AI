# W-S2 World Readiness Summary

**Date:** 2026-07-28  
**Version:** 59  
**Parent:** `w-s2-must-readiness.md`

---

## Must Readiness % by World

| World | Must Readiness % | Status | Driver |
|---|---:|---|---|
| core_world | **100%** | Ready | top_gap + ability_separation とも Derived 供給可 |
| midhole_world | **100%** | Ready | mid_band + top_monopoly Derived |
| rank7_world | **67%** | Partial | chaos/pace が Feature restore 依存（240/285） |
| midupper_world | **50%** | Partial | aptitude_fit Missing；development Partial |
| mixed_world | **50%** | Partial | multi_path Ready；unexplained Missing |
| bug_world | **0%** | Blocked | exception_flag Missing |

```text
Mean Must Readiness % (equal weight) ≈ 61%
```

---

## World-level Readiness label

| Label | Rule used here |
|---|---|
| Ready | 全 Must = Ready |
| Partial | 混在（Ready/Partial/Blocked）だが全 Blocked ではない |
| Blocked | 全 Must Blocked、または唯一 Must が Blocked |

---

## Notes tied to V58 conditions

1. **bug_world = Blocked** → S4 で Blocked 明示する材料が揃った。  
2. Exclusion / Polarity は World % に **入れていない**（対象外・S3）。  
3. 本 % は「Must 供給可能性」であり、Shadow Positive Match Rate（38%）や Unsatisfied（62%）とは別指標。

---

*Version59 — summary only.*
