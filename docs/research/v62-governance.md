# Version62 — Governance（Exclusion ROI Simulation）

**Date:** 2026-07-28  
**Subject:** Exclusion 緩和の ROI 期待値判定  
**Locks:** Trigger / Signal / Threshold / Polarity / Prediction / PE / Production / Exclusion 実装 — すべて変更禁止

---

## Governance scale（本フェーズ）

| Grade | Meaning |
|---|---|
| **A** | ROI 期待大（Hit/Purchase 改善が反実仮想で十分） |
| **B** | 限定的（Shadow 指標のみ、または Hit 改善が薄い） |
| **C** | ROI 不足（Hit/Purchase Δ≈0、または悪化方向） |

---

## Verdict

# **C（ROI 不足）**

| Layer | Grade | Evidence |
|---|---|---|
| Hit / Purchase | **C** | False 解除・条項解除・全 Near 解除いずれも **Δ0** |
| rank710 / other_miss | **C** | いずれも **Δ0**（PE 固定） |
| Winner Alignment（Shadow） | **B 相当** | False 51 解除で aligned **+51**（ラベル品質） |
| 条項一律解除 | **C** | Hit Δ0 かつ True 巻き込みで soft/misaligned 増 |

**総合:** 本フェーズの ROI 定義は **賭け指標（Hit/Purchase）** を主とする。Shadow WA 改善だけでは **A/B に上げない** → **C**。

---

## アーム別判定

| Arm | Hit ROI | Shadow WA | 判定 |
|---|---|---|---|
| False Exclusion 解除 | Δ0 | +51 aligned | **C**（賭け）/ Shadow のみ見れば限定的 |
| True Exclusion 維持 | — | 誤解除時 aligned 0 | **維持が正しい** |
| sfp / mid_band / chaos 一律 | Δ0 | +16〜+36（True 汚染あり） | **C** |
| 全 Near 解除 | Δ0 | +51 + soft25 + mis28 | **C（悪化方向のラベル混入）** |

---

## Binding rules

1. Exclusion 緩和は **Prediction/PE に結合しない限り Hit ROI を生まない**（V62 実証）。  
2. False Exclusion 51 は **設計過剰の証拠**だが、**即時 Rewrite 許可にはならない**。  
3. Polarity ADR（W-S3）・閾値・Trigger は **未変更のまま**。  
4. World→PE Policy 結合は **別 Decision**（本フェーズ非承認）。  
5. True Exclusion 53 の維持を優先（誤解除は misaligned 多い）。

---

## Decision Gate

```
【Decision】
Action Type: Research — Exclusion ROI Simulation (V62)
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書・反実仮想のみ）
Expected Next Action: Exclusion Rewrite / Trigger 変更は未承認。ROI を求めるなら World↔PE 結合の別 Decision、または現状維持で Track W を継続。
```

---

## 成果物

| File | Role |
|---|---|
| `docs/research/v62-exclusion-roi.md` | 解除アーム別 ROI・変化予測 |
| `docs/research/v62-rule-impact.md` | 条項別インパクト |
| `docs/research/v62-governance.md` | 本判定 |

---

## 明示的非実施

- Exclusion 条項の削除・緩和実装  
- Threshold / Polarity / Trigger 変更  
- Prediction / PE / Production 変更  
- Cutover
