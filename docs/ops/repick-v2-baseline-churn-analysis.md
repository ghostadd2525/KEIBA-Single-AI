# RePick v2 — Baseline Verification & Churn Breakdown

**Date:** 2026-07-21  
**Status:** Analysis only（**設計変更禁止** / AB Report 採択）  
**Parent:** [`repick-v2-ab-report.md`](./repick-v2-ab-report.md)  

---

## 1. Baseline Verification

### 1.1 数値対照

| ソース | Hit | rank710 | other_miss | n |
|--------|----:|--------:|-----------:|--:|
| Exit 契約（Version1 Final） | **216** | **15** | **19** | 285 |
| Phase255 CSV（`phase255_fire_path.csv`） | **216** | **15** | **19** | 285 |
| 本次 AB Control（Flag OFF） | **215** | **16** | **19** | 285 |
| 本次 AB Treatment（Flag ON） | 220 | 11 | 19 | 285 |

- 契約 vs Phase255 CSV: **一致**（216/15/19）
- 契約 vs AB Control: **不一致**（Hit −1, rank710 +1）

### 1.2 レース単位の差異（Phase255 CSV vs AB Control）

- `after_miss_group` 不一致: **1** レース
- Hit のみ Phase255: `['2026-03-29-中山-11']`
- Hit のみ Control: `[]`
- rank710 のみ Phase255: `[]`
- rank710 のみ Control: `['2026-03-29-中山-11']`

| race_id | Phase255 | Control | in_repick b→c | in_multi b→c | pool b→c |
|---------|----------|---------|---------------|--------------|----------|
| 2026-03-29-中山-11 | Hit | rank710_hidden_miss | 1→1 | **1→0** | 9.0→9 |

**該レースの詳細:**

| 項目 | Phase255 | AB Control |
|------|----------|------------|
| winner | サンデーファンデー（rank7） | 同左 |
| in_pool / in_repick / in_purchase | 1 / 1 / 0 | 1 / 1 / 0（**同一**） |
| first_loss_stage | purchase | purchase |
| `db_rescued` | **1** | **0** |
| `in_multi_after_delete` | **1** → Hit | **0** → rank710_hidden_miss |
| `repick_v2` | （未存在） | `disabled`（Flag OFF） |

→ 差分は **RePick 段ではなく Delete/DB overlay 後の multi 生存**。コーパス全体で `in_repick` / pool / purchase の不一致はこの 1 件の multi 以外 **0 件**。

### 1.3 評価データ / 設定 / Feature Flag / 入力データの差分

| 軸 | Phase255 Final | 本次 AB Control | 差分有無 |
|----|----------------|-----------------|----------|
| コーパス | 285R（labeled_test） | 同左（`load_winners_and_jobs`） | なし |
| Phase195 lock / after sets | `load_after_sets` + `load_race_lock` | 同左 | なし（ロック入力は共通） |
| CP+RP | ON（combined_max=1） | ON（combined_max=1） | なし |
| DB overlay | ON | ON | **意図は同じだが、該レースで `db_rescued` 結果が不一致** |
| EN-1′ Safe | ON（en3/4 OFF） | ON（en3/4 OFF） | なし |
| Compress (CM) | OFF | OFF | なし |
| V2 sidecars (T-W/T-E/…/T-R7N) | 未適用 | 明示 OFF | 実質なし |
| **RePick v2** | 未存在 | Flag OFF（`reason=disabled`） | **該レース差分の原因ではない** |
| 評価ハーネス | `p252.run_full_corpus` | `_run_repick_v2_ab_evaluation.evaluate_one` | **あり（DB overlay 適用結果がズレ）** |
| 入力バンドル | `p182.load_race_bundle` | 同左 | pool/repick 一致から入力差は小さい |

#### 解釈

1. **Flag / スタック意図は Phase255 と揃っている。** RePick v2 は Control で OFF。
2. **216→215 / 15→16 の差分は単一レース `2026-03-29-中山-11` のみ。** pool・repick・purchase は一致し、**DB rescue（multi 後）だけが不一致**。
3. したがって Exit AB-I1 失敗の主因は「RePick v2 の副作用」ではなく、**AB ハーネスの Delete/DB overlay 再現が Phase255 CSV と 1 レース分ズレたこと**。
4. Treatment Hit 220 は Control 215 基準では Δ=+5・Hit損失0だが、契約 Baseline 216 との厳密比較には **Control を Phase255 に再ロック**する必要がある。

---

## 2. Churn Breakdown（発火 100 件）

定義:

| ラベル | 定義 |
|--------|------|
| 順位変更なし | 発火したが repick メンバー集合が不変（victim/cand 欠落等） |
| 順位変更あり | cand 挿入 + victim 除外により集合が変化（N 不変 displacement） |
| Hit改善 | Control≠Hit → Treatment=Hit |
| Hit維持 | Control=Hit かつ Treatment=Hit |
| Hit悪化 | Control=Hit → Treatment≠Hit |
| Hit非該当 | Control・Treatment とも非 Hit |

### 2.1 集計（n=100）

| 分類 | n |
|------|--:|
| 順位変更なし | **0** |
| 順位変更あり | **100** |
| Hit改善 | **5** |
| Hit維持 | **77** |
| Hit悪化 | **0** |
| Hit非該当 | **18** |

### 2.2 クロス表

|  | Hit改善 | Hit維持 | Hit悪化 | Hit非該当 |
|--|--------:|--------:|--------:|----------:|
| 順位変更なし | 0 | 0 | 0 | 0 |
| 順位変更あり | 5 | 77 | 0 | 18 |

### 2.3 切り分け（広い vs 強い）

| 仮説 | 根拠となる件数 | 判定 |
|------|----------------|------|
| **発火条件が広い** | Hit維持 77 + Hit非該当 18 = **95** / 100（うち既 Hit への無意味 churn が主） | **主因** |
| **補正ロジックが強すぎる（破壊的）** | Hit悪化 **0** | **該当薄い**（0 または極小なら非主因） |
| 補正が効いた（望ましい強さ） | Hit改善 **5** | 効果は限定的 |

**結論:** 発火 100 件の大半は **メンバー集合を入れ替える churn** であり、最終 Hit を壊す「強すぎる補正」より、**NEAR 匿名トリガが不要レース（既 Hit 等）にまで発火する広さ**が支配的。

---

## 3. 総合

1. Baseline ズレ（216→215）は **単一レースの DB rescue 再現ズレ**（`2026-03-29-中山-11`）。RePick v2 ON/OFF の直接効果ではない。
2. Churn 失敗（Exit AB-C*）は **発火条件の広さ**が主因（Hit維持77）。補正の破壊力は **Hit悪化 0** で非主因。
3. 設計改訂は本レポートでは行わない（禁止どおり）。

JSON: `compare/repick_v2_baseline_churn_analysis.json`
