# Version63 — Governance（PE Integration ROI）

**Date:** 2026-07-28  
**Subject:** World→PE 結合の ROI 期待値判定  
**Locks:** Production / PE / Prediction / Signal / Trigger / Threshold — 変更禁止・実装禁止

---

## Governance scale（本フェーズ）

| Grade | Meaning |
|---|---|
| **A** | ROI 期待あり（NI 付き Hit↑ が証明） |
| **B** | 限定的（影響はある／Hit↑ はあるが NI 非適合、または実用帯で悪化） |
| **C** | ROI 期待なし（影響も Hit 改善も実質なし） |

---

## Verdict

# **B（限定的）**

| Layer | Grade | Evidence |
|---|---|---|
| PE 影響（Top1 変化） | 影響あり | Legacy 25% で 14.7%、100% で 79.6% |
| 実用帯 ROI（25–75%） | **なし（負）** | ΔHit = -5 / -8 / -22 |
| 安全 ROI（Hit↑∧NI） | **不在** | 全 weight で `ni_with_influence ∧ hit_improved = False` |
| 極端 100% | Hit +45 だが rank710 +3 | 期待値としては **unsafe** |
| 総合 | **B** | 結合は inert ではないが、**出荷可能な ROI は未証明** |

**A にしない理由:** NI（rank710 / other_miss 非悪化）付き Hit↑ が一度も成立しない。  
**C にしない理由:** w=100% で Hit +45、かつ全正 weight で meaningful Top1 変化があり、「結合しても何も起きない」は偽。

---

## Primary arm checks（Legacy）

| Weight | Hit≥base | rank710≤base | other≤base | influence | Hit↑ | NI+ROI |
|-------:|:--------:|:------------:|:----------:|:---------:|:----:|:------:|
| 25% | No | No | No | Yes | No | No |
| 50% | No | No | Yes | Yes | No | No |
| 75% | No | No | No | Yes | No | No |
| 100% | Yes | No | Yes | Yes | Yes | **No** |

---

## Binding rules

1. V35: 現行 PE は World 非消費 — 結合しない限り Hit 不変（確定）。  
2. V62: Exclusion 緩和のみでは Hit Δ0（確定）。  
3. V63: Virtual PE Policy 結合でも **安全 ROI は未証明**（確定）。  
4. Hit フィット kernel 最適化は本フェーズ禁止（推測・過学習回避）。  
5. PE / Prediction / Production 実装は **未承認**。

---

## Decision Gate

```
【Decision】
Action Type: Research — PE Integration ROI Study (V63)
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（文書・反実仮想のみ）
Expected Next Action: PE 結合実装は未承認。次に進むなら「別 Policy / 別 Kernel / 別 Integration Point」の研究 Decision が必要。現状の design kernel では GO 不可。
```

---

## 成果物

| File | Role |
|---|---|
| `docs/research/v63-pe-integration-roi.md` | 接続点・変化 Simulation・ROI 期待 |
| `docs/research/v63-policy-impact.md` | World/Weight 別影響 |
| `docs/research/v63-governance.md` | 本判定 |
| `docs/research/_v63-sim.json` | 数値正本（KEIBA-Single-AI） |

---

## 明示的非実施

- PE / Ranker / Scorer の World 消費実装  
- Threshold / Trigger / Signal 変更  
- Production デプロイ  
- Kernel の Hit 最適化
