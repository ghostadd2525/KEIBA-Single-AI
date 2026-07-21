# PV2-F01 Feature Contract

**Contract ID:** `expect-prediction-v2-market-features/1.0`  
**Status:** **ARCHIVED** — Version 2 対象外（2026-07-21 採択）  
**Decision:** ROI 18.8% < 20% → 実装チケットなし  
**Archive stub:** [`prediction-v2-f01-feature-contract-ARCHIVED.md`](./prediction-v2-f01-feature-contract-ARCHIVED.md)  
**Successor:** [`prediction-v1-miss69-theme-roi-review.md`](./prediction-v1-miss69-theme-roi-review.md)  
**Parent design:** [`prediction-v2-design-review.md`](./prediction-v2-design-review.md)  
**Date:** 2026-07-21  

## 変更禁止

| 領域 | 扱い |
|------|------|
| Collector（Planner/Queue/Scheduler/…） | **変更禁止** |
| ETL Bridge | **変更禁止** |
| Prediction V1（凍結 28 特徴・現行 Scorer 既定経路） | **変更禁止** |
| Phase255 / Bundle `single-prediction-bundle/2.0` | **変更禁止** |

本契約は **V2 専用 Feature + V2-A 後段補正** の正本である。実装は本契約承認後のみ。

---

## 0. 用語

| 用語 | 定義 |
|------|------|
| **V1 行列** | `win5_lgbm_ranker_features.json` の 28 列。値・順序・意味を変えない |
| **V2 派生列** | 本契約 §1 の列。V1 に追加される独立セット |
| **入力行** | `FeatureLoader.load()` が返す `FeatureLoadResult.frame` の 1 馬行 |
| **Source 論理名** | データの論理起源（odds / track）。Collector モジュールへの参照ではない |
| **Flag** | `PREDICTION_V2_MARKET_FEATURES`（既定 `false`） |

---

## 1. 追加する特徴量一覧

V2 派生列は **すべて `v2_` 接頭辞**。V1 列名との衝突を禁止する。

| # | feature_name | dtype | 役割 | V2-A での利用 |
|---|--------------|-------|------|----------------|
| 1 | `v2_log_odds` | float64 | 単勝オッズの対数 | 補正入力 |
| 2 | `v2_odds_rank_in_race` | float64 | レース内オッズ順位（1=最短オッズ） | 補正入力 |
| 3 | `v2_odds_gap_to_favorite` | float64 | 当該オッズ / レース最短オッズ | **主補正入力** |
| 4 | `v2_implied_prob` | float64 | 1/odds をレース内で正規化した示唆確率 | 補正入力（副） |
| 5 | `v2_track_condition_code` | float64 | 馬場状態コード | 補正入力（副・任意） |
| 6 | `v2_market_missing` | float64 | 市場必須欠損フラグ（0/1） | ゲート / フォールバック |
| 7 | `v2_track_missing` | float64 | 馬場欠損フラグ（0/1） | 情報のみ（補正必須ではない） |

**列順（契約固定）:** 上記 #1→#7 の順で V2 行列の末尾に連結する（V1 28 列の後ろ）。

**非追加（本契約の範囲外）:** popularity の再エンコード、frame/jockey からの新規列、P2/P3 履歴特徴。

---

## 2. Source（odds / track）

Source は **論理ソース**。Prediction は Collector API を呼ばない。

| feature | Source | Feature 行上の入力カラム（読取契約） | 備考 |
|---------|--------|--------------------------------------|------|
| `v2_log_odds` | **odds** | `odds`（必須候補） | V1 既存列と同一キー |
| `v2_odds_rank_in_race` | **odds** | 同一レース全行の `odds` | レース単位集約 |
| `v2_odds_gap_to_favorite` | **odds** | 同上 | favorite = min(odds) among valid |
| `v2_implied_prob` | **odds** | 同上 | Σ(1/odds) で正規化 |
| `v2_track_condition_code` | **track** | 最初に存在するキーを採用: `track_condition` → `condition` → `baba` → `track` | いずれも無ければ欠損 |
| `v2_market_missing` | **odds** | （派生） | odds 必須条件不成立時 1 |
| `v2_track_missing` | **track** | （派生） | track 入力が解決できない時 1 |

**禁止:** `app.data.collect` / `app.data.etl` からの直接読取。入力は `FeatureLoadResult.frame` のみ。

---

## 3. Availability

