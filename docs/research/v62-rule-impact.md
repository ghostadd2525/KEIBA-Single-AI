# Version62 — Exclusion Rule Impact

**Date:** 2026-07-28  
**Subject:** 条項別 Exclusion 解除の Shadow / Hit 影響（反実仮想）  
**Locks:** 実装・閾値・Trigger・Polarity・Prediction・PE・Production 変更禁止  
**関連:** `v62-exclusion-roi.md` / W-S3 Exclusion Shadow

---

## 対象条項（W-S3 Top3）

| 条項 | primary 発火 n | False | True | 主 World |
|---|---:|---:|---:|---|
| `CORE_EXCL:sfp↑_F+` | 77 | 36 | 41 | core 77 |
| `CORE_EXCL:mid_band_open_ForbidDef` | 64 | 32 | 32 | core 55 / midupper 9 |
| `CORE_EXCL:chaos↑_F+` | 30 | 16 | 14 | core 24 / midhole 6 |

---

## 条項別インパクト（解除シミュレーション）

### `CORE_EXCL:sfp↑_F+`

| 観点 | 結果 |
|---|---|
| Released | 77 |
| WA aligned 回収 | +36（False 36 のみ） |
| True 巻き込み | 41（soft 19 + misaligned 22） |
| Hit / Purchase / rank710 / other_miss | **すべて Δ0** |
| False サブセット既存 Hit | 36/36（観測；因果ではない） |

**評価:** 件数最大だが True 比率が高い。条項一律解除は **WA 汚染（+41 soft/mis）** が大きい。

---

### `CORE_EXCL:mid_band_open_ForbidDef`

| 観点 | 結果 |
|---|---|
| Released | 64 |
| WA aligned 回収 | +32 |
| True 巻き込み | 32（soft 16 + misaligned 16） |
| Hit 系 | **Δ0** |
| False サブセット既存 Hit | 30/32 |

**評価:** False/True 半々。一律解除は sfp より規模は小さいが、同様に True 汚染あり。

---

### `CORE_EXCL:chaos↑_F+`

| 観点 | 結果 |
|---|---|
| Released | 30 |
| WA aligned 回収 | +16 |
| True 巻き込み | 14（soft 5 + misaligned 9） |
| Hit 系 | **Δ0** |
| False サブセット既存 Hit | 14/16 |

**評価:** 規模最小。ROI（Hit）効果なし。ラベル是正も限定的。

---

## 比較：False のみ vs 条項一律

| 戦略 | Released | WA+ | WA+/Released | Hit Δ | True 誤解放 |
|---|---:|---:|---:|---:|---:|
| False Exclusion のみ | 51 | 51 | **1.00** | 0 | 0 |
| sfp 一律 | 77 | 36 | 0.47 | 0 | 41 |
| mid_band 一律 | 64 | 32 | 0.50 | 0 | 32 |
| chaos 一律 | 30 | 16 | 0.53 | 0 | 14 |
| 全 Near 解除 | 104 | 51 | 0.49 | 0 | 53 |

**ルール設計上の含意（実装しない）:** もし将来 Exclusion を触るなら「条項削除」より **False 判定に相当する Narrowing** の方が WA 効率が良い。ただし本フェーズでは **いずれも Hit ROI は出ない**。

---

## Hit / miss バケツ（cohort 104・全アーム共通）

PE 固定のため、どの解除アームでも同一:

| Hit | rank46 | rank710 | other_miss |
|---:|---:|---:|---:|
| 78 | 14 | 9 | 3 |

---

## 禁止事項（再確認）

本ドキュメントは影響の **測定** のみ。条項削除・閾値変更・Rewrite は **未承認・未実施**。
