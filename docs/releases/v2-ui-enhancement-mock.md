# Version 2 — UI Enhancement モック設計

**Date:** 2026-07-21  
**Status:** **正式承認**（2026-07-21 — summary 名前空間 / confidence.band / short_reason / prediction.status 反映）  
**対象:** Race Catalog（`races.html`）/ Prediction 画面（`race.html`）  
**制約:** **PI API 契約（`/v1/races` / `/v1/predictions`）を変更しない**

**ビジュアルモック:** Cursor Canvas  
[`v2-ui-enhancement-mock.canvas.tsx`](/Users/Mr.me/.cursor/projects/c-Users-Mr-me-expect-keiba-ai/canvases/v2-ui-enhancement-mock.canvas.tsx)

---

## 0. エグゼクティブサマリー

v1.1 本番では **Race Catalog のみ**で一覧を描画しており、カードの信頼度は **0%**、◎ 本命は **非表示**。一方 UI 骨格（日付切替・会場フィルタ・検索・お気に入り・並び替え）は **既に実装済み**。

Version 2 UI Enhancement は **表示データの enrich** と **カードレイアウト刷新** が中心。PI スキーマは触らず、**BFF 合成レイヤ** で一覧専用 DTO を返す。

| 項目 | 方針 |
|------|------|
| DTO | **`RaceCardSummary`** — PredictionBundle の簡易版ではなく **一覧専用** |
| Prediction 由来 | **`summary` 名前空間** に集約（honmei / confidence / short_reason） |
| 信頼度 | **`summary.confidence.score` + `band`** — UI は判定ロジックを持たない |
| Explainability | **`summary.short_reason`** を Phase 2 用に予約 |
| 予想状態 | **`prediction.status`** — `ready` / `processing` / `failed` / `missing` |
| 実装順 | **BFF → URL 同期 → HTML → 検索 → お気に入り** |

| 改善候補 | 現状 | v2 モック |
|----------|------|-----------|
| 一覧カード ◎ 表示 | なし | **◎ + 番号 + 馬名** 行を追加 |
| 一覧カード信頼度 | 0%（Catalog のみ） | **Prediction サマリ** をマージ |
| 開催日切替 | 単日 Catalog 取得 | **週末タブ + API 再取得** |
| 競馬場フィルタ | クライアント側のみ | 維持 + 件数バッジ |
| レース検索 | シート UI あり | 維持 + ◎/信頼度も検索対象 |
| お気に入り | localStorage 最大3 | **◎/信頼度** を fav カードに反映 |

---

## 1. 現状ギャップ

### 1.1 データフロー（v1.1）

```text
GET /api/races?date=YYYY-MM-DD
  → PI GET /v1/races/{date}     ← 変更禁止
  → toCardBundle(item)
       ai_confidence.score = null
  → raceCardHtml → conf=0%, ◎なし

GET /api/predictions/:id
  → PI GET /v1/predictions/:id  ← 変更禁止
  → PredictionBundle（詳細のみ）
```

v1.1 既知課題（`docs/releases/v1.1.md` §今後の課題）:

> 一覧カードの AI 信頼度 — `races.html` は Race Catalog のみ参照のため、カード上の信頼度が 0% 表示のまま。

### 1.2 UI 骨格（実装済み・モックでは強化）

| 要素 | ファイル | 状態 |
|------|----------|------|
| 日付タブ | `#dateTabs` | Catalog 描画後に chip 生成 |
| 会場 chip | `#venueChips` | 同上 |
| 検索シート | `#raceSearchRoot` | キーワード + 日付 + 会場 |
| 並び替え | `#raceSortPanel` | 信頼度順（data-race-conf） |
| お気に入り ★ | `favorites.js` | 一覧・詳細・ホーム |
| 本命カード | `race.html` `.honmei-card` | Prediction 詳細 |

---

## 2. PI API 非破壊アーキテクチャ

### 2.1 原則

```text
PI /v1/races        → 変更なし（Race Catalog 正本）
PI /v1/predictions  → 変更なし（PredictionBundle 正本）
BFF                 → 合成のみ（新規 meta / 任意 query）
Web                 → 表示のみ
```

### 2.2 一覧 enrich 方式（採用案: BFF Race Card Summary）

**新規 BFF エンドポイント（PI 非変更）:**