| 条件 | 内容 |
|------|------|
| **Flag OFF** | V2 列を計算しない。V1 経路のみ（出力は V1 とビット一致） |
| **Flag ON かつ市場可用** | §4 の「市場可用」を満たす → V2 列計算 + V2-A 補正適用可 |
| **Flag ON かつ市場不可用** | V2 列は欠損規約どおり埋め、**V2-A 補正は適用しない**（V1 スコアをそのまま採用）。`PREDICTION_V2_MARKET_STRICT=true` のときは当該レースを V2 評価対象外（Canary 除外） |
| **馬場** | track 系は **任意**。欠損でも市場可用なら V2-A は実施可能（track 項の補正係数は 0） |

### 市場可用（Market Available）

レース内で次をすべて満たすこと:

1. 出走行数 ≥ 2  
2. 有効 `odds`（有限かつ `odds > 0`）を持つ行が **過半数**  
3. 有効 odds の最小値 `odds_min` が有限かつ `odds_min > 0`  

満たさない → `v2_market_missing=1`（全行）、市場不可用。

### 馬場可用（Track Available）

レース単位で track 入力カラムが 1 つ以上解決でき、エンコード可能 → `v2_track_missing=0`。  
否则 → `v2_track_missing=1`、`v2_track_condition_code=0`。

---

## 4. 欠損時の挙動

| 状況 | 各特徴の値 | V2-A |
|------|------------|------|
| 行の `odds` 欠損 / ≤0 / 非有限 | 当該行: `v2_log_odds=0`, `v2_odds_gap_to_favorite=1`, `v2_implied_prob=0`, `v2_odds_rank_in_race=race_median_rank`※ | 当該行の補正 δ=0 |
| レースが市場不可用 | 全行: §1 の数値は中立値※※、`v2_market_missing=1` | **レース全体で補正オフ**（V1 順位のまま） |
| track 欠損 | `v2_track_condition_code=0`, `v2_track_missing=1` | track 項=0（市場補正は継続可） |
| STRICT=true かつ市場不可用 | 計算は中立埋め | Canary/AB からレース除外（本番は Flag OFF 推奨） |

※ `race_median_rank` = (N+1)/2（N=出走頭数）  
※※ 中立値: `v2_log_odds=0`, `v2_odds_rank_in_race=(N+1)/2`, `v2_odds_gap_to_favorite=1`, `v2_implied_prob=1/N`, codes/flags は上表どおり  

**V1 列の補完・改変は禁止。** 欠損処理は V2 列と V2-A のみ。

---

## 5. 正規化方法

定数（契約固定）:

| 定数 | 値 | 用途 |
|------|-----|------|
| `EPS` | `1e-6` | log / 除算安定化 |
| `ODDS_CLIP_MIN` | `1.01` | log 入力下限クリップ |
| `ODDS_CLIP_MAX` | `999.0` | log 入力上限クリップ |

### 計算式（契約）

レース内の有効 odds 集合を \(O = \{o_i\}\)、\(o_{\min} = \min O\) とする。

