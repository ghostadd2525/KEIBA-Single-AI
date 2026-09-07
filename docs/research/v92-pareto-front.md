# Version92 — Decision Policy Pareto Front

**Generated:** `2026-07-28T11:37:53+00:00`  
**Axes (rank7):** maximize Purchase Hit × Ticket ROI  
**Grid:** Top2–5 × Pool4–7（16点）  
ADR-008 / Prediction 非変更

## Pareto Front（Hit × ROI）

| Policy | Top | Pool | PurchaseHit | TicketROI | Coverage | Hit | Buy |
|---|---:|---:|---:|---:|---:|---:|---:|
| `rank7_Top5_Pool4_s1` | 5 | 4 | 0.6462 | -0.3542 | 0.6462 | 0.6462 | 1.0000 |
| `rank7_Top5_Pool5_s1` | 5 | 5 | 0.6462 | -0.3542 | 0.6462 | 0.6462 | 1.0000 |
| `rank7_Top5_Pool6_s1` | 5 | 6 | 0.6462 | -0.3542 | 0.7846 | 0.6462 | 1.0000 |
| `rank7_Top5_Pool7_s1` | 5 | 7 | 0.6462 | -0.3542 | 0.8308 | 0.6462 | 1.0000 |
| `rank7_Top3_Pool4_s1` | 3 | 4 | 0.4462 | -0.3494 | 0.5538 | 0.4462 | 1.0000 |
| `rank7_Top3_Pool5_s1` | 3 | 5 | 0.4462 | -0.3494 | 0.6462 | 0.4462 | 1.0000 |
| `rank7_Top3_Pool6_s1` | 3 | 6 | 0.4462 | -0.3494 | 0.7846 | 0.4462 | 1.0000 |
| `rank7_Top3_Pool7_s1` | 3 | 7 | 0.4462 | -0.3494 | 0.8308 | 0.4462 | 1.0000 |

## Pareto Front（Coverage × ROI）

| Policy | Top | Pool | Coverage | TicketROI | PurchaseHit |
|---|---:|---:|---:|---:|---:|
| `rank7_Top3_Pool7_s1` | 3 | 7 | 0.8308 | -0.3494 | 0.4462 |

## 推奨点

- **Max ROI:** `rank7_Top3_Pool4_s1` ROI=-0.3494 Hit=0.4462
- **Max Purchase Hit:** `rank7_Top5_Pool4_s1` Hit=0.6462 ROI=-0.3542
- **Balanced (Hit+ROI):** `rank7_Top5_Pool7_s1` Hit=0.6462 ROI=-0.3542
- **M1 baseline:** `rank7_Top3_Pool5_s1` on_pareto=True

**Recommended default (Shadow):** `rank7_Top5_Pool7_s1`
