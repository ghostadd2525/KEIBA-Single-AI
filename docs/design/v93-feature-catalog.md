# Version9.3 Design — Feature Catalog

**Status:** Design only（実装なし / コード変更禁止）  
**Date:** 2026-07-27  
**Parent:** `docs/design/v93-research-collector.md` / `docs/design/v92-prediction-snapshot.md`  
**Hard Lock:** AI / PE / CE 変更禁止。Research 専用メタデータ。

---

## 1. 目的

Prediction Snapshot に載せる **Feature ごと**に、次を一元管理する。

| 属性 | 意味 |
|------|------|
| **Source** | どのアダプタ / API / 派生計算か |
| **ObservedAt** | 観測時刻の取り方・必須制約 |
| **Consumer** | 誰が読むか（Resolver / Mining / YoungHorse / Report） |
| **Quality** | 品質ルール・スコア定義 |
| **Missing率** | 運用 KPI（層別・理由別） |

Collector は Catalog を読んで収集し、Catalog は Collector の結果で Missing 率を更新する（制御ループ）。

---

## 2. Catalog の位置づけ

```
Feature Catalog (定義・契約・KPI)
        ↑ 定義参照          ↓ KPI 更新
Research Collector ----→ Snapshot Store
        ↓
Evidence Catalog (実インスタンス索引)
        ↓
Weekly Report
```

| | Feature Catalog | Evidence Catalog |
|--|-----------------|------------------|
| 粒度 | Feature 定義（型・ソース・消費者） | Snapshot / race インスタンス |
| 変化頻度 | 低（バージョニング） | 高（毎 Prediction） |
| 例 | `win_odds` の仕様 | 2026-07-26 の race X の欠落 |

---

## 3. Feature レコード契約（Draft）

スキーマ案: `expect-research-feature-catalog/1.0`

```json
{
  "feature_id": "win_odds",
  "schema_version": "expect-research-feature-catalog/1.0",
  "display_name": "単勝オッズ",
  "priority": "P0",
  "scope": "runner",
  "value_type": "number",
  "nullable": true,
  "source": {
    "source_id": "odds_api_win",
    "adapter": "OddsWinAdapter",
    "fallback_source_ids": []
  },
  "observed_at": {
    "required": true,
    "strategy": "source_timestamp_or_fetch_time",
    "must_be_lte_prediction_created_at": true
  },
  "consumers": ["tie_resolver", "evidence_mining", "weekly_report"],
  "quality": {
    "min_score_for_resolver": 0.6,
    "rules": ["positive_odds", "consistent_with_popularity_order"]
  },
  "missing": {
    "track_rate": true,
    "exclude_reasons_from_rate": ["not_applicable"],
    "slo_max_rate": 0.10
  },
  "segment_notes": {
    "二歳新馬": "P0 必須。未取得時 Resolver unresolved"
  },
  "status": "active|deprecated|planned"
}
```

### 3.1 共通フィールド説明

| フィールド | 説明 |
|------------|------|
| `feature_id` | 安定 ID（Snapshot JSON キーと一致） |
| `priority` | `P0` / `P1` / `P2`（V9.2 ロードマップ） |
| `scope` | `race` \| `runner` |
| `source` | 主ソースと任意フォールバック |
| `observed_at` | 時刻戦略と Anti-Leak 制約 |
| `consumers` | 下流の許可リスト |
| `quality` | Resolver 採用閾値・検証ルール |
| `missing` | Missing 率の定義と SLO |
| `status` | 運用状態 |

---

## 4. Feature 一覧（V9.2 カタログ対応）

### 4.1 P0