```
GET /api/race-cards?date=YYYY-MM-DD
```

| レイヤ | 処理 |
|--------|------|
| 1 | PI `/v1/races?date=` で Catalog 取得 |
| 2 | 各 `race_id` に PI `/v1/predictions/{race_id}` を **BFF 内部**で取得（既存 mapper 再利用） |
| 3 | Web 専用 DTO `RaceCardSummary[]` を合成して返却（**PredictionBundle とは別契約**） |

**RaceCardSummary（BFF 専用・一覧 DTO・PI 契約外）:**

> **非目標:** PredictionBundle のフィールドを削った簡易版にしない。Catalog 正本（`race_info`）と Prediction 由来サマリ（`summary`）を **意図的に分離** した一覧専用形状とする。

```typescript
/** 一覧カード 1 件 — expect-race-card-summary/1.0 */
interface RaceCardSummary {
  schema_version: "expect-race-card-summary/1.0";
  race_id: string;

  /** Race Catalog 由来のみ — Prediction フィールドを混在させない */
  race_info: RaceInfo;

  /** 予想パイプラインの到達状態（bool ではなく状態型） */
  prediction: RaceCardPredictionState;

  /**
   * Prediction 由来の一覧表示用サマリ。
   * prediction.status !== "ready" のとき null または部分省略。
   */
  summary?: RaceCardSummaryBlock | null;
}

interface RaceCardPredictionState {
  status: "ready" | "processing" | "failed" | "missing";
  engine_source?: string;
}

/**
 * Prediction 由来情報の集約名前空間。
 * 詳細画面の PredictionBundle とは独立 — 一覧に必要な最小集合のみ。
 */
interface RaceCardSummaryBlock {
  honmei?: {
    horse_number: number;
    horse_name: string | null;
    mark: "honmei";
  } | null;

  /** BFF が band を確定 — Web は score + band を表示するだけ */
  confidence?: {
    score: number | null;              // 0–1（表示時に % 換算）
    band: "high" | "medium" | "low";
  } | null;

  /**
   * Explainability 接続点（Phase 2）。
   * Phase 1: null または省略。一覧カードに 1 行理由を載せる予約フィールド。
   * 例: "CE 1 位 · 中上位ルート型"
   */
  short_reason?: string | null;
}
```

**`prediction.status` マッピング（BFF 責務）:**

| status | PI / BFF 条件 | `summary` |
|--------|---------------|-----------|
| `ready` | `prediction_available=true` かつ mapper 成功 | honmei + confidence 填充 |
| `processing` | 予想生成中（PI 将来拡張 or BFF タイムアウト前） | null |
| `failed` | PI 5xx / mapper 例外 / 明示的 failure | null |
| `missing` | `prediction_available=false` / 404 | null |

**`summary.confidence.band` 判定（BFF 責務 — Web 禁止）:**

| band | 条件（PredictionBundle `ai_confidence` と同一閾値） |
|------|-----------------------------------------------------|
| `high` | score ≥ 0.60 |
| `medium` | 0.35 ≤ score < 0.60 |
| `low` | score < 0.35 |

UI は `band` をそのままラベル・星表示に利用。**クライアント側で score から band を再計算しない。**

**Explainability 接続（Phase 2）:**

```text
explain.reason.decision_key.label + factors[0].label
        ↓ BFF raceCardSummaryBuilder
summary.short_reason  （一覧 1 行）
        ↓
races.html カード本文（v2_explain + v2_race_list_ui）
```

Phase 1 では `short_reason` フィールド定義のみ（値は null）。詳細 Explain は `race.html` + `v2_explain`。

**レスポンス例（ready）:**

```json
{
  "schema_version": "expect-race-card-summary/1.0",
  "race_id": "2026-07-25-01-06",
  "race_info": {
    "venue": "新潟",
    "race_number": 6,
    "race_name": "豊栄特別",
    "post_time": "10:35"
  },
  "prediction": {
    "status": "ready",
    "engine_source": "pi"
  },
  "summary": {
    "honmei": {
      "horse_number": 4,
      "horse_name": "コルドンブルー",
      "mark": "honmei"
    },
    "confidence": {
      "score": 0.42,
      "band": "medium"
    },
    "short_reason": null
  }
}
```

**レスポンス例（missing）:**

