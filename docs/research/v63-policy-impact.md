# Version63 — Policy Impact

**Date:** 2026-07-28  
**Subject:** World→PE Virtual Policy の World 別 / Weight 別影響  
**Locks:** 実装禁止。製品 PE 未変更  
**データ:** `_v63-sim.json`（285R × Legacy / V44 / V44+FalseRelease）

---

## Primary: Legacy World × Weight 100%（最大影響）

| World | n | Top1 change rate | base Hit | policy Hit | ΔHit |
|---|---:|---:|---:|---:|---:|
| midupper_world | 110 | 100% | 25 | 50 | **+25** |
| mixed_world | 56 | 100% | 7 | 27 | **+20** |
| core_world | 104 | 44.2% | 22 | 25 | +3 |
| midhole_world | 15 | 100% | 5 | 2 | **-3** |

Hit +45 の主因は **midupper (+25) + mixed (+20)**。kernel が中帯を top1 に押し上げる効果。  
同時に全体 **rank710 +3**（悪化）— World 別の Hit 益が miss 構造を壊す。

---

## Legacy × 実用 Weight（25% / 50%）

### Weight 25%

| ΔHit | ΔPurchase | Δrank710 | Δother_miss | Top1 change |
|---:|---:|---:|---:|---:|
| -5 | -5 | +2 | +5 | 42 (14.7%) |

### Weight 50%

| ΔHit | ΔPurchase | Δrank710 | Δother_miss | Top1 change |
|---:|---:|---:|---:|---:|
| -8 | -8 | +7 | -1 | 123 (43.2%) |

**解釈（測定）:** 影響は十分（Top1 変化 ≥5%）だが、Hit/Purchase は改善せず悪化。

---

## V44 アーム（Positive Match のみ Policy）

| Weight | ΔHit | Δrank710 | Top1 change | 注 |
|-------:|-----:|---------:|------------:|---|
| 25% | 0 | +19 | 64 | unsatisfied 176 = identity |
| 50% | -5 | +26 | 100 | |
| 100% | +11 | +17 | 106 | rank7/midhole が Hit 益の主 |

V44 単独では **NI 付き ROI なし**。rank710 悪化が顕著。

---

## V44 + False Exclusion 解除（V62 ラベル反実仮想）

| Weight | ΔHit | Δrank710 | Top1 change |
|-------:|-----:|---------:|------------:|
| 25% | **+1** | +19 | 68 |
| 50% | -2 | +26 | 111 |
| 100% | +27 | +17 | 129 |

唯一の「低 weight Hit↑」は **+1 @25%** だが rank710 **+19** で NI 失敗。  
Exclusion 品質改善を PE に渡しても、**安全 ROI は出ていない**。

---

## Policy Domination フラグ

| Mode | Top1 change @100% | 判定 |
|---|---:|---|
| Legacy | 79.6% | domination（≥50%） |
| V44 | 37.2% | 中程度（identity 多い） |
| V44+False | 45.3% | 中程度 |

---

## Ranking Policy への含意（実装しない）

1. Design kernel の midupper/mixed 押し上げは Hit を動かし得るが、**rank710 とトレードオフ**。  
2. 現行 Legacy 分布（midupper 110 / core 104 / mixed 56 / midhole 15）では、ブレンドは実用帯で **負の Hit**。  
3. Kernel 再設計・学習は本フェーズ対象外（Hit フィットは過学習リスク。V37 と同方針で未実施）。

---

## Guardrails

Trigger / Signal / Threshold / PE / Prediction / Production — 未変更。
