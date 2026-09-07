# Version89 — Decision Evaluation

**Generated:** `2026-07-28T10:55:50+00:00`  

## World別 — Decision OFF

| World | n | ROI | PurchaseHit | Coverage | Explain | Buy |
|---|---:|---:|---:|---:|---:|---:|
| `core_world` | 8 | -0.2000 | 0.2500 | 0.2500 | 1.0000 | 1.0000 |
| `midhole_world` | 24 | -0.6750 | 0.0833 | 0.0833 | 1.0000 | 1.0000 |
| `midupper_world` | 6 | 0.5500 | 0.3333 | 0.3333 | 1.0000 | 1.0000 |
| `mixed_world` | 6 | 1.8167 | 0.5000 | 0.5000 | 1.0000 | 1.0000 |
| `rank7_world` | 65 | -0.4369 | 0.1538 | 0.1538 | 1.0000 | 1.0000 |
| `unsatisfied` | 176 | 0.2216 | 0.2273 | 0.2273 | 1.0000 | 1.0000 |

## World別 — Decision ON

| World | n | ROI | PurchaseHit | Coverage | Explain | Buy | Skip |
|---|---:|---:|---:|---:|---:|---:|---:|
| `core_world` | 8 | — | — | 0.2500 | 1.0000 | 0.0000 | 1.0000 |
| `midhole_world` | 24 | -0.6750 | 0.0833 | 0.5000 | 1.0000 | 1.0000 | 0.0000 |
| `midupper_world` | 6 | — | — | 0.3333 | 1.0000 | 0.0000 | 1.0000 |
| `mixed_world` | 6 | — | — | 0.5000 | 1.0000 | 0.0000 | 1.0000 |
| `rank7_world` | 65 | -0.3494 | 0.4462 | 0.6462 | 1.0000 | 1.0000 | 0.0000 |
| `unsatisfied` | 176 | 0.2216 | 0.2273 | 0.2273 | 1.0000 | 1.0000 | 0.0000 |

## 指標定義

| 指標 | 定義 |
|---|---|
| Ticket ROI | (Σreturn − Σstake) / Σstake。return = stake×odds（的中 win） |
| Purchase Hit | 購入レースのうち、いずれかの win ticket が的中した割合 |
| Coverage | 勝馬が Candidate Pool に含まれる割合（順位配列は不変） |
| User Decision | BUY / SKIP 率 |
| Explainability | 説明テンプレが World Policy と一致する割合 |

Coverage lift races (ON>OFF): 42 / drop: 0
