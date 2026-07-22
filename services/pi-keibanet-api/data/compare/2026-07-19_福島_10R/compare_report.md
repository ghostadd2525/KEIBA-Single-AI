# Win5AI vs PI API 比較レポート

## 対象レース

| 項目 | 値 |
|------|-----|
| 日付 | 2026-07-19 |
| 会場 | 福島 |
| レース番号 | 10R |
| numeric_race_id | 202603020810 |
| Legacy ディレクトリ | `C:\win5-ai\data` |
| PI ディレクトリ | `C:\win5-ai\KEIBA-Single-AI\services\pi-keibanet-api\data\pipeline\2026-07-19` |

## 総合結果

- **一致率**: 93.41%
- **調整一致率** (netkeibaオッズ/人気タイミング差除外): 98.57%
- **目標**: 99% 以上（調整一致率で判定）
- **判定**: **FAIL**
- **差分行数**: 638

## Before / After 一致率比較

| データセット | Before | After | 変化 |
|-------------|--------|-------|------|
| **総合** | 55.74% | 93.41% | +37.67% |
| runners | 85.52% | 90.00% | +4.48% |
| horse_history_raw | 0.00% | 94.87% | +94.87% |
| runners_pace_market_features | 46.01% | 74.04% | +28.03% |
| 差分行数 | 401 | 638 | +237 |

*Before: horse_history が初回 HTML のみ fetch（ajax 未使用）*

## Remaining Difference

- **残差件数（全分類）**: 638
- **残差件数（netkeiba_spec除外）**: 138
- **残差一致率（4分類ベース）**: 93.41%
- **調整一致率（netkeiba_spec除外）**: 98.57%
- **比較セル総数**: 9678

| 分類 | 件数 | 説明 |
|------|------|------|
| `parse_difference` | 0 | HTMLパース差（sex/age/馬番/斤量/jockey 等） |
| `missing_data` | 36 | 片方のみ値あり（取得失敗・欠損） |
| `feature_calc_difference` | 102 | 特徴量計算差（history_score / running_style 等） |
| `netkeiba_spec_difference` | 500 | netkeiba仕様・取得タイミング差（odds/人気/HTML構造） |

### Legacy history 正規化 (Phase Y-2)

- 期待 horse_id 数: 12
- 正規化前 Legacy horse_id 数: 4
- 欠損していた horse_id (8): 2017101772, 2021105375, 2022102532, 2022103405, 2022103522, 2022104669, 2022104781, 2022106772
- AJAX 再取得した horse_id (8): 2017101772, 2021105375, 2022102532, 2022103405, 2022103522, 2022104669, 2022104781, 2022106772
- 正規化出力: `C:\win5-ai\legacy_normalized\2026-07-19_福島_10R\horse_history_raw.csv`

## 差分原因分類

| 原因分類 | 件数 | 説明 |
|---------|------|------|
| `netkeiba_spec_difference` | 500 | netkeiba仕様差（取得タイミング・HTML構造・馬の増減） |
| `feature_calc_difference` | 102 | 特徴量差（集計ロジックまたは入力データ差） |
| `missing_data` | 36 | 欠損項目（片方のみ値あり） |

## runners

| 指標 | Legacy | PI |
|------|--------|-----|
| 行数 | 12 | 12 |
| horse_id 数 | 12 | 12 |
| 共通 horse_id | 12 | |
| Legacy のみ | 0 | |
| PI のみ | 0 | |
| 比較セル数 | 240 | |
| 一致セル数 | 216 | |
| **一致率** | **90.00%** | |
| 欠損 (Legacy) | 0 | |
| 欠損 (PI) | 24 | |

### 差分詳細（上位20件）

| horse_id | 列 | Legacy | PI | 差分 | 原因 |
|----------|-----|--------|-----|------|------|
| 2022103522 | `odds` | 14.3 | nan |  | netkeiba_spec_difference |
| 2022103522 | `popularity` | 5 | nan |  | netkeiba_spec_difference |
| 2022104781 | `odds` | 43.7 | nan |  | netkeiba_spec_difference |
| 2022104781 | `popularity` | 10 | nan |  | netkeiba_spec_difference |
| 2022102532 | `odds` | 188.1 | nan |  | netkeiba_spec_difference |
| 2022102532 | `popularity` | 12 | nan |  | netkeiba_spec_difference |
| 2022104635 | `odds` | 2.3 | nan |  | netkeiba_spec_difference |
| 2022104635 | `popularity` | 1 | nan |  | netkeiba_spec_difference |
| 2022106772 | `odds` | 42.0 | nan |  | netkeiba_spec_difference |
| 2022106772 | `popularity` | 9 | nan |  | netkeiba_spec_difference |
| 2022106825 | `odds` | 5.2 | nan |  | netkeiba_spec_difference |
| 2022106825 | `popularity` | 3 | nan |  | netkeiba_spec_difference |
| 2022100781 | `odds` | 4.6 | nan |  | netkeiba_spec_difference |
| 2022100781 | `popularity` | 2 | nan |  | netkeiba_spec_difference |
| 2021106826 | `odds` | 33.1 | nan |  | netkeiba_spec_difference |
| 2021106826 | `popularity` | 8 | nan |  | netkeiba_spec_difference |
| 2017101772 | `odds` | 24.8 | nan |  | netkeiba_spec_difference |
| 2017101772 | `popularity` | 6 | nan |  | netkeiba_spec_difference |
| 2022104669 | `odds` | 5.7 | nan |  | netkeiba_spec_difference |
| 2022104669 | `popularity` | 4 | nan |  | netkeiba_spec_difference |
| ... | | | | | 他 4 件は compare_diff.csv 参照 |

