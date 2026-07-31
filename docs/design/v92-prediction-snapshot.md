# Version9.2 Design — Prediction Snapshot

**Status:** Design only（実装なし / コード変更禁止）  
**Date:** 2026-07-27  
**Parent:** `docs/design/v91-tie-resolver.md` / `docs/research/v91-rank-degeneracy-analysis.md`  
**Sibling:** `docs/design/v92-evidence-platform.md`  
**Hard Lock:** PE / CE / AI推論 / Research Runtime / ResultAutomation のロジック変更禁止（本票は設計のみ）

---

## 1. 目的

Prediction 生成時刻の **市場・馬柱・環境・血統** 情報を、本番 Prediction Bundle とは **完全分離** した Research 専用ストアへ固定保存する。

これにより Version10 以降で:

- Tie Resolver（同点時のみ）
- Evidence Mining
- Young Horse / 新馬分析

が **リークのない予測時点 Evidence** を参照できる。

V9.1 で判明した DATA GAP（人気・オッズ・厩舎・血統・調教・馬体重が空）を、Score を変えずに解消するための **データ基盤設計**である。

---

## 2. 非ゴール

| 禁止 | 理由 |
|------|------|
| `predictions.bundle_json` へのフィールド混入 | Prediction 契約・UI・Challenge 正本を汚染しない |
| PE の特徴量・スコア計算変更 | Hard Lock / Score Immutability |
| 結果確定後の人気・オッズで Snapshot を上書き | 事後リーク |
| 本票でのコード実装 | 設計のみ |

---

## 3. 概念分離

```
┌─────────────────────────────┐
│ Prediction (本番)            │
│  predictions.bundle_json     │
│  win_prob / marks / ranks    │
│  → UI / Challenge / RA       │
└──────────────┬──────────────┘
               │ prediction_id / race_id / created_at で紐付けのみ
               ▼
┌─────────────────────────────┐
│ Prediction Snapshot (Research)│
│  予測時点の外部観測のみ        │
│  → Tie Resolver / Mining     │
│  Score を含まない（推奨）      │
└─────────────────────────────┘
```

| | Prediction | Prediction Snapshot |
|--|------------|---------------------|
| 所有者 | Product / AI 本番 | **Research 専用** |
| 内容 | モデル出力・説明 | 予測時点の観測特徴 |
| 書き換え | 再推論で新行追加可 | **原則イミュータブル** |
| 消費者 | UI, Challenge, RA | Resolver, Mining, 分析 |
| 契約 | `single-prediction-bundle/*` | `expect-prediction-snapshot/*`（新設予定） |

**ルール:** Snapshot は Prediction を置き換えない。欠落しても Prediction 成功をブロックしない（Research 収集失敗は別監視）。

---

## 4. キャプチャタイミング

### 4.1 正規トリガ

| イベント | Snapshot 動作 |
|----------|----------------|
| Prediction Bundle が **初めて永続化**された瞬間 | **Create**（必須） |
| 同一 `race_id` で再推論（新 `prediction_id`） | **新 Snapshot 行**（旧行は保持） |
| 結果確定（RA） | **書込禁止**（読取・結合のみ） |
| 出走取消・馬体重発表の更新 | 原則反映しない（§4.3） |

紐付けキー:

```
(race_id, prediction_id, captured_at)
```

`prediction_id` = `predictions.id`（または将来の Lifecycle 上の Draft id）。

### 4.2 時刻不変条件（Anti-Leak）

Snapshot に入れるすべての時変フィールドは:

```
source_observed_at <= prediction.created_at
```

を満たすこと。満たせない場合は `null` + `missing_reason`（後述）。

### 4.3 例外ポリシー（設計）

| ケース | 方針 |
|--------|------|
| 予測時点で馬体重未発表 | `horse_weight=null`, `missing_reason=not_yet_published` |
| 締切前にオッズだけ更新したい | **しない**（イミュータブル）。必要なら Version10 で `snapshot_revision=prepost` 別レコード案 |
| PI 一時障害 | Snapshot 行は作り、フィールドは null + `capture_status=partial` |

---

## 5. 保存フィールド（必須カタログ）

スキーマ草案: `expect-prediction-snapshot/1.0`

### 5.1 レース文脈（Race Context）

| フィールド | 型 | 説明 |
|------------|-----|------|
| `meeting` / `venue` | string | 開催（競馬場） |
| `distance` | int | 距離 (m) |
| `field_size` | int | 頭数 |
| `frame` ※馬ごと | int | 枠番 |
| `surface` | string | 馬場（芝/ダ/障） |
| `going` / `track_condition` | string | 馬場状態（良/稍重/…） |
| `weather` | string | 天候 |
| `moisture_rate` | number \| null | **含水率**（取得源が無い場合 null） |
| `race_name` / `class_label` | string | レース名（新馬判定用） |
| `race_date` | date | 開催日 |

