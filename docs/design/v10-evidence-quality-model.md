# Version10 Design — Evidence Quality Model

**Status:** Design only（実装なし / コード変更禁止）  
**Date:** 2026-07-27  
**Parent:** `docs/design/v10-younghorse-intelligence.md`  
**Related:** `docs/design/v93-feature-catalog.md` · `docs/design/v92-prediction-snapshot.md` · `docs/design/v91-tie-resolver.md`  
**Hard Lock:** PE / CE / AI / Prediction Logic 変更禁止

---

## 0. 目的

Young Horse Intelligence が使う Evidence について、次を **共通モノサシ** で定義する。

1. 何をもって「取得できた」とするか  
2. Quality / Coverage / 欠損率の計算  
3. Prediction 前取得可否の判定  
4. AI改善期待の付け方（Score 非改変前提）  
5. 出走歴0における **同等品質（Q-Parity）** の合否  

本モデルは Research / Snapshot / Resolver 専用。本番 Prediction Bundle の契約には混ぜない。

---

## 1. 評価ディメンション

各 Evidence（Feature）は次の6軸で評価する（Young Horse 設計書の表と同一語彙）。

| 軸 | ID | 定義 |
|----|-----|------|
| 取得元 | `source` | アダプタ / API / HTML / 派生関数 |
| Prediction前取得可否 | `pred_time_available` | 予測永続化時刻に原則取れるか |
| Quality | `quality_grade` | 値の信頼性・正規化・Resolver 採用可否 |
| Coverage | `coverage` | 対象母集団で非 Missing の割合 |
| 欠損率 | `missing_rate` | `1 - coverage`（規則付き） |
| AI改善期待 | `ai_lift_expectation` | Strict / Soft回収への期待 |

追加（内部計算用）:

| 軸 | ID | 定義 |
|----|-----|------|
| Freshness | `freshness_sec` | `prediction_created_at - observed_at` |
| Anti-leak | `anti_leak_ok` | `observed_at ≤ prediction_created_at` |
| Resolver-usable | `resolver_usable` | Quality・欠損・セグメント規則を満たすか |

---

## 2. Prediction前取得可否（`pred_time_available`）

### 2.1 列挙値

| 値 | 意味 |
|----|------|
| `YES` | カード/枠出以降、予測時刻に安定取得可能（静的または早期確定） |
| `CONDITIONAL` | ウィンドウ依存（発売後・体重発表後・調教公開後など） |
| `NO` | 予測時点では原則不可、またはソース未接続 |
| `N/A` | セグメント上定義不能（例: 初出走の継続騎乗） |

### 2.2 判定ルール

```
IF feature がセグメントで定義不能 → N/A
ELSE IF source_adapter 未実装 → NO（BLOCKED 相当）
ELSE IF 値が時刻ウィンドウ外でのみ存在 → CONDITIONAL
ELSE IF 予測作成前に確定しているカード系 → YES
```

### 2.3 Young Horse Tier への適用

| Tier | 典型 | pred_time_available |
|------|------|---------------------|
| Tier1 市場 | 人気・単勝・想定人気 | **CONDITIONAL**（発売後 YES） |
| Tier2 能力 | 厩舎・父・母父・生産牧場 | **YES**（コレクタ整備後） |
| Tier3 当日 | 体重・追切・調教 | **CONDITIONAL**（発表/公開後） |

**運用規則:** `CONDITIONAL` かつウィンドウ外 → 値は入れず `missing_reason=not_yet_published`（正規 Missing）。失敗と混同しない。

---

## 3. Quality（`quality_grade`）

### 3.1 グレード定義

| Grade | 意味 | Resolver 採用 |
|-------|------|---------------|
| **A** | 型・範囲・正規化が安定。ソース公式に近い | **採用可** |
| **B** | 利用可だが表記ゆれ・稀な欠損・派生誤差あり | 閾値付き採用 |
| **C** | 仮説・スケール未固定・パース脆い | Shadow / Mining のみ |
| **D** | 信頼不足・誤用リスク（斤量混同など） | **禁止** |
| **X** | 欠測・N/A・Anti-leak 違反 | 不採用 |

### 3.2 共通 Quality ルール（例）

| feature_id | 合格条件（A/B） | 即 X / D |
|------------|----------------|----------|
| `popularity` | 整数 1..field_size | 0, 重複過多は B 下げ |
| `win_odds` | number > 1.0 | ≤1, null |
| `expected_popularity` | win_odds 全頭から安定ソート | 上流 Missing |
| `trainer` | 非空・正規化名 | 空、馬名混入 |
| `sire` / `damsire` | id または正規化名 | 生文字列のみは ≤B |
| `breeder` | 正規化牧場名 or id | 産地のみ曖昧は C |
| `horse_weight` | 350–600kg 目安 | **斤量流用は D** |
| `workout_rating` | 文書化されたスケール | スケール未定義は C 固定 |
| `training_time` | ラップ整合 | 欠落ラップ多は C |

### 3.3 Resolver 採用閾値