| feature_id | Source | ObservedAt | Consumers | Quality 要点 | Missing SLO |
|------------|--------|------------|-----------|--------------|-------------|
| `popularity` | `odds_api_win` / shutuba ninki | ソース時刻 ≤ pred | tie_resolver, mining, yh, report | 1..18 整数 | ≤ 10% |
| `win_odds` | `odds_api_win` | 同上 | tie_resolver, mining, report | >1.0 | ≤ 10% |
| `place_odds` | `odds_api_place` | 同上 | mining, report | min≤max, >1.0 | ≤ 15% |
| `expected_popularity` | `derived_expected_pop`（win_odds 派生） | = win_odds.observed_at | tie_resolver, mining | win_odds 存在時必須 | win_odds に連動 |
| `jockey` | `shutuba_entries` | shutuba fetch | tie_resolver*, mining, yh | 正規化名・ノイズ除去 | ≤ 5% |
| `jockey_continued` | `horse_history` | history + today | mining, yh | 新馬は N/A | N/A 除外後 ≤ 15% |
| `trainer` | `shutuba_entries`（`_trainer` 露出） | shutuba fetch | tie_resolver, mining, yh | 非空文字列 | ≤ 10% |
| `frame` | `shutuba_entries` | shutuba fetch | tie_resolver(P2), mining | 1..8、0 は Missing | ≤ 10% |
| `venue` | `race_meta` | race card | yh, report, mining | コード/名称辞書 | ≤ 1% |
| `distance` | `race_meta` | race card | yh, mining | >0 | ≤ 1% |
| `field_size` | `race_meta` | race card | yh, mining | ≥2 | ≤ 1% |
| `surface` | `race_meta` | race card | yh, mining | 芝/ダ/障 | ≤ 5% |
| `going` | `race_meta` | race card | yh, mining | 良/稍重/… | ≤ 10% |
| `weather` | `race_meta` | race card | yh, mining | 晴/曇/… | ≤ 15% |

\* `jockey` は初出走の継続判定には使わないが、騎手×厩舎 prior の入力候補。

### 4.2 P1

| feature_id | Source | ObservedAt | Consumers | Quality 要点 | Missing SLO |
|------------|--------|------------|-----------|--------------|-------------|
| `horse_weight` | `horse_weight_board` | 発表時刻 ≤ pred | tie_resolver, mining, yh | 350–600kg 目安 | ≤ 40%（発表前多い） |
| `horse_weight_delta` | 同上 | 同上 | mining, yh | 整数 kg | horse_weight に連動 |
| `sire` | `pedigree_db` | DB as_of ≤ pred | tie_resolver, mining, yh | id または正規化名 | ≤ 20% |
| `damsire` | `pedigree_db` | 同上 | tie_resolver, mining, yh | 同上 | ≤ 25% |

### 4.3 P2

| feature_id | Source | ObservedAt | Consumers | Quality 要点 | Missing SLO |
|------------|--------|------------|-----------|--------------|-------------|
| `workout_rating` | `workout_page` | 調教記事時刻 | mining, yh | スケール文書化 | ≤ 50% |
| `training_time` | `workout_page` | 同上 | mining, yh | lap 配列整合 | ≤ 50% |
| `moisture_rate` | `track_moisture` | 当日計測 | mining, report | 0–100% | 開催非対応は rate 除外可 |

---

## 5. Source レジストリ

Feature Catalog から参照される Source 側マスタ。

```json
{
  "source_id": "odds_api_win",
  "owner": "research-collector",
  "endpoint_ref": "PI_or_netkeiba_odds",
  "auth": "collector_secret",
  "rate_limit_rps": 2,
  "timeout_ms": 8000,
  "retryable_errors": ["timeout", "5xx", "429"],
  "anti_leak": true
}
```

| source_id | 備考 |
|-----------|------|
| `shutuba_entries` | 厩舎露出がブロッカー（V9.1 DATA GAP） |
| `odds_api_win` / `odds_api_place` | 予測時点スナップ必須 |
| `derived_expected_pop` | 純関数・ネットワーク無し |
| `horse_history` | 継続騎乗 |
| `pedigree_db` | 未整備なら planned |
| `horse_weight_board` | 発表ウィンドウ短 |
| `workout_page` | パース脆い → quality 低め想定 |
| `race_meta` | refresh / race_info |
| `track_moisture` | 任意 |

AI Feature Store（`features` テーブル / PE 入力 CSV）とは **別レジストリ**。同名でも ID 空間を共有しない（`research:` 接頭を推奨する場合あり）。

---

## 6. ObservedAt ポリシー（Catalog 共通）

1. Feature ごとに `observed_at.strategy` を定義  
2. すべて `must_be_lte_prediction_created_at=true`（静的メタも可能な範囲で）  
3. 派生 Feature（想定人気）は **上流 Feature の observed_at を継承**  
4. `not_applicable` の Feature は observed_at = null でよい  

Weekly Report は Feature 別の平均 freshness（秒）を掲載する。

---

## 7. Consumer マトリクス