## horse_history_raw

| 指標 | Legacy | PI |
|------|--------|-----|
| 行数 | 226 | 230 |
| horse_id 数 | 12 | 12 |
| 共通 horse_id | 12 | |
| Legacy のみ | 0 | |
| PI のみ | 0 | |
| 比較セル数 | 8814 | |
| 一致セル数 | 8362 | |
| **一致率** | **94.87%** | |
| 欠損 (Legacy) | 0 | |
| 欠損 (PI) | 452 | |

### 差分詳細（上位20件）

| horse_id | 列 | Legacy | PI | 差分 | 原因 |
|----------|-----|--------|-----|------|------|
| 2021106826 [0] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [0] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [1] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [1] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [2] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [2] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [3] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [3] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [4] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [4] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [5] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [5] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [6] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [6] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [7] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [7] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [8] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [8] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| 2021106826 [9] | `odds_today` | 51.7 | nan |  | netkeiba_spec_difference |
| 2021106826 [9] | `popularity_today` | 8.0 | nan |  | netkeiba_spec_difference |
| ... | | | | | 他 432 件は compare_diff.csv 参照 |

## runners_pace_market_features

| 指標 | Legacy | PI |
|------|--------|-----|
| 行数 | 12 | 12 |
| horse_id 数 | 12 | 12 |
| 共通 horse_id | 12 | |
| Legacy のみ | 0 | |
| PI のみ | 0 | |
| 比較セル数 | 624 | |
| 一致セル数 | 462 | |
| **一致率** | **74.04%** | |
| 欠損 (Legacy) | 36 | |
| 欠損 (PI) | 24 | |

**Legacy のみの列** (11): front_count, horse_count, leg_base_chaos, leg_favorite_bias, leg_field_pressure, leg_style_fit_bonus, leg_upset_risk, pace_collapse_risk, race_leg_difficulty, style_entropy, unknown_count

**PI のみの列** (18): course, date, date_race, numeric_race_id_race, pace_pressure, pace_pressure_rate, race_name, race_name_race, race_number, senkou_count, target_distance, target_surface, track_condition, track_condition_race, turn, turn_race, weather, weather_race

### 差分詳細（上位20件）

| horse_id | 列 | Legacy | PI | 差分 | 原因 |
|----------|-----|--------|-----|------|------|
| 2022103522 | `distance_score` | 0.0 | 0.686 | 0.6860 | feature_calc_difference |
| 2022103522 | `history_score` | 0.765704 | 0.745704 | 0.0200 | feature_calc_difference |
| 2022103522 | `layoff_days` | nan | 63.0 |  | missing_data |
| 2022103522 | `odds` | 14.3 | nan |  | netkeiba_spec_difference |
| 2022103522 | `oikomi_count` | 2 | 1 | 1.0000 | feature_calc_difference |
| 2022103522 | `popularity` | 5 | nan |  | netkeiba_spec_difference |
| 2022103522 | `same_distance_avg_finish` | nan | 4.8 |  | missing_data |
| 2022103522 | `same_distance_count` | 0 | 20 | 20.0000 | feature_calc_difference |
| 2022103522 | `same_surface_avg_finish` | nan | 4.8 |  | missing_data |
| 2022103522 | `same_surface_count` | 0 | 20 | 20.0000 | feature_calc_difference |
| 2022103522 | `sashi_count` | 3 | 4 | 1.0000 | feature_calc_difference |
| 2022103522 | `style_distance_fit_weight` | 0.8 | 0.9 | 0.1000 | feature_calc_difference |
| 2022104781 | `distance_score` | 0.0 | 0.593 | 0.5930 | feature_calc_difference |
| 2022104781 | `history_score` | 0.498973 | 0.478973 | 0.0200 | feature_calc_difference |
| 2022104781 | `layoff_days` | nan | 57.0 |  | missing_data |
| 2022104781 | `odds` | 43.7 | nan |  | netkeiba_spec_difference |
| 2022104781 | `oikomi_count` | 2 | 1 | 1.0000 | feature_calc_difference |
| 2022104781 | `popularity` | 10 | nan |  | netkeiba_spec_difference |
| 2022104781 | `same_distance_avg_finish` | nan | 7.5 |  | missing_data |
| 2022104781 | `same_distance_count` | 0 | 8 | 8.0000 | feature_calc_difference |
| ... | | | | | 他 142 件は compare_diff.csv 参照 |

## 推奨アクション

- **特徴量差**: 入力 history 行が一致しているか確認後、features.py の式を再検証
- **netkeiba仕様差**: 取得時刻差による odds/人気変動、または HTML 構造変更を確認
- **欠損項目**: PI pipeline の fetch 失敗ログを確認