| Consumer | 最低 Quality |
|----------|--------------|
| Tie Resolver（本番候補） | **A**、または **B かつ coverage セグメント SLO 達成** |
| Shadow Resolver | B 以上 |
| Evidence Mining / Report | C 以上（フラグ付き） |

`quality_grade=X` は常にスキップ。

---

## 4. Coverage / 欠損率

### 4.1 母集団

Young Horse Intelligence の既定母集団:

```
population = races WHERE (class == 2歳新馬 OR starts_before == 0)
             AND prediction EXISTS
             AND race_result EXISTS   # 事後評価時
```

Coverage は **runner 単位**（レース単位の「1頭でも欠ける」とは別に、runner fill rate を正とする）。

### 4.2 計算

```
eligible = runners in population WHERE missing_reason NOT IN exclude_set
filled   = eligible WHERE value IS NOT NULL AND quality_grade NOT IN {X}
coverage = filled / eligible
missing_rate = 1 - coverage
```

**exclude_set（欠損率分母から除外してよい理由）:**

| reason | 例 |
|--------|-----|
| `not_applicable` | 初出走×継続騎乗 |
| `not_yet_published` | 発売前の人気、体重発表前 |
| `source_unavailable` | 開催が含水非対応など（Feature による） |

**分母に残す理由（悪い Missing）:**

| reason | 例 |
|--------|-----|
| `fetch_failed` | タイムアウト・5xx |
| `parse_failed` | HTML 壊れ |
| `not_exposed` | `_trainer` 未露出 |
| `adapter_missing` | 血統コレクタ未実装 |
| `anti_leak_rejected` | 予測後の値を棄却 |

### 4.3 SLO（Young Horse・設計目標）

| Tier | Feature | ウィンドウ内 Missing SLO |
|------|---------|-------------------------|
| 1 | popularity / win_odds / expected_popularity | **≤ 10%**（発売後予測） |
| 2 | trainer | **≤ 10%** |
| 2 | sire / damsire | **≤ 20% / 25%** |
| 2 | breeder | **≤ 30%**（初期は 50% まで許容し Stage 上げ） |
| 3 | horse_weight | 発表後 **≤ 15%**（発表前は除外） |
| 3 | workout / training | 公開後 **≤ 40%**（初期緩い） |

SLO 未達の Feature は `resolver_usable=false`（Shadow のみ可）。

---

## 5. AI改善期待（`ai_lift_expectation`）

### 5.1 意味

PE / AI のスコアを変えずに、**Intelligence Layer（主に Tie Resolver）経由**で Strict Hit や Soft回収が改善する期待。

| 値 | 意味 |
|----|------|
| `High` | Soft∧¬Strict 回収の主信号になりうる |
| `Med` | 補助信号・交差検証・発売前フォールバック |
| `Low` | 弱い / レース共通 / 実証 0 |
| `None` | ターゲット外・定義不能 |

### 5.2 付け方の規則（Young Horse）

| 規則 | 内容 |
|------|------|
| L1 | タイ内で馬ごとに値が分散しうる → High/Med 候補 |
| L2 | レース共通値のみ → **Low**（Resolver 不可） |
| L3 | 初出走で N/A → **None** |
| L4 | 未収集で未検証でも、V9.1 がボトルネック指定した市場・厩舎は **High 仮説**を維持 |
| L5 | Soft 外救済を約束しない（天井は Soft Hit） |

### 5.3 Tier 別の既定期待

| Tier | 既定 `ai_lift_expectation` |
|------|----------------------------|
| Tier1 人気・単勝・想定人気 | **High** |
| Tier2 厩舎・父・母父 | **High** |
| Tier2 生産牧場 | **Med–High** |
| Tier3 馬体重・追切・調教 | **Med**（追切は仮説 Med–High） |

---

## 6. 同等品質モデル（Q-Parity）

### 6.1 レース単位グレード

出走歴0レースごとに算出:

| Grade | 条件 |
|-------|------|
| **Q-Parity** | Tier1 `resolver_usable` かつ（`trainer` OR (`sire`∧`damsire`) OR `breeder` のいずれか usable）かつ Resolver `resolved` |
| **Q-Strong** | Tier1 usable かつ Resolver `resolved` |
| **Q-Partial** | Tier1 不可、Tier2 のいずれか usable |
| **Q-Weak** | 上記以外（現行フォールバック相当） |

通常レースは「過去走 Evidence + 一意スコア」により暗黙に Q-Parity 相当とみなす。  
初出走は **本 Grade が Q-Parity のとき「同等品質」と宣言**する。

### 6.2 予測時刻クラス

| クラス | 典型時刻 | 期待 Grade |
|--------|----------|------------|
| `pre_market` | 発売前 | 最大 Q-Partial（Parity 不可を明示） |
| `in_market` | 発売〜締切 | Q-Strong / Q-Parity 目標 |
| `paddock` | 体重発表後 | Tier3 追加で Parity 強化可 |

**契約:** `pre_market` で Q-Parity を要求しない。UI/Ops は Grade を出す（実装は別承認）。

---

## 7. Prior（Tier2 補助スコア）の品質

Resolver が使う `trainer_prior` / `sire_prior` / `damsire_prior` / `farm_prior` は Feature 本体とは別オブジェクト。

