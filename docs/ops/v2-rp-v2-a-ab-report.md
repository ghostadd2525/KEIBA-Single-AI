# RP-V2-A — AB Report (Version 2 Accuracy)

**Generated:** 2026-07-22T01:57:57Z
**Experiment ID:** `v2-rp-v2-a-285r-ab`
**Git SHA:** `7732f06e8d606d31d1deb338aa306d670a5e2576`
**Flag:** `WIN5_REPICK_V2_ENABLED` (Treatment only; PE-V2-A stays ON both arms)
**Control baseline:** PE-V2-A PASS (Hit=218)
**STATUS:** **FAIL**
**AB_PASS:** **False**
**Flag recommendation:** `OFF`

## Hard Gate

`Treatment.Hit > 218` → **FAIL** (Hit=218)

## Metrics

| arm | Hit | Purchase | rank710 | other | rank46 | Winner in Pool率 | Winner Rescue |
|-----|----:|---------:|--------:|------:|-------:|-----------------:|--------------:|
| Control (PE-V2-A) | 218 | 187 | 14 | 18 | 35 | 0.961404 | — |
| Treatment (PE+RP-V2-A) | 218 | 187 | 14 | 18 | 35 | 0.961404 | 0/11 |
| Δ | 0 | 0 | 0 | 0 | 0 | 0.0 | R_G1=0.0 |

- rp_v2 fired_tx: **5**
- hit_loss (churn): **0**

## Gates

| gate | pass |
|------|------|
| G-Hard_Hit_gt_218 | False |
| G-Ident_ctrl_pe_lock | True |
| G-Loss_churn_hit_0 | True |
| G-Single_flag_RP | True |
| G-Pool_p95_le_110pct | True |
| G-Purchase_p95_le_110pct | True |

## 1. Hit が改善したレース

- （なし）

## 2. Purchase が悪化したレース（Control in_purchase → Treatment 脱落）

- （なし）

## 3. RP-V2-A Winner Rescue 一覧（G1）

- （なし）

## 4. Rescue / 発火の副作用

- Hit/Purchase 副作用レースなし（本 AB 定義）

## 5. PE-V2-A と RP-V2-A の役割分担（考察）

- **PE-V2-A（Pool/Entry）:** 深位（rank10–13）の Candidate Pool 入場を +1 枠緩和。Winner in Pool 率を押し上げ、下流に候補を供給する。先行 AB で Hit 216→218、Purchase 189→187。
- **RP-V2-A（RePick）:** Pool 内だが survival 圧縮で枠外になった mid（rank7–10, N+1）を、深い victim（rank≥11）と 1:1 置換する。Pool サイズは増やさない。
- **本 AB の Purchase:** Control=Treatment=187（Δ0）。PE 由来の 189→187 は本 RP AB では再発していない。
- **Winner Rescue:** G1（評価母集団 11）での `in_repick` 復帰件数。本番トリガは匿名（TN-A/C/D + fire_cap）であり G1 allowlist は使わない。

### FAIL 要因（本 AB）

| 観測 | 値 | 解釈 |
|------|---:|------|
| Hard Gate Hit>218 | **未達**（218→218） | 効果ゼロ |
| Winner Rescue | **0/11** | G1 を救済できず |
| fired_tx | **5** | 発火が極端に少ない |
| mid_cap 不発 | 198 | selected 内 mid≥2 で大半がゲート落ち |
| no_near_candidate | 77 | TN-A（N+1 のみ）で候補不足 |
| no_deep_victim | 5 | TN-C で victim 不在 |
| G1 の不発内訳 | mid_cap 5 / no_near 6 | G1 母集団に到達せず |
| 発火5件の after | すべて既存 Hit | Hit 改善に寄与せず（最終 Hit は維持） |

**結論:** V2.1 厳密化（TN-A∧C∧D + fire_cap）は churn 抑制には成功したが、G1 到達前にゲート落ちし **効果不足で FAIL**。Flag は既定 OFF 維持。CE-V2 には進まない。再挑戦時は mid_cap / NEAR 帯の再設計が必要。

## Artifacts

- `C:\win5-ai\compare\v2_rp_v2_a_ab_summary.json`
- `C:\win5-ai\compare\v2_rp_v2_a_control_fire_path.csv`
- `C:\win5-ai\compare\v2_rp_v2_a_treatment_fire_path.csv`
- `C:\win5-ai\compare\v2_rp_v2_a_winner_rescue.csv`

## Notes

- Control must equal PE-V2-A PASS lock (218/14/18) before Treatment is judged.
- Hard Gate is Hit > 218 only; Purchase Δ is analyzed but not a PASS/FAIL gate.
- CE-V2 is blocked until this RP-V2-A PASS/FAIL judgment is accepted.
