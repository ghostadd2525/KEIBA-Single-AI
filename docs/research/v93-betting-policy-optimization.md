# Version93 — Betting Policy Optimization

**Generated:** `2026-07-28T11:57:05+00:00`  
**Decision structure:** V92 `Top5_Pool7` 固定  
**Coverage floor (rank7):** 0.8308  
grid=200 / feasible=200

## Baseline（V92 betting）

`bet_L5_decay_none_b1__dec_T5P7`

- ROI=-0.3542 / PurchaseHit=0.6462 / Coverage=0.8308 / EV_on_buys=-0.1800

## 最適（Coverage 維持 ∩ ROI 最大）

**`bet_L1_equal_field_gt_16_b0.5__dec_T5P7`**

- buy_legs=1 / alloc=equal / skip=field_gt_16 / budget=0.5
- Ticket ROI=-0.2680 (Δ vs baseline 0.0862)
- Purchase Hit=0.2000
- Coverage=0.8308
- EV_on_buys=-0.1187
- Buy=0.7692 / Skip=0.2308

## Top20 feasible（rank7 ROI順）

| Policy | Legs | Alloc | Skip | Bud | ROI | Hit | Cov | EV | Buy | SkipRate |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| `bet_L1_equal_field_gt_16_b0.5__dec_T5P7` | 1 | equal | field_gt_16 | 0.5 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_equal_field_gt_16_b1__dec_T5P7` | 1 | equal | field_gt_16 | 1.0 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_decay_field_gt_16_b0.5__dec_T5P7` | 1 | decay | field_gt_16 | 0.5 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_decay_field_gt_16_b1__dec_T5P7` | 1 | decay | field_gt_16 | 1.0 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_top_heavy_field_gt_16_b0.5__dec_T5P7` | 1 | top_heavy | field_gt_16 | 0.5 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_top_heavy_field_gt_16_b1__dec_T5P7` | 1 | top_heavy | field_gt_16 | 1.0 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_mass_prop_field_gt_16_b0.5__dec_T5P7` | 1 | mass_prop | field_gt_16 | 0.5 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L1_mass_prop_field_gt_16_b1__dec_T5P7` | 1 | mass_prop | field_gt_16 | 1.0 | -0.2680 | 0.2000 | 0.8308 | -0.1187 | 0.7692 | 0.2308 |
| `bet_L5_equal_mass_lt_10_b0.5__dec_T5P7` | 5 | equal | mass_lt_10 | 0.5 | -0.2794 | 0.7273 | 0.8308 | -0.2565 | 0.5077 | 0.4923 |
| `bet_L5_equal_mass_lt_10_b1__dec_T5P7` | 5 | equal | mass_lt_10 | 1.0 | -0.2794 | 0.7273 | 0.8308 | -0.2565 | 0.5077 | 0.4923 |
| `bet_L3_top_heavy_field_gt_16_b0.5__dec_T5P7` | 3 | top_heavy | field_gt_16 | 0.5 | -0.2932 | 0.4600 | 0.8308 | -0.1435 | 0.7692 | 0.2308 |
| `bet_L3_top_heavy_field_gt_16_b1__dec_T5P7` | 3 | top_heavy | field_gt_16 | 1.0 | -0.2932 | 0.4600 | 0.8308 | -0.1435 | 0.7692 | 0.2308 |
| `bet_L2_equal_mass_lt_10_b0.5__dec_T5P7` | 2 | equal | mass_lt_10 | 0.5 | -0.2970 | 0.3636 | 0.8308 | -0.2416 | 0.5077 | 0.4923 |
| `bet_L2_equal_mass_lt_10_b1__dec_T5P7` | 2 | equal | mass_lt_10 | 1.0 | -0.2970 | 0.3636 | 0.8308 | -0.2416 | 0.5077 | 0.4923 |
| `bet_L4_equal_ev_neg_b0.5__dec_T5P7` | 4 | equal | ev_neg | 0.5 | -0.3000 | 0.5455 | 0.8308 | 0.5630 | 0.1692 | 0.8308 |
| `bet_L4_equal_ev_neg_b1__dec_T5P7` | 4 | equal | ev_neg | 1.0 | -0.3000 | 0.5455 | 0.8308 | 0.5630 | 0.1692 | 0.8308 |
| `bet_L5_top_heavy_field_gt_16_b0.5__dec_T5P7` | 5 | top_heavy | field_gt_16 | 0.5 | -0.3006 | 0.6800 | 0.8308 | -0.1508 | 0.7692 | 0.2308 |
| `bet_L5_top_heavy_field_gt_16_b1__dec_T5P7` | 5 | top_heavy | field_gt_16 | 1.0 | -0.3006 | 0.6800 | 0.8308 | -0.1508 | 0.7692 | 0.2308 |
| `bet_L5_mass_prop_mass_lt_10_b0.5__dec_T5P7` | 5 | mass_prop | mass_lt_10 | 0.5 | -0.3007 | 0.7273 | 0.8308 | -0.2528 | 0.5077 | 0.4923 |
| `bet_L5_mass_prop_mass_lt_10_b1__dec_T5P7` | 5 | mass_prop | mass_lt_10 | 1.0 | -0.3007 | 0.7273 | 0.8308 | -0.2528 | 0.5077 | 0.4923 |

## 方法

- 券種: win のみ（複勝オッズ/着順なしのため）
- 購入点数: buy_legs 1–5（V92 Top5 候補内）
- 配分: equal / decay / top_heavy / mass_prop
- Skip: none / ev_neg / mass_lt_08 / mass_lt_10 / field_gt_16
- Budget: 0.5 / 1.0 × UNIT
- Pool は常に Pool7 → Coverage を構造的に維持

## 関連

- `v93-betting-pareto.md`
- `v93-governance.md`
