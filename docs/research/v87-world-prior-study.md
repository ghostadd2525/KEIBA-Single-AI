# Version87 — World Prior Value Study

**Generated:** `2026-07-28T10:47:29+00:00`  
**Question:** World Prior の Calibration 改善は Global Calibration 以上の意味を持つか？  
**Locks:** Production / PE / Trigger / Blueprint / Interaction — 非変更 / 実装禁止

## Conclusion: **INCONCLUSIVE**

World は点推定で Global より良いが、bootstrap 95% CI は 0 を含み 統計的意味は未証明（標本・World差が小さい可能性）

## 方法

- Prior = chronological train half の empirical `hit_at_1` rate
- Course = `venue|surface` / Distance = 帯域ビン
- cell n < 5 は backoff
- 意味の判定 = bootstrap 2000 回、ΔBrier または ΔECE の 95% CI が改善側で 0 を含まない

train=142 / test=143 / global_train_rate=0.7746

## Cell 統計（train）

| Prior key | n_cells | n≥min | median n |
|---|---:|---:|---:|
| `global` | 1 | 1 | 142.0 |
| `course` | 17 | 10 | 5.0 |
| `distance` | 5 | 4 | 24.0 |
| `world` | 6 | 5 | 11.0 |
| `world_course` | 50 | 6 | 2.0 |
| `world_distance` | 21 | 9 | 3.0 |
| `world_course_distance` | 79 | 4 | 1.0 |

## Test 順位（ECE → Brier）

| Rank | Prior | ECE | Brier | LogLoss | bias |
|---:|---|---:|---:|---:|---:|
| 1 | `global` | 0.0194 | 0.1852 | 0.5576 | 0.0194 |
| 2 | `world` | 0.0202 | 0.1824 | 0.5491 | 0.0174 |
| 3 | `world_course` | 0.0259 | 0.1813 | 0.5452 | 0.0148 |
| 4 | `distance` | 0.0266 | 0.1878 | 0.5647 | 0.0173 |
| 5 | `course` | 0.0725 | 0.1950 | 0.8107 | 0.0447 |
| 6 | `world_course_distance` | 0.0813 | 0.1990 | 0.5958 | 0.0066 |
| 7 | `world_distance` | 0.1240 | 0.2033 | 0.6111 | 0.0141 |

## 主比較: World vs Global

- ΔBrier mean=-0.0028 CI=[-0.0071, 0.0025] P(better)=0.8720
- ΔECE mean=0.0051 CI=[-0.0064, 0.0238] P(better)=0.2685
- ΔLL mean=-0.0082 CI=[-0.0245, 0.0135]
- Brier CI excludes 0 (World better): **False**
- ECE CI excludes 0 (World better): **False**

## World別（test）— Global vs World Prior

| World | n | Global ECE | World ECE | Global Brier | World Brier |
|---|---:|---:|---:|---:|---:|
| `rank7_world` | 38 | 0.0411 | 0.0380 | 0.1520 | 0.1517 |
| `midhole_world` | 10 | 0.1254 | 0.0286 | 0.1057 | 0.0908 |
| `unsatisfied` | 91 | 0.0714 | 0.0496 | 0.2138 | 0.2111 |
| `midupper_world` | 1 | 0.2254 | 0.2000 | 0.0508 | 0.0400 |
| `mixed_world` | 3 | 0.2254 | 0.2254 | 0.0508 | 0.0508 |

## 関連

- `v87-prior-comparison.md`
- `v87-governance.md`