```json
{
  "schema_version": "expect-race-card-summary/1.0",
  "race_id": "2026-07-25-01-12",
  "race_info": { "venue": "新潟", "race_number": 12, "race_name": "未設定" },
  "prediction": { "status": "missing" },
  "summary": null
}
```

**代替案（却下）:** PI `/v1/races` レスポンスに prediction フィールドを追加 → **PI 契約変更のため不可**。

**代替案（次点）:** Web が `/api/predictions?date=` を並列 fetch → 可能だが N+1 相当。BFF 集約の方が v1.1 一覧レイテンシ課題に整合。

### 2.3 Feature Flag

| Flag | レイヤ | 既定 | 効果 |
|------|--------|------|------|
| `v2_race_cards` | BFF | **false** | `/api/race-cards` 有効 |
| `v2_race_list_ui` | Web | **false** | 新カードレイアウト |
| `v2_explain` | Web | **false** | 詳細 Explain（別 Initiative） |

Flag OFF → 現行 `GET /api/races` + 0% 表示（v1.1 完全同等）。

---

## 3. 画面モック — Race Catalog（`races.html`）

### 3.1 レイアウト（375×812 モバイル基準）

```text
┌─────────────────────────────────────┐
│ Expect                    [≡][🔍] │  ← 並び替え + 検索（既存）
├─────────────────────────────────────┤
│ [7/25][7/26][7/27]  開催日タブ       │  ← タップで API date 切替
│ [すべて][新潟][中京][阪神]           │  ← 会場フィルタ + 件数
│ 対象 36レース · 会場 3 · ★最大3件    │
├─────────────────────────────────────┤
│ ★  新潟 6R                          │
│     豊栄特別                         │
│     ◎ 4 コルドンブルー               │  ← 【新規】summary.honmei
│     10:35発走 · ★★★☆☆              │  ← summary.confidence.band
│                          ┌────────┐ │
│                          │  42%   │ │  ← summary.confidence.score
│                          │ 中程度 │ │  ← band ラベル（BFF 確定）
│                          └────────┘ │
│     （Phase 2: short_reason 1行）   │  ← 予約 — Explainability
│                    詳細を見る ›      │
├─────────────────────────────────────┤
│ ... レースカード × N ...             │
└─────────────────────────────────────┘
│ 🏠  📋  ⭐  👤                       │  ← 既存 nav
└─────────────────────────────────────┘
```

### 3.2 レースカード — v2 コンポーネント

| ゾーン | 内容 | データ源 |
|--------|------|----------|
| 左上 | 会場 + R + レース名 | `race_info`（Catalog） |
| **本命行** | `◎ {num} {horse_name}` | `summary.honmei` |
| メタ | 発走時刻 + 星（信頼度 band） | `race_info` + `summary.confidence.band` |
| 右 | 信頼度 % + band ラベル | `summary.confidence`（score + band） |
| **理由行（Phase 2）** | 1 行テキスト | `summary.short_reason` |
| 右上 | ★ お気に入り | localStorage（既存） |

**`prediction.status` 別表示:**

| status | カード表示 |
|--------|------------|
| `ready` | ◎ + 馬名 + 信頼度% + band |
| `processing` | ◎ — （予想準備中）+ 信頼度 — |
| `failed` | Catalog のみ + muted「予想取得失敗」 |
| `missing` | Catalog のみ + muted「予想未公開」 |

グレーアウト + `data-prediction-status="{status}"`。エラーにしない（v1.1 UX 準拠）。

### 3.3 開催日切替（強化）

| 操作 | 動作 |
|------|------|
| タブ `7/25` | `?date=2026-07-25` + `GET /api/race-cards?date=` 再 fetch |
| `すべて` | 同一 fetch 結果内のクライアント filter（現行維持） |
| 週末外 | `ExpectWeekendCalendar` で次開催日を提案 |

**URL 同期:** `races.html?date=2026-07-25` — ブックマーク可能。

### 3.4 競馬場フィルタ（強化）

| chip | 表示 |
|------|------|
| すべて | `すべて (36)` |
| 新潟 | `新潟 (12)` |

件数は **フィルタ前** の Catalog 件数。active chip は gold accent（既存 `.chip.is-active`）。

### 3.5 レース検索（既存シート — 微修正）

