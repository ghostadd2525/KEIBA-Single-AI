# Version62 — Exclusion ROI Simulation

**Date:** 2026-07-28  
**Subject:** W-S3 Exclusion Shadow（False Exclusion 51 / True Exclusion 53）を解除した場合の ROI 反実仮想  
**Locks:** Trigger / Signal / Threshold / Polarity / Prediction / PE / Production — **変更禁止・実装禁止**  
**入力:** `docs/implementation/w-s3-exclusion-104-rows.jsonl` + 285R fixture Hit + dual-eval Near World

---

## 結論（1行）

Exclusion を緩めても **既存 PE top1 の Hit / Purchase / miss バケツは Δ0**。改善するのは Shadow の **Positive Match / Winner Alignment** のみ。**賭け ROI としては不足（C）**。

---

## 方法（反実仮想のみ）

| 層 | 扱い |
|---|---|
| Prediction / PE pick | **固定**（285R `hit_at_1` を観測） |
| Exclusion | 条項・種別ごとに「Near Match primary World を採用」とみなす（コード未変更） |
| ROI（本フェーズ） | ① Hit/Purchase/rank710/other_miss ② WA / PM（Shadow KPI） |

**定義**

- **False Exclusion 解除:** `kind=false_exclusion`（51）の primary Near World を V44 World とみなす  
- **True Exclusion 維持:** `kind=true_exclusion`（53）は引き続き `unsatisfied`  
- **条項別解除:** primary で当該 `CORE_EXCL:*` が発火したレースのみ解除（True/False 混在）

---

## ① False Exclusion 解除 Simulation

| 指標 | Baseline（Exclusion 維持） | False のみ解除 | Δ |
|---|---:|---:|---:|
| 対象 cohort | 104 | 104 | — |
| Released | 0 | **51** | +51 |
| Hit（既存 pick） | 78 | 78 | **0** |
| Purchase（=Hit@1） | 78 | 78 | **0** |
| rank710 | 9 | 9 | **0** |
| other_miss | 3 | 3 | **0** |
| WA aligned | 0 | **51** | **+51** |
| PM rate | 0% | **49.0%** | +49pp |

解除後 World 分布（51 のみ）: `core_world` 37 / `midupper` 8 / `midhole` 6（残り 53 は unsatisfied）

False 51 の既存 Hit: **45/51（88.2%）** — すでに当たっているレースが多く、World ラベル修正だけでは Purchase は増えない。

---

## ② True Exclusion 維持 Simulation

| 指標 | 値 |
|---|---|
| True 53 の扱い | Exclusion 維持 → `unsatisfied` |
| True を誤って解除した場合の WA | aligned 0 / soft 25 / **misaligned 28** |
| True 既存 Hit | 33/53（62.3%） |

**含意:** True を緩めると PM は増えるが WA aligned は増えない（soft/misaligned のみ）。**True 維持は正しい**。False 解除アームと「True 維持＋False 解除」は数値上同一。

---

## ③ 条項別 Simulation（primary 発火）

| 条項 | Released | WA aligned | Δ WA | Hit Δ | うち False | False 内 Hit（観測） |
|---|---:|---:|---:|---:|---:|---:|
| `CORE_EXCL:sfp↑_F+` | 77 | 36 | +36 | 0 | 36 | 36/36 |
| `CORE_EXCL:mid_band_open_ForbidDef` | 64 | 32 | +32 | 0 | 32 | 30/32 |
| `CORE_EXCL:chaos↑_F+` | 30 | 16 | +16 | 0 | 16 | 14/16 |

条項単独解除は True も巻き込むため、**WA 効率は False のみ解除（+51 / 51 released）より劣る**（sfp: +36/77）。

---

## ④〜⑧ 変化予測サマリ

| # | 指標 | False 解除 | True 維持 | 全 Near 解除 | 条項別（最大 sfp） |
|---|---|---:|---:|---:|---:|
| ④ | Hit | **0** | 0 | **0** | **0** |
| ⑤ | Purchase | **0** | 0 | **0** | **0** |
| ⑥ | rank710 | **0** | 0 | **0** | **0** |
| ⑦ | other_miss | **0** | 0 | **0** | **0** |
| ⑧ | Winner Alignment（aligned） | **+51** | （False 解除と同） | +51（+ soft25 / mis28） | +16〜+36 |

全 Near 解除（104）でも WA aligned は +51 止まり。追加 53 は soft/misaligned であり **ROI 代理としても悪化方向**。

---

## 285R 全体への換算

| 項目 | 値 |
|---|---|
| Full 285 Hit | 218（固定） |
| Exclusion 解除による Full Hit Δ | **0**（PE 未変更） |
| Shadow: Unsatisfied∩Must→Exclude 104 内 PM | 0 → 最大 104（全解除）または 51（False のみ） |

---

## 解釈

1. **賭け ROI（Hit/Purchase）:** Exclusion 単独緩和では **期待値ゼロ**（Prediction 経路と非結合）。  
2. **Shadow ラベル品質:** False 51 解除で WA aligned +51 — 設計上の過剰 Exclusion 是正効果は大きいが、**Purchase には乗らない**。  
3. **次に ROI を出す条件（本フェーズでは未実施）:** World→PE/Policy 結合の別 Decision。本シミュレーションはそれを承認しない。

---

## 変更していないもの

Trigger / Signal / Threshold / Polarity ADR / Prediction / PE / Production / Exclusion 実装 — **すべて未変更**。