| Consumer | 読む Feature | 欠落時の挙動 |
|----------|--------------|--------------|
| `tie_resolver` | P0 中心（人気/オッズ/厩舎…） | unresolved / fail-open |
| `evidence_mining` | P0–P2 すべて | 行スキップ or 欠損フラグ付き学習不可（分析のみ） |
| `young_horse_analysis` | セグメント + P0/P1 | カバレッジ注記 |
| `weekly_report` | KPI・Missing 率 | 必須 |
| `challenge` / `ui` / `pe` | **なし** | Catalog 上も許可しない |

`consumers` に無いコンシューマが読む場合は設計違反（V10 実装時のガード案）。

---

## 8. Quality ルールライブラリ（案）

| rule_id | 適用 Feature | 内容 |
|---------|--------------|------|
| `positive_odds` | win_odds, place_odds | 値 > 1 |
| `popularity_range` | popularity | 1..field_size |
| `consistent_with_popularity_order` | win_odds↔popularity | 順序相関の弱チェック |
| `frame_range` | frame | 1..8、0 は invalid→Missing |
| `jockey_name_normalized` | jockey | DB文言混入を除去できたか |
| `weight_plausible` | horse_weight | 妥当レンジ |
| `pedigree_id_present` | sire/damsire | id 優先 |

Quality score が `min_score_for_resolver` 未満の値は、Resolver からは **Missing 扱い**（値は Snapshot に残し mining は参照可）。

---

## 9. Missing 率の定義

### 9.1 計算

対象期間（日 / 週）について Feature `f`:

```
eligible_cells = runner-or-race instances where reason ≠ not_applicable
missing_cells  = eligible_cells where value is null OR reason in tracked_missing
missing_rate   = missing_cells / eligible_cells
```

層別:

- 全体 / 2歳新馬 / 3歳未勝利 / 1勝+  
- reason 別内訳  

### 9.2 SLO とアラート

| priority | 週次 Missing 率上限（全体） | 新馬 |
|----------|---------------------------|------|
| P0 | `slo_max_rate`（概ね ≤10–15%） | より厳しく（Catalog 値） |
| P1 | ≤ 40% | 監視 |
| P2 | 上限なし（可視化のみ） | 可視化 |

SLO 超過は Weekly Report の Action List に自動掲載。

---

## 10. Catalog 保管

| 層 | パス案 |
|----|--------|
| 定義（Git 正本） | `contracts/expect-research-feature-catalog/1.0/features/*.json` または単一 `catalog.json` |
| 実行時コピー | Collector 起動時に読込 |
| KPI 時系列 | `evidence/research/catalog/features/{feature_id}/{yyyy-mm-dd}.json` |

定義変更は PR レビュー必須（Consumer / SLO 変更は Research オーナー承認）。

---

## 11. Weekly Report への出し方

Feature Catalog KPI ブロック例:

```json
{
  "week_id": "2026-W31",
  "features": [
    {
      "feature_id": "win_odds",
      "priority": "P0",
      "source_id": "odds_api_win",
      "missing_rate": 0.42,
      "missing_rate_shinba": 0.71,
      "avg_quality": 0.0,
      "avg_freshness_sec": null,
      "consumers": ["tie_resolver", "evidence_mining"],
      "slo_max_rate": 0.10,
      "slo_breach": true
    }
  ]
}
```

V9.1 時点の「人気 Missing 100%」のような状態を、週次で定量追跡するのが当面の価値。

---

## 12. バージョニング

| 変更種別 | やり方 |
|----------|--------|
| 互換追加（新 Feature planned→active） | catalog minor |
| SLO / consumer 変更 | minor + CHANGELOG |
| 型・意味変更 | major（Snapshot schema も追従） |
| deprecated | 90 日後に mining のみ、Resolver から除外 |

Snapshot `schema_version` と Feature Catalog major を対応表で管理する。

---

## 13. 非ゴール

- PE の `features` テーブル統合  
- Catalog からの自動 PE 学習投入  
- UI への Feature 直接露出  
- コード実装（本票）  

---

## 14. 参照

- `docs/design/v93-research-collector.md`  
- `docs/design/v92-prediction-snapshot.md`（フィールド正本）  
- `docs/design/v92-evidence-platform.md`  
- `docs/design/v91-tie-resolver.md`（Consumer: tie_resolver）  
- `docs/research/v91-rank-degeneracy-analysis.md`（DATA GAP 根拠）
