# W-S1 Governance（Unsatisfied Root Cause — Version57）

**Date:** 2026-07-28  
**Subject:** Why Shadow V44 yields Unsatisfied 176/285  
**Prior:** W-S1 Gate PASS（Production = Legacy; Δ0 Prediction）は維持

---

## Scale

| Grade | Meaning |
|---|---|
| **A** | 実装可能 — Trigger/コード修正で閉じる単一欠陥 |
| **B** | Signal不足 — 供給・復元・極性入力の不足が主因 |
| **C** | 設計不足 — Logic Form / Must定義 / 前提データと仕様のギャップが主因 |

---

## Verdict

# **C — 設計不足**

---

## Evidence

1. **Must 成功例がすべて Exclusion で潰れる（104）**  
   `must=True & exclude=False` が 0件。Positive Match の「Mustまで到達したのに Exclude」が支配的。  
   → V44 Exclusion 設計と batch-median 観測極性の交差（S3 Polarity ADR 未決領域）。コード1箇所のバグではない。

2. **mixed Must が multi_path 論理（113 near-miss）**  
   単一 Signal 追加では Positive Match にならない。設計上の Must 形。

3. **bug が exception_flag 必須だがコーパスに非存在**  
   bug 経路は仕様上閉じている。Signal「不足」であると同時に、仕様が存在しない入力を要求する **設計前提ギャップ**。

4. **副次 B（Signal不足）**  
   - 全 Must 失敗 72件（chaos / top_gap / aptitude 等の Must ギャップ）  
   - restore失敗 31件  
   - 極性1軸 Near Miss 63件  

B は併存するが、最大コホート（104）と mixed/bug の閉じ方は **C**。

---

## Why not A / B alone

| Grade | Reject |
|---|---|
| A | Production Trigger を直せば消える類ではない（Shadow Spec 観測）。実装禁止フェーズの対象外でも、性質が「単バグ」ではない |
| B only | Exclusion-after-Must 104 と multi_path Must を Signal 供給だけでは説明しきれない |

---

## Decision Gate（参照）

```
【Decision】
Action Type: W-S1 Unsatisfied Root Cause Audit
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書のみ）
Expected Next Action: W-S2 Must Signal Readiness（別Gate）— Unsatisfied の Signal/設計切り分け台帳化。改善実装は禁止のまま
```

---

## Note on prior `w-s1-governance.md`

W-S1 Stage Gate PASS（Legacy 決定・Δ0）は有効。  
本ファイルは **Unsatisfied 176 の原因統治**を Version57 として記録する。

---

*Version57 — research classification only. Grade C.*