### 5.2 馬ごと（Runner Evidence）

| フィールド | 型 | 説明 |
|------------|-----|------|
| `popularity` | int \| null | **人気**（確定人気。未定なら null） |
| `win_odds` | number \| null | **単勝オッズ** |
| `place_odds` | object \| null | **複勝オッズ**（下限/上限 or 代表値。形式は §6） |
| `expected_popularity` | int \| null | **想定人気**（§6.2） |
| `horse_weight` | int \| null | **馬体重** (kg) |
| `horse_weight_delta` | int \| null | **馬体重増減** (kg) |
| `workout_rating` | string \| number \| null | **追切評価** |
| `training_time` | object \| null | **調教時計**（§6.3） |
| `jockey` / `jockey_id` | string | **騎手** |
| `jockey_continued` | bool \| null | **継続騎乗**（§6.4） |
| `trainer` / `trainer_id` | string | **厩舎（調教師）** |
| `sire` / `sire_id` | string \| null | **父** |
| `damsire` / `damsire_id` | string \| null | **母父** |
| `frame` | int \| null | **枠** |
| `horse_number` | int | 馬番（結合キー） |
| `horse_id` | string | netkeiba horse id |

### 5.3 メタ

| フィールド | 説明 |
|------------|------|
| `schema_version` | `expect-prediction-snapshot/1.0` |
| `snapshot_id` | 一意 ID |
| `prediction_id` | 紐付く Prediction |
| `race_id` | 公開 race id |
| `captured_at` | ISO8601 |
| `capture_status` | `complete` \| `partial` \| `failed` |
| `field_coverage` | フィールド充足率 0–1 |
| `sources` | フィールド→データ源マップ |
| `missing` | `[{field, horse_number?, reason}]` |

**Score 非格納原則:** `win_prob` / `model_rank` / `mark` は Snapshot に入れない（Prediction 側を JOIN）。誤用防止。

---

## 6. フィールド仕様メモ

### 6.1 複勝オッズ

推奨表現（いずれか一方を契約で固定）:

```json
"place_odds": { "min": 1.1, "max": 1.5, "as_of": "..." }
```

単値がしか取れないソースでは `min=max=value`。

### 6.2 想定人気

公式人気が未確定のときの Research 定義:

1. 予測時点の単勝オッズを昇順ソートし、同オッズは馬番で安定ソート  
2. 付与した順位を `expected_popularity` とする  

公式 `popularity` が入った場合も **上書きせず併記**（どちらで Tie Break したか追跡可能）。

### 6.3 調教時計

```json
"training_time": {
  "date": "YYYY-MM-DD",
  "course": "美浦W / 栗東坂路 / ...",
  "time_text": "54.0-39.0-12.5",
  "lap_seconds": [54.0, 39.0, 12.5],
  "evaluator": "optional"
}
```

取得不能時は null + `missing_reason=source_unavailable`。

### 6.4 継続騎乗

```
jockey_continued =
  starts_before >= 1
  AND normalize(jockey_today) == normalize(prev_race_jockey)
```

初出走（`starts_before==0` / 新馬）: **必ず `null`**（false にしない。V9.1 で定義不能と判明）。

### 6.5 含水率

JRA / 地方の公開含水率が取れる開催のみ格納。取れない開催は null を正規とする（欠損をエラーにしない）。

---

## 7. 保存先（Research 専用）

Prediction DB テーブル `predictions` とは **別ストア**。

### 7.1 論理ストア

| 層 | パス / テーブル案 | 用途 |
|----|-------------------|------|
| Primary JSON | `evidence/research/prediction-snapshots/{race_date}/{race_id}/{prediction_id}.json` | 監査・同期・Git 任意 |
| Index DB（Research） | `research_prediction_snapshots`（AI DB 内でも **research_ 接頭** で隔離） | 高速 JOIN |
| Manifest | `evidence/research/prediction-snapshots/manifest/{date}.json` | 日次カバレッジ |

本番 Product API はデフォルトで Snapshot を返さない。Research / OPS 専用エンドポイント案は Platform 設計書へ。

### 7.2 行スキーマ（DB 草案）

```text
research_prediction_snapshots
  snapshot_id        TEXT PK
  schema_version     TEXT NOT NULL
  race_id            TEXT NOT NULL
  prediction_id      INTEGER NOT NULL   -- FK logical → predictions.id
  race_date          TEXT
  captured_at        TEXT NOT NULL
  capture_status     TEXT NOT NULL
  field_coverage     REAL
  payload_json       TEXT NOT NULL      -- 全文（§5）
  UNIQUE(prediction_id)
```

