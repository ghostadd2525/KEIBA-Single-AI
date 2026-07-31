# Version64 — Governance（World Classification Validation）

**Date:** 2026-07-28  
**Subject:** World 分類が設計意図どおりか  
**Locks:** PE / Prediction / Trigger / Signal / Threshold / World Logic / Production — 変更禁止  
**Note:** 先行の Strategy Discovery（同 Version64 系ドキュメント）は、本検証 **PASS まで停止**（ユーザー指示）。

---

## Governance scale

| Grade | Meaning |
|---|---|
| **A** | World 分類は設計どおり |
| **B** | 一部改善余地あり |
| **C** | World 分類は設計意図を満たしていない |

---

## Verdict

# **C（World 分類は設計意図を満たしていない）**

| 証拠 | 値 |
|---|---|
| Shadow vs Semantic GT Accuracy | **9.5%** |
| Shadow unsatisfied 率 | **61.8%**（≥50% → C 確定条件） |
| Winner Alignment aligned 率（Shadow） | **11.2%** |
| Macro Precision / Recall | 23.2% / 20.5% |
| bug 再現 | **0%**（Shadow 0 件） |
| V44 Positive Match 原則 | **未達成**（主結果が unsatisfied） |
| 主 Root Cause | Exclusion 117 / Must不足 89 / Data不足 36 |

**A/B にしない理由:** 精度も分布も WA も設計ミックスから大きく外れ、Positive Match 分類器として機能していない。

---

## Binding rules

1. **PE 研究・Strategy 研究は停止**（本検証が A/B 相当になるまで再開しない）。  
2. 本フェーズは検証のみ — 実装・閾値・Trigger・Signal・World Logic 変更禁止。  
3. GT は V43 Expected Characteristics Oracle（Shadow ラベルの自己参照禁止）。  
4. V45「Production ≠ Spec」および W-S1 Unsatisfied 61.8% と整合する再確認である。  
5. 先行 `v64-world-strategy.md` 等の Strategy 結論は、分類前提が未証明のため **採用保留**。

---

## Decision Gate

```
【Decision】
Action Type: Research — World Classification Validation (V64)
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書・集計のみ）
Expected Next Action: Classification が設計意図を満たすまで PE/Strategy を進めない。次の研究 Decision は別途（本フェーズは改修を許可しない）。
```

---

## 成果物

| File | Role |
|---|---|
| `v64-world-classification-validation.md` | GT 定義・Accuracy・WA |
| `v64-world-accuracy.md` | Precision / Recall |
| `v64-confusion-matrix.md` | 混同行列 |
| `v64-root-cause.md` | 誤分類原因 |
| `v64-governance.md` | 本判定 |
| `_v64-classification-validation.json` | 数値正本 |

---

## 明示的非実施

改善・実装・PE/Strategy 続行・Production 変更 — すべてなし。