| フィールド | 検索対象（v2 追加） |
|------------|---------------------|
| キーワード | レース名 / 会場 / R / **本命馬名** |
| 開催日 | chip（既存） |
| 会場 | chip（既存） |

`data-race-honmei` 属性をカードに追加。

### 3.6 お気に入り（強化）

| 場所 | v2 追加 |
|------|---------|
| 一覧カード ★ | 既存 |
| ホーム fav レール | **◎ + 信頼度%** をカード下部に |
| 詳細 `race.html` | 既存 + fav 同期 |

`ExpectFavorites.cacheBundles()` に RaceCardSummary を feed（`summary.honmei` / `summary.confidence` を fav カードへ投影）。

---

## 4. 画面モック — Prediction 画面（`race.html`）

### 4.1 レイアウト

```text
┌─────────────────────────────────────┐
│ ‹  新潟 6R                    ★    │
│     豊栄特別 · 10:35               │
├─────────────────────────────────────┤
│ [AI予想] [出馬表] [オッズ] ...       │
├─────────────────────────────────────┤
│ 印                                  │
│ ◎4  ○9  ▲13  △7                    │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ 4                               │ │
│ │ コルドンブルー                   │ │
│ │ AI本命 · 信頼度 42%（低い）      │ │
│ │ ★★☆☆☆                           │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ なぜ ◎ なのか          【v2 Explain】│
│ · CE 評価 1 位（勝率 6.6%）          │
│ · 中上位ルート型                     │
├─────────────────────────────────────┤
│ 信頼度の根拠                         │
│ · 1–2 位差 0.005（混戦）             │
│ · 頭数 18                           │
└─────────────────────────────────────┘
```

Explain ブロックは **Version 2 Explainability** Initiative と連携（`v2_explain` Flag）。UI Enhancement では **枠 + プレースホルダ** のみ先行可能。

### 4.2 Prediction 画面の v2 変更範囲

| 変更 | 説明 |
|------|------|
| 本命カード | 信頼度 band ラベル強調（既存 `applyRaceDetail` 拡張） |
| Provenance | `engine_source: pi` バッジ（v11 既存） |
| ◎ 理由セクション | Explainability 連携時に表示 |
| タブ | 出馬表/オッズは「準備中」維持 |

**PredictionBundle 契約:** 変更なし。表示は既存フィールド + 将来 `explain.*`。

---

## 5. コンポーネント設計

### 5.1 CSS クラス（新規）

| クラス | 用途 |
|--------|------|
| `.race-item-honmei` | ◎ 行（番号 + 馬名） |
| `.race-item-honmei-symbol` | ◎ マーク（gold） |
| `.race-item-honmei--pending` | 予想準備中 |
| `.race-conf--unavailable` | 信頼度未取得 |
| `.race-filters-count` | chip 件数 suffix |

### 5.2 `raceCardHtml` 拡張（設計）

```javascript
// 入力: RaceCardSummary のみ（PredictionBundle を直接渡さない）
// 出力: 既存 .race-item 構造 + .race-item-honmei
data-race-conf="{pct}"           // summary.confidence.score
data-race-conf-band="{band}"     // summary.confidence.band — 表示用のみ
data-race-honmei="{horse_name}"  // summary.honmei.horse_name
data-prediction-status="ready|processing|failed|missing"
```

**band → 星表示（表示マップのみ — 閾値判定は BFF 済み）:**

| band | 星（例） | ラベル（例） |
|------|----------|--------------|
| `high` | ★★★★☆ | 高い |
| `medium` | ★★★☆☆ | 中程度 |
| `low` | ★★☆☆☆ | 低い |

### 5.3 ソート / フィルタ

| 操作 | データ属性 |
|------|------------|
| 信頼度降順 | `data-race-conf`（既存） |
| 本命馬名検索 | `data-race-honmei`（新規） |
| お気に入り優先（任意 Phase 2） | `data-fav-active` |

---

## 6. 状態パターン

| `prediction.status` | `summary` | カード表示 |
|---------------------|-----------|------------|
| **ready** | 填充 | ◎ + 馬名 + 信頼度% + band |
| **processing** | null | ◎ — （予想準備中）+ 信頼度 — |
| **failed** | null | Catalog のみ + muted |
| **missing** | null | Catalog のみ + muted |
| **filtered out** | — | `hidden`（既存） |