`payload_json` に馬配列を含め、正規化テーブル（`research_snapshot_runners`）は Version10 で任意。

### 7.3 保持ポリシー

| 項目 | 案 |
|------|-----|
| 保持期間 | 最低 24 ヶ月（Young Horse 季節比較用） |
| 削除 | Prediction Archived 後も Snapshot は残す（Research 優先） |
| PII | 騎手・調教師名は公開情報扱い |

---

## 8. 収集源マッピング（設計）

| フィールド | 想定ソース（現行資産） | V9.1 現状 |
|------------|------------------------|-----------|
| 人気・単勝 | shutuba / odds API | runners で空が多い |
| 複勝 | odds API type=place | 未接続 |
| 想定人気 | 単勝から算出 | 未実装 |
| 馬体重・増減 | 当日成績/パドック系 | 未収集 |
| 追切・調教 | 調教ページ | 未収集 |
| 騎手 | shutuba / runners | あり（品質差） |
| 継続騎乗 | history_jockey vs today | 算出可 |
| 厩舎 | parse `_trainer` | **CSV 未露出** |
| 父・母父 | horse DB pedigree | 未収集 |
| 枠 | shutuba frame | 日により 0 埋め |
| 馬場・天候 | race meta / refresh | 部分あり |
| 含水率 | 開催当日情報 | 多くの場合 null 想定 |
| 開催・距離・頭数 | race_info / runners | あり |

収集アダプタは **PE の外**（Collector / PI refresh サイドカー）に置く。PE 呼び出しグラフに埋め込まない。

---

## 9. 品質ゲート（Research SLO）

Prediction 成功とは独立。日次 Research 監視:

| 指標 | 初期目標（導入後） |
|------|-------------------|
| Snapshot 作成率（Prediction 行に対する） | ≥ 95% |
| `capture_status=complete` 率 | ≥ 70%（調教・含水率は除外可） |
| P0 フィールド充足（人気 or 単勝, 厩舎, 騎手, 枠） | ≥ 90%（新馬含む） |
| P1（父・母父・馬体重） | ≥ 60% |
| Anti-leak 違反 | **0** |

欠落は `missing[]` に理由コードで残す:

`not_yet_published` | `source_unavailable` | `parse_failed` | `timeout` | `not_applicable`

---

## 10. 消費者インターフェース（読取専用案）

```text
GET /v1/research/prediction-snapshots/{race_id}?prediction_id=
GET /v1/research/prediction-snapshots?date=YYYY-MM-DD
```

- 認証: OPS / Research ロール  
- 本番 Challenge API からは呼ばない（V9.0 Benchmark と分離）

JOIN 例（分析）:

```text
predictions p
  JOIN research_prediction_snapshots s ON s.prediction_id = p.id
  JOIN race_results r ON r.race_id = p.race_id
```

Tie Resolver は `s.payload_json.runners[]` のみを Evidence とし、`p.bundle_json` の score は参照するが変更しない。

---

## 11. ライフサイクルとの関係

`docs/design/v9-prediction-lifecycle.md` との整合:

| Lifecycle | Snapshot |
|-----------|----------|
| Draft 生成 | Snapshot Create |
| Supersede（新 Draft） | 新 Snapshot（旧保持） |
| Published | Snapshot は既に固定済みを参照 |
| ChallengeEligible | Snapshot は settle に使わない（Benchmark は別）。Resolver 研究のみ |

Challenge 正本（単勝 Benchmark）は Snapshot に依存しない。

---

## 12. 実装フェーズ（将来チケット分割・本票では実装しない）

| Phase | 内容 |
|-------|------|
| V9.2a | 契約 JSON Schema + 空ストア + 書き込みスタブ設計レビュー |
| V9.2b | P0 収集（人気/単勝/複勝/想定人気/騎手/継続/厩舎/枠/開催コンテキスト） |
| V9.2c | P1（馬体重/増減/父/母父） |
| V9.2d | P2（追切/調教/含水率） |
| V10 | Tie Resolver Shadow が Snapshot を正式入力に |

---

## 13. 参照

- `docs/design/v92-evidence-platform.md`  
- `docs/design/v91-tie-resolver.md`  
- `docs/research/v91-rank-degeneracy-analysis.md`  
- `docs/design/v9-prediction-lifecycle.md`  
- `predictions` テーブル: `services/win5-ai/app/data/migrations/001_init.sql`  
- shutuba `_trainer`: `pi_keibanet/netkeiba/parse.py`
