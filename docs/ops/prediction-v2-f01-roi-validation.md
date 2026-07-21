# PV2-F01 ROI Validation Report

**Date:** 2026-07-21  
**Corpus:** Version 1 Baseline Phase255 — **285 races** (`compare/phase255_fire_path.csv`)  
**Market join:** `data/demo_daily_outputs/*/demo_runners_pace_market_features.csv`（勝者名×race_id）  
**Scope:** 解析のみ（Prediction V1 / Collector / ETL 変更なし）  
**Feature Contract:** 条件付き承認 → 本 ROI で実装可否を判定

---

## 0. 判定

| 項目 | 値 |
|------|-----|
| **ROI 十分か** | **NO → チケット化見送り** |
| Decision | `HOLD_NO_TICKET` |
| 根拠 | odds-improvable misses=13/69 (18.8%); threshold n>=10 and rate>=20%; structural_pool_misses=14 |

判定閾値（本 Validation で固定）: ミスレースのうち **odds 改善可能 ≥ 10 件 かつ ≥ 20%**。

---

## 1. Version1（285R）結果分布

Phase255 最終（`after_miss_group`）:

| bucket | n | 割合 |
|--------|--:|-----:|
| hit | 216 | 75.8% |
| rank46 | 35 | 12.3% |
| rank710 | 15 | 5.3% |
| other_miss | 19 | 6.7% |
| **合計** | **285** | 100% |

参考（Phase255 公式ゲート）: Hit 216 / rank710 15 / other_10_13 14。本表の rank46 は最終 `rank46_miss` 集計（Hit 以外の内訳）。

データ結合:

| 項目 | n |
|------|--:|
| 勝者 odds マッチ | 260 |
| track code > 0 | 257 |
| market_available | 260 |

---

## 2. 改善可能レース数・改善率

**対象ミス:** 69 レース（285 − hit）

| 指標 | 値 |
|------|-----|
| **odds 改善可能レース数** | **13** |
| **改善率（対ミス）** | **18.8%** |
| 改善率（対 285） | 4.6% |
| odds 信号ありだが V2-A では効きにくい（人気側） | 0 |
| 改善が期待できない（構造・深位・大穴飽和等） | 56 |

### bucket 別 odds 改善可能

| bucket | n | odds 改善可能 | 率 |
|--------|--:|-------------:|---:|
| rank46 | 35 | 11 | 31.4% |
| rank710 | 15 | 2 | 13.3% |
| other_miss | 19 | 0 | 0.0% |

---

## 3. 解析方法（再現条件）

PV2-F01 Contract の V2-A（α=0.03, \|δ\|≤0.05）を前提に、**再学習なしの小さなオッズギャップ補正**で理論的に動かしうるミスを抽出した。

**odds 改善可能**の条件（すべて）:

1. 最終が miss（hit 以外）
2. 勝者 odds が結合でき market_available
3. 候補プール内（`in_candidate_pool=1`）— プール外はスコア補正では救済不能
4. `gap = odds/odds_min` ∈ [1.2, 5]（rank46）または [1.2, 4]（rank710）
5. 推定 δ ≥ 0.01

**含意:** 本数は「確定 Hit 化」ではなく **V2-A が効きうる上限候補**。実 Canary で検証が必要。

---

## 4. odds が効いたケース（候補）

件数: **13**

クラス内訳:

| roi_class | n |
|-----------|--:|
| odds_improvable_rank46 | 11 |
| odds_improvable_rank710_weak | 2 |

代表例（最大 25）:

| race_id | winner | wr | bucket | odds | gap | pop | class |
|---------|--------|---:|--------|-----:|----:|----:|-------|
| 2024-02-25-小倉-11 | カンチェンジュンガ | 6 | rank46 | 7.7 | 2.33 |  | odds_improvable_rank46 |
| 2024-04-21-福島-11 | アシャカタカ | 6 | rank46 | 15.6 | 4.33 |  | odds_improvable_rank46 |
| 2024-06-02-東京-09 | グランドカリナン | 6 | rank46 | 7.2 | 2.32 |  | odds_improvable_rank46 |
| 2025-12-06-阪神-11 | デビットバローズ | 6 | rank46 | 4.3 | 1.65 |  | odds_improvable_rank46 |
| 2026-01-04-中山-11 | カラマティアノス | 6 | rank46 | 14.8 | 4.62 |  | odds_improvable_rank46 |
| 2026-01-25-中山-11 | ショウヘイ | 6 | rank46 | 5.0 | 1.67 |  | odds_improvable_rank46 |
| 2026-01-25-小倉-11 | エラトー | 6 | rank46 | 10.5 | 3.00 |  | odds_improvable_rank46 |
| 2026-02-15-小倉-11 | ジョーメッドヴィン | 6 | rank46 | 11.2 | 3.03 |  | odds_improvable_rank46 |
| 2026-03-01-阪神-10 | ベルウェザー | 6 | rank46 | 13.5 | 4.66 |  | odds_improvable_rank46 |
| 2026-03-08-中山-10 | ブレイクフォース | 6 | rank46 | 14.0 | 3.50 |  | odds_improvable_rank46 |
| 2026-04-25-東京-11 | ゴーイントゥスカイ | 6 | rank46 | 8.1 | 3.38 |  | odds_improvable_rank46 |
| 2024-01-21-京都-11 | ウィリアムバローズ | 7 | rank710 | 5.5 | 2.75 |  | odds_improvable_rank710_weak |
| 2026-04-19-中山-10 | ナムラフランク | 8 | rank710 | 8.5 | 1.60 |  | odds_improvable_rank710_weak |