| 制約 | 内容 |
|------|------|
| 時間 | 当該 `race_id` の発走より **厳密に前**の結果のみ |
| セグメント | 新馬 / 初出走に限定した集計を既定とする |
| 平滑化 | 小サンプルは先验（Bayesian 等）で C 以下なら不採用 |
| PE 分離 | Prior テーブルは Research 専用。学習パイプラインに流し込まない |

Prior の Quality:

| Grade | 条件 |
|-------|------|
| A | n≥30、定義固定、リーク検査パス |
| B | 10≤n<30 |
| C | n<10 または定義試験中 |
| X | リーク疑い / 定義崩壊 |

---

## 8. Evidence レコード契約（Draft）

Snapshot 内の1 Feature:

```json
{
  "feature_id": "win_odds",
  "tier": 1,
  "value": 5.6,
  "observed_at": "2026-07-26T09:12:00+09:00",
  "source_id": "odds_api_win",
  "pred_time_available": "CONDITIONAL",
  "quality_grade": "A",
  "missing_reason": null,
  "anti_leak_ok": true,
  "resolver_usable": true,
  "ai_lift_expectation": "High"
}
```

欠測時:

```json
{
  "feature_id": "popularity",
  "tier": 1,
  "value": null,
  "observed_at": null,
  "source_id": "odds_api_win",
  "pred_time_available": "CONDITIONAL",
  "quality_grade": "X",
  "missing_reason": "not_yet_published",
  "anti_leak_ok": true,
  "resolver_usable": false,
  "ai_lift_expectation": "High"
}
```

レース単位サマリ:

```json
{
  "race_id": "2026-07-26-03-05",
  "segment": "2歳新馬",
  "starts_before_max": 0,
  "prediction_time_class": "in_market",
  "yh_quality_grade": "Q-Strong",
  "tier_fill": { "1": 0.95, "2": 0.88, "3": 0.0 },
  "score_mutated": false
}
```

---

## 9. Young Horse Evidence 評価表（正本サマリ）

詳細の叙述は `v10-younghorse-intelligence.md` §4。ここは Quality Model 観点の一覧。

### Tier1

| feature_id | source | pred_time | quality | coverage† | missing† | ai_lift |
|------------|--------|-----------|---------|-----------|----------|---------|
| popularity | JRA odds / shutuba | CONDITIONAL | A | ≥0.90 | ≤0.10 | High |
| win_odds | JRA `type=1` | CONDITIONAL | A | ≥0.90 | ≤0.10 | High |
| expected_popularity | derived(win_odds) | CONDITIONAL | A | =win_odds | =win_odds | High |

### Tier2

| feature_id | source | pred_time | quality | coverage† | missing† | ai_lift |
|------------|--------|-----------|---------|-----------|----------|---------|
| trainer | shutuba `_trainer` | YES | A–B | ≥0.90 | ≤0.10 | High |
| sire | pedigree / Netkeiba | YES | B→A | ≥0.80 | ≤0.20 | High |
| damsire | pedigree / Netkeiba | YES | B→A | ≥0.75 | ≤0.25 | High |
| breeder | profile / 産地 | YES | B–C | ≥0.70‡ | ≤0.30‡ | Med–High |

### Tier3

| feature_id | source | pred_time | quality | coverage† | missing† | ai_lift |
|------------|--------|-----------|---------|-----------|----------|---------|
| horse_weight | 当日ボード | CONDITIONAL | B | ≥0.85※ | ≤0.15※ | Med |
| workout_rating | 調教ページ | CONDITIONAL | C→B | ≥0.60※ | ≤0.40※ | Med–High |
| training_time | 調教ページ | CONDITIONAL | C→B | ≥0.60※ | ≤0.40※ | Med |

† ウィンドウ内・SLO 目標（現状実測ではない）。  
‡ 初期は緩めて Stage 上げ。  
※ 発表/公開後のみ分母。

**現状ギャップ（2026-07 実測）:** Tier1 coverage ≈ 0（refresh）、trainer 未露出、血統・牧場・Tier3 未接続 → 大半が Quality X / adapter_missing。Intelligence の第一仕事は **カバレッジを SLO まで上げること**。

---

## 10. 監視 KPI（Weekly）

| KPI | 層別 |
|-----|------|
| Feature 別 coverage / missing_rate | 新馬 × prediction_time_class |
| missing_reason 内訳 | bad vs 正規 |
| yh_quality_grade 分布 | Q-Parity 率 |
| Soft Recovery / Strict Hit | Resolver Shadow |
| anti_leak 違反件数 | 必須 0 |

---

## 11. 変更境界

| 領域 | 本設計 |
|------|--------|
| コード | **未変更** |
| PE / CE / AI / Prediction Logic | **未変更** |
| 成果物 | 本ファイル（Parent と対） |

---

## 12. 参照

- `docs/design/v10-younghorse-intelligence.md`  
- `docs/design/v93-feature-catalog.md`  
- `docs/design/v92-prediction-snapshot.md`  
- `docs/audit/v94-source-feasibility-audit.md`  
- `docs/research/v91-rank-degeneracy-analysis.md`
