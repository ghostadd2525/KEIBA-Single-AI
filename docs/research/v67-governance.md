# Version67 — Governance（Trigger Rule Anatomy）

**Date:** 2026-07-28  
**Subject:** R1/R7/R8 内部の改善ポイントは何か  
**Locks:** Trigger / Threshold / Signal / Polarity / PE / Prediction / Production — 変更禁止

---

## Governance scale

| Grade | Meaning |
|---|---|
| **A** | 改善ポイント特定（条件単位で触る点が明確） |
| **B** | 追加分析必要 |
| **C** | Rule 構造変更が必要 |

---

## Verdict

# **C（Rule 構造変更が必要）**

| 層 | 判定 |
|---|---|
| 条件の可視化 | できた（sfp / OR 腕 / difficulty / DEFAULT） |
| Top3 FP の依存 | **100% Rule設計**（Data/Signal 0） |
| R8 | **DEFAULT 構造** — 原子条件が存在しない |
| R7 | **単一 difficulty** — Aux/第2 Must 無し |
| R1 | OR bundle Pass率 79% — **構造的に弱選択** |

条件名・失敗件数は特定できたが、主責任は「どの閾値か」ではなく **Logic Form（DEFAULT / 単条件 / 広 OR）**。  
よって A（閾値・条件ピンポイント改善で足りる）ではなく **C**。

---

## ⑦ Priority（Rule 内部・観測のみ）

| 順 | Rule | 内部ポイント | 根拠 |
|---:|---|---|---|
| 1 | R7 | `difficulty≥0.50` 単一 Must | Trigger FP 57 が全て通過 |
| 2 | R1 | `sfp≥0.72` ゲート（OR は選別弱） | FP 50 全て sfp True。OR ほぼ冗長 |
| 3 | R8 | DEFAULT 残余そのもの | FP 46。正の Must 無し（V42 と一致） |

**本リストは改修許可ではない。**

---

## Binding rules

1. 解剖のみ — Trigger/Threshold 変更禁止。  
2. V66 Priority（R7>R1>R8）と整合。  
3. Signal/Data 主因仮説は Top3 FP では **棄却**。  
4. 将来改修するなら構造（Logic Form）が対象になり得るが、**別 Decision が必要**。

---

## Decision Gate

```
【Decision】
Action Type: Research — Trigger Rule Anatomy Audit (V67)
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書・集計のみ）
Expected Next Action: 構造変更を検討する場合は別 Decision。本フェーズは改修禁止のまま終了。
```

---

## 成果物

| File | Role |
|---|---|
| `v67-trigger-rule-anatomy.md` | 内部条件・Failure |
| `v67-condition-analysis.md` | Precision / Recall / Dead |
| `v67-rule-dependency.md` | Signal/Data/Rule設計 |
| `v67-governance.md` | 本判定 |
| `_v67-rule-anatomy.json` | 数値正本 |