Phase 2: `ready` かつ `summary.short_reason` 非空 → カードに理由 1 行を追加。

---

## 7. アクセシビリティ

| 要素 | 対応 |
|------|------|
| ◎ 行 | `aria-label="本命 4番 コルドンブルー"` |
| 信頼度 | `aria-label="AI信頼度 42パーセント"` |
| 日付タブ | `role="tablist"` + `aria-selected` |
| 検索 | 既存 `role="dialog"` 維持 |

---

## 8. パフォーマンス設計

| 項目 | 方針 |
|------|------|
| 一覧 fetch | BFF 並列 9 件（v1.1 既存方針） |
| キャッシュ | BFF `Cache-Control: max-age=60` |
| Skeleton | 既存 `.expect-skel` 維持 |
| 段階表示 | Catalog 先出し → Summary merge（任意 Progressive） |

**Progressive 案（Phase 2）:**

1. Catalog でカード骨格即描画  
2. Summary 到着後に ◎ / 信頼度を patch  

---

## 9. テスト計画（実装フェーズ）

| テスト | 内容 |
|--------|------|
| PI 契約 | `/v1/races` / `/v1/predictions` snapshot 不変 |
| BFF | `race-cards` → `summary.honmei` + `summary.confidence.band` 非 null（ready 時） |
| BFF | `prediction.status` 4 状態マッピング |
| BFF | `summary.short_reason` フィールド存在（Phase 1 は null 可） |
| UI | Flag ON で ◎ 行 + band ラベル表示（クライアント band 計算なし） |
| Regression | Flag OFF → v1.1 同一 |
| a11y | aria-label 検証 |

---

## 10. 実装順序（正式）

```text
① BFF
   GET /api/race-cards + RaceCardSummary DTO + v2_race_cards Flag
   summary 名前空間 / prediction.status / confidence.band 判定
        ↓
② URL 同期
   races.html?date= — 日付タブ ↔ query 双方向同期
        ↓
③ HTML
   raceCardHtml v2 + CSS + fetch 切替（/api/race-cards）
        ↓
④ 検索
   data-race-honmei + summary フィールドを検索対象に
        ↓
⑤ お気に入り
   fav カードへ summary.honmei / summary.confidence 反映
```

**Phase 2（本順序外）:** `summary.short_reason` 填充 + 一覧理由行 UI（Explainability 連携）

**race.html polish:** 本命カード band 強調は Explainability / 詳細 Initiative と並行可。

---

## 11. 関連文書

| 文書 | パス |
|------|------|
| v1.1 既知課題 | `docs/releases/v1.1.md` |
| Race クライアント | `public/assets/api/race.js` |
| カード HTML | `public/assets/api/prediction-bind.js` |
| 一覧ページ | `public/races.html` |
| Explainability | `docs/releases/v2-explainability-design-review.md` |

---

## 12. 承認チェックリスト

- [x] RaceCardSummary = 一覧専用 DTO（PredictionBundle 簡易版ではない）
- [x] Prediction 由来 → `summary` 名前空間
- [x] `summary.confidence` = score + band（UI 判定なし）
- [x] `summary.short_reason` 予約（Explainability Phase 2）
- [x] `prediction.status` 状態型（ready / processing / failed / missing）
- [x] 実装順: BFF → URL 同期 → HTML → 検索 → お気に入り
- [x] 本設計レビュー正式承認（2026-07-21）
- [x] Phase 1 BFF: `GET /api/race-cards` + Flag `v2_race_cards`（既定 false）
- [x] Phase 2 URL 同期: `races.html?date=` ↔ 日付タブ（`ExpectRaceListUrl`）
- [x] Phase 3 HTML: `raceCardSummaryHtml` + `v2_race_list_ui` + `/api/race-cards` fetch 切替
- [x] Phase 4 検索: `data-race-honmei` + `ExpectRaceSearch`（本命 / 信頼度 / band）· Flag OFF 恒等
- [x] Phase 5 お気に入り: RaceCardSummary feed · fav レール ◎/% · localStorage · 検索共存 · Flag OFF 恒等

---

**UI Enhancement Phase 1–5 完了。** 最終レポート: `docs/releases/v2-ui-enhancement-final-report.md`