1. **クリップ**  
   \(o'_i = \mathrm{clip}(o_i,\ \mathrm{ODDS_CLIP_MIN},\ \mathrm{ODDS_CLIP_MAX})\)

2. **`v2_log_odds`**  
   \(\log(o'_i + \mathrm{EPS})\)  
   （自然対数）

3. **`v2_odds_rank_in_race`**  
   \(o'_i\) 昇順で rank（最短=1）。同値は平均順位（dense ではなく average rank）。  
   出力は float。追加の [0,1] 正規化は **しない**（補正側で使用時に変換）。

4. **`v2_odds_gap_to_favorite`**  
   \(o'_i / o_{\min}\)  
   下限 1.0。上限クリップ **20.0**（契約: `GAP_CLIP_MAX=20`）

5. **`v2_implied_prob`**  
   \(p_i = (1/o'_i) / \sum_j (1/o'_j)\)  
   有効行のみで Σ。無効行は 0。  
   合計は有効行で 1（数値誤差 ±1e-6 許容）

6. **`v2_track_condition_code`**（整数を float で保持）

| 入力文字列（正規化: strip・全半角・「馬場」除去後） | code |
|--------------------------------------------------|------|
| 良 / firm | 1 |
| 稍重 / 稍 / yielding | 2 |
| 重 / soft | 3 |
| 不良 / heavy | 4 |
| その他・不明 | 0 |

7. **flags**  
   `v2_market_missing`, `v2_track_missing` ∈ `{0.0, 1.0}`

---

## 6. FeatureLoader I/F

### 6.1 変更しない既存 I/F（V1 保護）

```text
FeatureLoader.load(core_race_id: str) -> FeatureLoadResult | None

FeatureLoadResult:
  frame: pandas.DataFrame      # 馬×特徴
  feature_source: str          # "db" | "daily_csv" | "global_csv"
  metadata: dict[str, Any]
```

- **FeatureLoader クラス本体の変更は本契約の実装チケットでも禁止**（読取のみ）。  
- V2 は `frame` を受け取る **純関数レイヤ**（仮称 `build_v2_market_features(frame) -> DataFrame`）として Core 側に追加する。

### 6.2 V2 が要求する入力カラム

| カラム | 必須 | 用途 |
|--------|------|------|
| `odds` | 市場可用判定に必要 | Source odds |
| `horse_number` | 推奨（順位付け・結合） | 行識別 |
| `track_condition` / `condition` / `baba` / `track` | 任意 | Source track（いずれか） |

V1 の他 26 列は **あっても無視しない**（V1 行列構築は既存 FeatureGenerator に委譲）。V2 関数は V1 列を書き換えない。

### 6.3 V2 出力 I/F（新規・契約）

```text
V2MarketFeatureResult:
  frame: DataFrame
    # 入力 frame のコピー + §1 の 7 列を付与（V1 列は未変更）
  market_available: bool
  track_available: bool
  feature_set: "v2_market"
```

呼び出し側（Flag ON）:

1. `FeatureLoader.load`（既存）  
2. V1 `FeatureGenerator.build_feature_matrix`（既存・変更禁止）  
3. `build_v2_market_features(raw_frame)`（新規）  
4. V1 Scorer（既存）→ V2-A 補正（新規・§7）  

### 6.4 依存禁止

```text
[OK] v2_market_features ← FeatureLoadResult.frame
[NG] v2_market_features ← collect / etl / friday_gate / manifest
[NG] FeatureLoader のシグネチャ変更
[NG] V1 FeatureGenerator の 28 列変更
```

---

## 7. V2-A の補正上限

V2-A は V1 モデルの **生スコア / logit 相当** \(s_i\) に対する後段バイアスのみ。モデル重み・28 入力は変更しない。

### 7.1 補正式（契約）

市場可用かつ Flag ON のときのみ:

\[
\delta_i = \alpha \cdot \tanh\left(\beta \cdot \left(1 - \frac{1}{g_i}\right)\right)
+ \gamma \cdot \mathbb{1}[\mathrm{track\_code}=c^{\*}]
\]

- \(g_i = \mathrm{v2\_odds\_gap\_to\_favorite}_i\)（§5 クリップ後）  
- 第 1 項: 人気薄（gap 大）への過大バイアスを tanh で飽和  
- 第 2 項: 初期 **γ = 0**（track は観測のみ。PV2-T01 で解禁）

\[
s'_i = s_i + \delta_i
\]

その後、既存の温度付き softmax / ランキング手順（V1）に \(s'\) を渡す。  
**順位のみが変わりうる。** Bundle スキーマは不変。

### 7.2 上限パラメータ（契約固定・初期値）

| パラメータ | 記号 | 初期値 | 硬上限（絶対に超えない） | 意味 |
|------------|------|--------|-------------------------|------|
| 市場バイアス強度 | \(\alpha\) | `0.03` | `\|\alpha\| ≤ 0.05` | 1 頭あたりの最大市場寄与（tanh 飽和前スケール） |
| 形状 | \(\beta\) | `1.0` | `0.5 ≤ β ≤ 2.0` | gap→tanh 感度 |
| 馬場項 | \(\gamma\) | `0.0` | `\|\gamma\| ≤ 0.02` | F01 では常に 0 |
| 頭ごと δ | \(\delta_i\) | — | `\(\|\delta_i\| ≤ 0.05\)` | 適用前に clip |
| レース内 δ レンジ | \(\max\delta-\min\delta\) | — | `≤ 0.08` | 超過時は全体をスケールダウン |
| Top1 強制入替 | — | 禁止 | — | δ のみ。明示スワップ API 禁止 |
| 補正適用 | — | market_available のみ | — | missing 時 δ=0 |

**解釈:** V1 の頭間スコア差が典型的に 0.1〜1 オーダーと仮定し、δ は **最大でも小さな再ランク**に留める。Canary で α を `{0.02, 0.03, 0.05}` のグリッド探索してよいが、硬上限 0.05 を超える提案は **別 Contract 改訂**が必要。

### 7.3 不変条件

1. Flag OFF ⇒ 補正コード非実行、出力ビット一致  
2. Flag ON + market 不可用 ⇒ δ=0（STRICT でなければ）  
3. \(\sum_i \delta_i\) のゼロ和制約は **課さない**（契約簡易化）。必要なら後続 Contract  

---

## 8. AB テスト項目

### 8.1 実験定義

| 項目 | 内容 |
|------|------|
| Control | `PREDICTION_V2_MARKET_FEATURES=false` |
| Treatment | `PREDICTION_V2_MARKET_FEATURES=true`（V2-A, α=初期値） |
| 単位 | race_id |
| 環境 | Development Canary のみ（本番既定 OFF） |
| 同一入力 | 同一 FeatureLoader 結果を両アームへ |

### 8.2 必須メトリクス

| ID | メトリクス | Control 比較 | 合格（ゲート） |
|----|------------|--------------|----------------|
| M1 | **flag_off_identity** | Treatment を立てず同一実行を2回 | ビット一致（必須・別テスト） |
| M2 | **hit_at_1** | Treatment − Control | **非低下**（≥ Control − ε, ε=0） |
| M3 | **miss_top1** | 件数または率 | **非増加** |
| M4 | **ECE**（または信頼度較正代理） | 差分 | 悪化幅 ≤ `0.02`（絶対） |
| M5 | **top3_overlap** | Jaccard / 一致頭数 | 監視（ゲートなし・報告必須） |
| M6 | **rank_churn** | Top1 が入れ替わったレース率 | ≤ `15%`（超過は要説明・FAIL 推奨） |
| M7 | **market_available_rate** | Treatment 対象レース比率 | 報告必須（低すぎる場合はデータ前提不足） |
| M8 | **δ_saturation_rate** | `\|\delta_i\|` が硬上限に張り付いた割合 | ≤ `5%` |

### 8.3 除外ルール

- `v2_market_missing=1` のレースは **主ゲート（M2/M3）の Treatment 効果測定から除外**（別枠で「欠損時フォールバック同一性」を検証）  
- `feature_missing` / mock_fallback 併発レースは IMP 方針どおり除外可  

### 8.4 合格判定（Canary）

| 結果 | 条件 |
|------|------|
| **PASS** | M1 別途 PASS、かつ M2・M3・M4・M6・M8 を満たす |
| **FAIL** | 左記のいずれか違反 |
| **INCONCLUSIVE** | 対象レース数 < 合意最小 N（推奨 N≥30）。再計測 |

PASS 後も **本番 Flag 既定は false**。ON は Human Review + RC 承認後。

### 8.5 報告必須フィールド

- α, β, γ（実効値）  
- market_available_rate  
- Control/Treatment の hit_at_1, miss_top1, ECE  
- rank_churn  
- 除外レース数と理由  

---

## 9. 契約バージョン・改訂

| 項目 | 値 |
|------|-----|
| schema_version | `expect-prediction-v2-market-features/1.0` |
| 互換 | 1.0 の硬上限・列名・式の変更は **マイナー不可** → `1.1` へ昇格審査 |
| 実装チケット化 | **本契約が Approved になった後のみ** |

---

## 承認チェックリスト（レビュー用）

- [x] §1 特徴一覧で不足・過剰がない（条件付き承認）
- [x] §2 Source が Collector 非依存で明確
- [x] §3 Availability / STRICT が運用可能
- [x] §4 欠損時に V1 を汚さない
- [x] §5 正規化が再現可能
- [x] §6 FeatureLoader を変更しない I/F で足りる
- [x] §7 V2-A 上限が保守的
- [x] §8 AB ゲートが Baseline 保護に十分

**承認ステータス:** **ARCHIVED**（2026-07-21 採択）  
**ROI Validation:** [`prediction-v2-f01-roi-validation.md`](./prediction-v2-f01-roi-validation.md) → **18.8% < 20% → Version2 除外**  
**実装チケット:** **作成しない**  
**後任設計レビュー:** [`prediction-v1-miss69-theme-roi-review.md`](./prediction-v1-miss69-theme-roi-review.md)