詳細 CSV: `docs/ops/_pv2_f01_roi_validation_detail.csv`

---

## 5. track が効いたケース（仮説）

F01 では γ=0（馬場項オフ）のため、**実装初期の直接効果は 0**。  
それでも「稍重/重/不良 × 境界ミス × プール内」は将来 PV2-T01 の仮説母集団。

| 指標 | n |
|------|--:|
| track 仮説（rank46/710 境界） | 11 |
| track 非良だが未証明ミス | 3 |
| track データなし | 9 |

代表例（track 仮説・最大 15）:

| race_id | winner | wr | bucket | track | code |
|---------|--------|---:|--------|-------|-----:|
| 2024-01-21-京都-11 | ウィリアムバローズ | 7 | rank710 | 重 | 3 |
| 2024-02-25-小倉-11 | カンチェンジュンガ | 6 | rank46 | 稍重 | 3 |
| 2024-02-25-阪神-10 | ナナオ | 6 | rank46 | 重 | 3 |
| 2024-06-02-東京-09 | グランドカリナン | 6 | rank46 | 稍重 | 3 |
| 2024-06-23-東京-10 | ニシノカシミヤ | 6 | rank46 | 重 | 3 |
| 2024-07-07-函館-11 | キミノナハマリア | 6 | rank46 | 稍重 | 3 |
| 2025-12-14-中京-11 | モズナナスター | 8 | rank710 | 稍重 | 3 |
| 2026-02-15-小倉-11 | ジョーメッドヴィン | 6 | rank46 | 稍重 | 3 |
| 2026-03-08-中山-10 | ブレイクフォース | 6 | rank46 | 稍重 | 3 |
| 2026-04-05-中山-11 | ジュタ | 6 | rank46 | 稍重 | 3 |
| 2026-04-25-京都-10 | マイノワール | 7 | rank710 | 稍重 | 3 |

**結論（track）:** F01 V2-A（γ=0）では改善寄与なし。ROI 判定は **odds 側のみ**で行う。

---

## 6. 改善が期待できないケース

ミス 69 件中、主に以下（重複なく roi_class で分類）:

| クラス | n | 理由 |
|--------|--:|------|
| not_improvable_structural_pool | 14 | プール外 — 微小 δ では membership 不能 |
| not_improvable_too_deep | 5 | 着順 11+ — δ≤0.05 で届かない |
| not_improvable_longshot_saturated | 8 | gap>8 — 補正飽和・ノイズ |
| odds_signal_v2a_limited_favorite | 0 | 人気側ミス — 現行 V2-A は δ≈0 |
| not_improvable_unclear / no_odds | 29 | 条件外・データ欠落 |

構造プール外の例（最大 15）:

| race_id | winner | wr | bucket | first_loss |
|---------|--------|---:|--------|------------|
| 2024-02-04-東京-11 | サクラトゥジュール | 13 | other_miss | candidate_pool |
| 2024-02-11-京都-10 | ゴーゴーユタカ | 6 | rank46 | after_delete |
| 2024-02-11-東京-11 | ジャスティンミラノ | 9 | rank710 | candidate_pool |
| 2024-02-18-東京-11 | ペプチドナイル | 13 | other_miss | candidate_pool |
| 2024-03-10-阪神-11 | エトヴプレ | 6 | rank46 | after_delete |
| 2024-04-14-中山-10 | セイウンプラチナ | 14 | other_miss | candidate_pool |
| 2024-05-12-東京-11 | テンハッピーローズ | 11 | other_miss | re_pick |
| 2024-05-12-京都-10 | ボーデン | 12 | other_miss | re_pick |
| 2024-05-26-東京-11 | ダノンデサイル | 13 | other_miss | candidate_pool |
| 2024-06-02-京都-10 | ベリーヴィーナス | 10 | rank710 | candidate_pool |
| 2024-06-23-函館-11 | サヴァ | 12 | other_miss | re_pick |
| 2024-06-30-小倉-10 | レリジールダモーレ | 11 | other_miss | candidate_pool |
| 2025-12-13-中山-10 | モンドプリューム | 9 | rank710 | re_pick |
| 2025-12-21-阪神-10 | ルシュヴァルドール | 11 | other_miss | re_pick |
| 2025-12-27-中山-09 | アンビバレント | 13 | other_miss | candidate_pool |

---

## 7. ROI 総合と次アクション

| 観点 | 評価 |
|------|------|
| odds による改善余地 | **境界的（件数は足りるが率 18.8% < 20%）** |
| track（F01） | 寄与なし（γ=0）。仮説母集団 11 件は T01 候補 |
| V1 Baseline 破壊リスク | 低（Flag OFF 同一性 + δ 硬上限） |
| 実装チケット | **作成しない（HOLD）** |

### 再判定オプション（チケット化前）

1. 閾値を「n≥10 かつ ≥15%」へ緩和する（ステークホルダー合意が必要）  
2. Canary 対象を **rank46 セグメント**に限定した Contract 1.1（rank46 内 31.4% は局所 ROI あり）  
3. V2-A に人気側項を足す改訂（現状 favorite ミスはほぼ拾えない）  

いずれも **Contract 改訂 + ROI 再計測**が前提。現行 1.0 のままでは実装チケット化しない。

### 実装チケット（ROI YES の場合のみ）

- （本判定では未作成）

---

## 8. 注意（解釈限界）

1. 本解析は **オフラインヒューリスティック**であり、実スコア差を再計算していない。  
2. Win5 Product の Hit 定義と Prediction Core Top1 はレイヤが異なる。F01 は Core 側 AB が本番検証。  
3. Phase255 は Product BKC。Core V2 は独立 Flag 経路。
