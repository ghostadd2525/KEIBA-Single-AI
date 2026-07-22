# Version 2 — Explainability 設計レビュー

**Date:** 2026-07-21  
**Status:** **Phase 1–3 実装完了 — Final Report 提出**  
**Goal:** Prediction 画面で **「なぜ ◎ なのか」** を説明可能にする  
**Baseline:** Version 1.1（`single-prediction-bundle/2.0` 後方互換を維持）

---

## 0. エグゼクティブサマリー

本番 Prediction 経路（PI API → BFF → Web）では、**Candidate Evaluation（CE）まで**のデータは取得可能だが、`explain.reasons` / `narrative` は **空のまま** UI が「理由データなし」を表示している。

Version 2 Explainability は **PredictionBundle の additive 拡張（explain 2.1）** により、◎（本命）選定理由を構造化して返す。既存 2.0 クライアントは破壊せず、新フィールドを無視できる。

| 項目 | 方針 |
|------|------|
| 契約 | `explain.schema_version: "single-explain/2.1"` + reason / confidence_reason / decision_trace |
| 決定打 | **`reason.decision_key`** — ◎ 選定の唯一の決定因子（summary とは別） |
| 信頼度寄与 | **`confidence_reason.components[].contribution` / `weight`** |
| トレース | **`decision_trace.stages[]`** — stage / status / delta / timestamp? |
| 実装順 | **Core explain_payload → PI pass-through → BFF mapper → Web Flag** |
| データ源（現行） | AI Core CE 出力（World / Confidence meta） |
| データ源（将来） | Product Pool / Entry / RePick journal |
| UI | Feature Flag `v2_explain`（Web） |
| Baseline | Flag OFF 時は v1.1 と同一表示 |

---

## 1. 現状分析

### 1.1 データフロー（v1.1 本番）

```text
PI API (CorePipeline.evaluate)
  → candidates[Rank, Confidence, WorldMeta, SubWorldMeta]
  → world / sub_world / overall_confidence / meta{gap12, entropy, race_required_pick, ...}
       ↓
BFF piPredictionMapper
  → evaluation.runners (mark=honmei ← Rank1)
  → explain.reasons=[] / narrative=""   ← 欠落
       ↓
Web race.html (#reasonsSectionBody)
  → 「理由データなし」
```

### 1.2 既存 PredictionBundle 契約

| ブロック | 現状 | Explain 用途 |
|----------|------|--------------|
| `evaluation.world` / `sub_world` | PI からマップ済 | レース世界・ルート分類 |
| `evaluation.runners[]` | Rank / mark / win_prob | ◎ 対象馬の特定 |
| `ai_confidence` | score / band / factors[] | 信頼度（factors 空） |
| `explain.reasons[]` | **空** | 馬別 bullets（レガシー） |
| `explain.narrative` | **空** | 短文サマリー |

契約: `contracts/single-prediction-bundle/2.0/schema.json` — `additionalProperties: true` のため **explain サブスキーマ拡張が可能**。

### 1.3 PI Core が既に持つ Explain 素材（未投影）

`GET /v1/predictions/{race_id}` の `prediction.meta` 例（285R 相当コーパス外の本番サンプル）:

| キー | 例 | 説明用途 |
|------|-----|----------|
| `gap12` | 0.004883 | 1–2 位差 → ◎ の明確さ |
| `top2_sum` | 0.126579 | 上位集中度 |
| `entropy` | 2.887667 | レース混戦度 |
| `race_required_pick` | 2 | Required Role（必要拾い数） |
| `spread_need_label` | strong_spread | 展開需要 |
| `observer_repick_ready_flag` | 1 | RePick 準備度 |
| `race_type_label` | ability | レース型 |
| `rank7_9_pick_required_flag` | 0 | 役割別フラグ |

候補馬 `WorldMeta` / `SubWorldMeta`: `midupper_world` / `midupper_route`

### 1.4 現行 PI 経路の限界

| 段 | 本番 PI | Explain 可否 |
|----|---------|--------------|
| Candidate Evaluation | ✅ | **即時可能** |
| World / SubWorld / Route | ✅（CE meta） | **即時可能** |
| Required Role | ✅（race meta） | **即時可能** |
| Pool / Entry | ❌ 未配線 | `decision_trace` に `not_applied` |
| RePick | ❌ 未配線 | `not_applied` + meta フラグのみ |
| Delete | ❌ 変更禁止 | 記載のみ（触らない） |

**設計上の正直な表現:** Phase 1 は **「なぜ CE 上で ◎ なのか」** を説明。Product 段の理由は Phase 2 で journal 連携後に追記。

---

## 2. ユーザーストーリー

> レース詳細（AI予想タブ）で本命 ◎ の馬名の下に、  
> **2〜3 行の理由** と **信頼度の根拠** が表示される。  
> 「詳しく見る」で **判断トレース（CE → Pool → …）** を段階表示。

**非目標（Phase 1）:**

- 勝ち馬の事後説明（結果連動）
- LLM 生成ナラティブ
- Analysis API 依存

---

## 3. PredictionBundle 拡張設計

### 3.1 方針

- **Bundle 本体は `single-prediction-bundle/2.0` を維持**
- **`explain` ブロック内に `schema_version: "single-explain/2.1"`** を追加
- 新規 3 フィールド: **`reason`** / **`confidence_reason`** / **`decision_trace`**
- 既存 `reasons[]` / `narrative` は **後方互換のため維持**（mapper が自動生成）

### 3.2 型定義（設計）

```typescript
/** explain ブロック — v2.1 拡張 */
interface ExplainV21 {
  schema_version?: "single-explain/2.1";
  meta?: ExplainMeta;

  /** レガシー（2.0 互換）— mapper が reason から自動填充 */
  reasons?: ExplainReason[];
  narrative?: string;

  /** 【新規】◎ 本命の構造化理由（Primary Answer） */
  reason?: HonmeiReason;

  /** 【新規】信頼度算出根拠（ai_confidence とリンク） */
  confidence_reason?: ConfidenceReason;

  /** 【新規】パイプライン判断トレース */
  decision_trace?: DecisionTrace;
}
```

### 3.3 `HonmeiReason` — 「なぜ ◎ か」

```typescript
interface HonmeiReason {
  schema_version: "single-honmei-reason/1.0";
  candidate_id: string;
  horse_number: number;
  horse_name?: string | null;
  mark: "honmei";

  /**
   * 【必須・1 件】AI が最終的に決定打とした因子。
   * summary（叙述）とは別。UI は「決定打」ラベルで 1 行表示。
   * 別名 primary_factor（内部）— 契約フィールド名は decision_key に統一。
   */
  decision_key: DecisionKey;

  /** ユーザー向け 1 文（必須）— decision_key を含む叙述 */
  summary: string;

  /** 構造化根拠（表示順固定）。decision_key と一致する factor を primary に */
  factors: HonmeiReasonFactor[];

  /** 内部コード（UI 非表示・ログ用） */
  reason_codes?: string[];
}

/** 決定打 — ちょうど 1 件 */
interface DecisionKey {
  key: string;                   // ce_rank1 | gap12_lead | route_midupper | ...
  kind: HonmeiReasonFactor["kind"];
  label: string;                 // UI: 「CE 評価 1 位」
  text?: string;                 // 補足 1 行（任意）
  evidence?: Record<string, unknown>;
}
```

**decision_key 選定ルール（Phase 1）:**

| 優先 | 条件 | key 例 |
|------|------|--------|
| 1 | `model_rank === 1` かつ `gap12` が field 内最大 | `ce_rank1_gap_lead` |
| 2 | `model_rank === 1` のみ | `ce_rank1` |
| 3 | world/route が race 型判定の主因 | `route_midupper` 等 |

**必ず 1 件。** 複数候補時は上表優先度で Core が決定。BFF は **上書きしない**（pass-through または Core 出力を投影）。

```typescript
interface HonmeiReasonFactor {
  kind:
    | "candidate_evaluation"
    | "world"
    | "sub_world"
    | "route"
    | "required_role"
    | "repick"
    | "comparison";
  label: string;
  text: string;
  weight?: "primary" | "secondary";
  evidence?: Record<string, unknown>;
}
```

**summary 生成ルール（設計）:**

```
template: "{horse}を◎としたのは、{ce_reason}。{world_route}。{confidence_hint}。"
```

例:

> 4番コルドンブルーを◎としたのは、CE 評価 1 位（勝率 6.6%）で 2 位との差が最も大きいため。中上位世界・中上位ルート型のレースで、能力差が読みやすい構成です。

### 3.4 `ConfidenceReason` — 信頼度算出根拠

```typescript
interface ConfidenceReason {
  schema_version: "single-confidence-reason/1.0";
  score: number | null;          // ai_confidence.score と一致
  band: "high" | "medium" | "low" | "unknown";
  score_unit: "normalized";

  /** ユーザー向け 1 文 */
  summary: string;

  /** 構成要素（ConfidenceBuilder 由来） */
  components: ConfidenceComponent[];

  /** 計算式参照（監査用・折りたたみ） */
  formula_ref?: string;          // e.g. "top1*(0.55+0.25*gap_factor+0.20*spread_factor)"
}

interface ConfidenceComponent {
  key: string;                   // gap12 | entropy | field_size | top2_sum | ...
  label: string;                 // 「1–2 位差」
  value: number | string;
  unit?: string;
  interpretation: string;        // 「差が小さく混戦」

  /**
   * 将来の寄与率分析用（Phase 1 からフィールド定義、値は Core 算出）
   * contribution: 当該成分が overall score に占める正規化寄与（0–1、合計≈1）
   * weight: 公式内の係数（例: gap_factor 項の 0.25）
   */
  contribution?: number;
  weight?: number;
}
```

**CE `ConfidenceBuilder` との対応:**

| component.key | ソース | weight（公式） | contribution（例） |
|---------------|--------|----------------|-------------------|
| `gap12` | meta.gap12 | 0.25（gap_factor 項） | gap_factor × top1 寄与 |
| `top2_sum` | meta.top2_sum | — | 参考指標 |
| `entropy` | meta.entropy | 0.20（spread_factor 項） | spread_factor × top1 寄与 |
| `field_size` | meta.field_size | — | 間接（entropy 経由） |
| `top1_prob` | meta.top1_prob | 0.55（ベース項） | ベース寄与 |

Phase 1 では `contribution` / `weight` を **必須出力**（分析基盤）。UI 初期表示は optional（折りたたみ）。

### 3.5 `DecisionTrace` — 判断トレース

Product Journal / RePick 解析と **同一ステージ構造** で将来拡張可能とする。

```typescript
interface DecisionTrace {
  schema_version: "single-decision-trace/1.0";
  pipeline_version: string;
  stages: DecisionTraceStage[];
}

/** journal 1 イベント ≒ stages 1 行 */
interface DecisionTraceStage {
  stage:
    | "candidate_evaluation"
    | "world_classification"
    | "candidate_pool"
    | "entry"
    | "repick"
    | "purchase"
    | "delete"
    | "mark_assignment";
  status: "applied" | "skipped" | "not_applied" | "locked";
  delta: DecisionTraceDelta;
  timestamp?: string;            // ISO 8601 UTC（Phase 2 Product journal）
}

interface DecisionTraceDelta {
  summary: string;
  reason_codes?: string[];
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
}
```

**Phase 2 RePick journal 映射例:**

```json
{
  "stage": "repick",
  "status": "applied",
  "timestamp": "2026-07-21T04:00:01.123Z",
  "delta": {
    "summary": "NEAR rescue: rank9 → repick membership",
    "reason_codes": ["rv2_near", "g1_strict"],
    "before": { "in_repick": 0, "surv_pos": 10 },
    "after": { "in_repick": 1, "surv_pos": 8 },
    "inputs": { "N": 8, "victim_rank": 11 },
    "outputs": { "displaced": true }
  }
}
```

**Phase 1 既定ステージ（PI = CE のみ）:**

| stage | status | delta.summary 例 |
|-------|--------|------------------|
| candidate_evaluation | applied | CE 1 位 → 4 番コルドンブルー（勝率 6.6%） |
| world_classification | applied | midupper_world / midupper_route |
| candidate_pool | not_applied | Product Pool 未配線（v1.1 PI 経路） |
| entry | not_applied | 同上 |
| repick | not_applied | RePick 未実行（observer_repick_ready=1） |
| purchase | not_applied | 同上 |
| delete | locked | Delete Boundary — 変更禁止 |
| mark_assignment | applied | Rank1 → mark=honmei（◎） |

**Phase 2:** Product journal を `stages[]` に **そのまま append**（フィールド変換なし）。

---

## 4. 候補ソース × 責務マッピング

| ユーザー候補 | データ源 | 投影先 | Phase |
|--------------|----------|--------|-------|
| Candidate Evaluation 理由 | CE ranking / win_prob | `reason.factors` + **`reason.decision_key`** | **1** |
| World | `evaluation.world` | `reason.factors[kind=world]` | **1** |
| SubWorld | `evaluation.sub_world` | `reason.factors[kind=sub_world]` | **1** |
| Route | `SubWorldMeta` / sub_world | `reason.factors[kind=route]` | **1** |
| Required Role | meta.race_required_pick, rank*_flag | `reason.factors[kind=required_role]` | **1** |
| RePick 理由 | Product journal（将来） | `reason.factors[kind=repick]` + trace | **2** |
| Confidence 算出根拠 | ConfidenceBuilder + meta | `confidence_reason` + **contribution/weight** | **1** |

### 4.1 コード → 日本語ラベル（辞書）

| code | label（UI） | decision_key 例 |
|------|-------------|-----------------|
| `ce_rank1` | CE 評価 1 位 | ◎ 決定打 |
| `ce_rank1_gap_lead` | CE 1 位・2 位差最大 | ◎ 決定打（優先） |
| `midupper_world` | 中上位世界 | factor |
| `midupper_route` | 中上位ルート型 | factor / 決定打（稀） |
| `ability` | 能力差レース | factor |
| `strong_spread` | 展開分散が必要 | factor |
| `race_required_pick:2` | 2 頭拾い必要 | factor |

辞書ファイル: `contracts/single-explain/1.0/labels.ja.json`（設計上の正本）

---

## 5. レイヤ別実装責務

### 5.0 実装順序（Phase 1 正式）

```text
① Core explain_payload     WIN5_EXPLAIN_V2_ENABLED
        ↓
② PI pass-through          prediction.explain_payload（契約 additive）
        ↓
③ BFF mapper               explainBuilder.js → explain 2.1
        ↓
④ Web Flag                 v2_explain UI
```

**禁止:** 逆順実装（UI 先行で mock reason を載せない）。各層は Flag OFF で v1.1 恒等。

```text
┌─────────────────────────────────────────────────────────────┐
│ AI Core (CE)                                                 │
│  evaluate() → CorePublicBundle + explain_payload (新規)      │
│  - ranking evidence, world, confidence meta                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ PI API                                                       │
│  prediction.explain_payload を pass-through（変更最小）       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ BFF piPredictionMapper + explainBuilder (新規)                 │
│  PI → PredictionBundle.explain (v2.1)                        │
│  - reason / confidence_reason / decision_trace 組み立て       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Web (race.html + prediction-bind.js)                         │
│  v2_explain Flag ON → ◎ 理由 UI 表示                         │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 AI Core — `explain_payload` 出力（新規）

`CorePipeline.evaluate()` 返却に optional ブロック追加:

```json
{
  "explain_payload": {
    "schema_version": "core-explain-payload/1.0",
    "honmei_candidate_id": "コルドンブルー",
    "decision_key": {
      "key": "ce_rank1_gap_lead",
      "kind": "candidate_evaluation",
      "label": "CE 評価 1 位",
      "evidence": { "model_rank": 1, "win_prob": 0.0657, "gap12": 0.004883 }
    },
    "ranking_evidence": { "rank": 1, "win_prob": 0.0657, "gap_to_next": 0.0049 },
    "world": { "world": "midupper_world", "sub_world": "midupper_route" },
    "confidence_meta": { "gap12": 0.004883, "entropy": 2.887667 },
    "confidence_components": [
      { "key": "gap12", "value": 0.004883, "weight": 0.25, "contribution": 0.12 },
      { "key": "entropy", "value": 2.887667, "weight": 0.20, "contribution": 0.08 }
    ],
    "decision_trace_stages": [
      {
        "stage": "candidate_evaluation",
        "status": "applied",
        "delta": {
          "summary": "CE 1 位: 4 番コルドンブルー",
          "outputs": { "model_rank": 1, "win_prob": 0.0657 }
        }
      }
    ],
    "required_role": { "race_required_pick": 2 },
    "product_stages": null
  }
}
```

**Feature Flag:** `WIN5_EXPLAIN_V2_ENABLED`（Core、既定 **false**）。OFF 時は `explain_payload` 省略 → BFF は v1.1 同等。

### 5.2 BFF — `explainBuilder.js`（新規）

| 関数 | 責務 |
|------|------|
| `buildHonmeiReason(piPred, honmeiRunner)` | decision_key + summary + factors |
| `buildConfidenceReason(meta, aiConfidence)` | components + contribution/weight |
| `buildDecisionTrace(piPred, flags)` | stages（stage/status/delta/timestamp?） |
| `legacyCompat(explain)` | reasons[] + narrative 自動生成 |

### 5.3 Web UI

| 要素 | データ |
|------|--------|
| 本命カード下 | **`explain.reason.decision_key.label`**（決定打 1 行）+ `summary` |
| #reasonsSection | `explain.reason.factors[]` をリスト |
| 信頼度詳細 | `confidence_reason.components`（contribution/weight は折りたたみ） |
| 折りたたみ | `decision_trace.stages[].delta.summary` タイムライン |

**Feature Flag:** `v2_explain: true`（`public/config/beta.json`）。OFF 時は現行 `reasonsSectionHtml`（空なら muted）。

---

## 6. 契約変更計画

### 6.1 新規ファイル（設計）

| パス | 内容 |
|------|------|
| `contracts/single-explain/1.0/schema.json` | HonmeiReason / ConfidenceReason / DecisionTrace |
| `contracts/single-explain/1.0/labels.ja.json` | コード辞書 |
| `contracts/single-prediction-bundle/2.0/schema.json` | `$defs/Explain` に optional refs 追加（**required 不変**） |

### 6.2 後方互換

| クライアント | 動作 |
|--------------|------|
| v1.1 Web（Flag OFF） | 従来どおり |
| v1.1 契約テスト | `required` フィールドのみ検証 → **PASS 維持** |
| v2 Web（Flag ON） | 新フィールド表示 |

### 6.3 PI API 変更範囲

v1.1 で Prediction API は本番固定だが、Explainability は **additive response フィールド** のみ:

```json
{
  "prediction": {
    "...existing...",
    "explain_payload": { "...optional..." }
  }
}
```

既存クライアントは `explain_payload` を無視可能。

---

## 7. サンプル Payload（設計）

```json
{
  "schema_version": "single-prediction-bundle/2.0",
  "race_id": "2026-07-25-01-06",
  "evaluation": {
    "world": "midupper_world",
    "sub_world": "midupper_route",
    "runners": [
      {
        "horse_number": 4,
        "horse_name": "コルドンブルー",
        "model_rank": 1,
        "win_prob": 0.0657,
        "mark": "honmei"
      }
    ]
  },
  "ai_confidence": {
    "score": 0.042,
    "band": "low",
    "factors": ["gap12=0.004883", "entropy=2.887667"]
  },
  "explain": {
    "schema_version": "single-explain/2.1",
    "narrative": "4番コルドンブルーを◎。CE 1 位、中上位ルート型。",
    "reasons": [
      {
        "horse_number": 4,
        "bullets": ["CE 評価 1 位", "中上位ルート型"]
      }
    ],
    "reason": {
      "schema_version": "single-honmei-reason/1.0",
      "candidate_id": "c04",
      "horse_number": 4,
      "horse_name": "コルドンブルー",
      "mark": "honmei",
      "decision_key": {
        "key": "ce_rank1_gap_lead",
        "kind": "candidate_evaluation",
        "label": "CE 評価 1 位",
        "text": "2 位との勝率差が最も大きい",
        "evidence": { "model_rank": 1, "win_prob": 0.0657, "gap12": 0.004883 }
      },
      "summary": "4番コルドンブルーを◎としたのは、CE 評価 1 位（勝率 6.6%）で 2 位との差が最も大きいため。中上位世界・中上位ルート型のレースです。",
      "factors": [
        {
          "kind": "candidate_evaluation",
          "label": "CE 評価",
          "text": "モデル順位 1 位・勝率 6.6%",
          "weight": "primary",
          "evidence": { "model_rank": 1, "win_prob": 0.0657, "gap12": 0.004883 }
        },
        {
          "kind": "world",
          "label": "レース世界",
          "text": "中上位世界",
          "evidence": { "code": "midupper_world" }
        },
        {
          "kind": "route",
          "label": "展開ルート",
          "text": "中上位ルート型",
          "evidence": { "code": "midupper_route" }
        },
        {
          "kind": "required_role",
          "label": "必要役割",
          "text": "2 頭拾い必要（展開分散 strong_spread）",
          "weight": "secondary",
          "evidence": { "race_required_pick": 2, "spread_need_label": "strong_spread" }
        }
      ],
      "reason_codes": ["ce_rank1", "world_midupper", "route_midupper"]
    },
    "confidence_reason": {
      "schema_version": "single-confidence-reason/1.0",
      "score": 0.042,
      "band": "low",
      "score_unit": "normalized",
      "summary": "信頼度は低め。1–2 位差が小さく混戦度が高いため、◎ の優位は限定的です。",
      "components": [
        {
          "key": "gap12",
          "label": "1–2 位差",
          "value": 0.004883,
          "interpretation": "差が小さく上位が拮抗",
          "weight": 0.25,
          "contribution": 0.12
        },
        {
          "key": "entropy",
          "label": "混戦度",
          "value": 2.887667,
          "interpretation": "勝率分布が分散",
          "weight": 0.20,
          "contribution": 0.08
        },
        {
          "key": "field_size",
          "label": "頭数",
          "value": 18,
          "interpretation": "多頭数で不確実性増",
          "contribution": 0.05
        }
      ],
      "formula_ref": "top1*(0.55+0.25*gap_factor+0.20*spread_factor)"
    },
    "decision_trace": {
      "schema_version": "single-decision-trace/1.0",
      "pipeline_version": "ai-core-migrated/1.0-phase1",
      "stages": [
        {
          "stage": "candidate_evaluation",
          "status": "applied",
          "delta": {
            "summary": "CE 1 位: 4 番コルドンブルー（勝率 6.6%）",
            "outputs": { "model_rank": 1, "horse_number": 4, "win_prob": 0.0657 }
          }
        },
        {
          "stage": "world_classification",
          "status": "applied",
          "delta": {
            "summary": "midupper_world / midupper_route",
            "outputs": { "world": "midupper_world", "sub_world": "midupper_route" }
          }
        },
        {
          "stage": "candidate_pool",
          "status": "not_applied",
          "delta": { "summary": "Product Pool 未配線（PI CE 経路）" }
        },
        {
          "stage": "repick",
          "status": "not_applied",
          "delta": {
            "summary": "RePick 未実行（observer_repick_ready=1）",
            "inputs": { "observer_repick_ready_flag": 1 }
          }
        },
        {
          "stage": "delete",
          "status": "locked",
          "delta": { "summary": "Delete Boundary — 変更禁止" }
        },
        {
          "stage": "mark_assignment",
          "status": "applied",
          "delta": {
            "summary": "Rank1 → ◎（honmei）",
            "before": { "mark": null },
            "after": { "mark": "honmei" }
          }
        }
      ]
    }
  }
}
```

---

## 8. Feature Flag 設計

| Flag | レイヤ | 既定 | 効果 |
|------|--------|------|------|
| `WIN5_EXPLAIN_V2_ENABLED` | AI Core | **false** | `explain_payload` 生成 |
| `EXPLAIN_V2_ENABLED` | PI API | **false** | pass-through 有効化 |
| `EXPLAIN_V2_ENABLED` | BFF | **false** | mapper v2.1 組み立て |
| `v2_explain` | Web UI | **false** | ◎ 理由パネル表示 |

**原則:** 全 Flag OFF ≡ v1.1 完全同等（explain 空）。

---

## 9. テスト計画（実装フェーズ）

| テスト | 内容 |
|--------|------|
| Contract | explain 2.1 サブスキーマ JSON Schema 検証 |
| Mapper | PI fixture → reason / confidence_reason / decision_trace 非空 |
| Regression | Flag OFF → 既存 snapshot 一致 |
| UI | ◎ カード + reasonsSection に summary 表示 |
| E2E | 本番 PI race_id で「理由データなし」が消える |

---

## 10. フェーズ分割

| Phase | スコープ | 説明深度 |
|-------|----------|----------|
| **Phase 1** | CE + World + Confidence + mark | 「なぜ CE 上で ◎ か」 |
| **Phase 2** | Product journal → Pool/Entry/RePick | 「なぜ Product でも ◎ か」 |
| **Phase 3** | Kaoba / 会話 AI 連携 | `explain_pick` intent に reason 注入 |

---

## 11. リスクと緩和

| リスク | 緩和 |
|--------|------|
| CE のみ説明で Product 実態と乖離 | decision_trace で `not_applied` を明示 |
| 過度な技術用語 | labels.ja.json + summary テンプレ |
| 契約破壊 | explain サブスキーム additive、required 不変 |
| v1.1 Baseline 抵触 | Feature Flag 既定 OFF |

---

## 12. 実装前チェックリスト

- [x] 本設計レビュー Phase 1 承認（2026-07-21 — decision_key / contribution・weight / trace delta）
- [x] `contracts/single-explain/1.0/` 追加（labels.ja.json）
- [x] ① Core `explain_payload` + Flag
- [x] ② PI pass-through
- [x] ③ BFF `explainBuilder.js`
- [x] ④ Web `v2_explain` UI
- [x] 契約テスト更新
- [x] 本番有効化前 E2E（Flag 行列 / 実レース表示 / legacy 互換 / payload 欠損耐性）
      → `docs/ops/v2-explainability-phase1-e2e-report.md`（2026-07-22 **PASS → RC**）
- [x] Phase 2: Product journal → Pool / Entry / RePick（product_stages + decision_trace + factors）
      → docs/ops/v2-explainability-phase2-report.md（**PASS**）
- [x] Phase 3: Kaoba explain_pick · Payload/UI/trace 最終統合
      → docs/ops/v2-explainability-phase3-report.md
- [x] Explainability Final Report
      → docs/releases/v2-explainability-final-report.md

---

## 13. 関連文書

| 文書 | パス |
|------|------|
| v1.1 Release（explain 課題） | docs/releases/v1.1.md |
| PredictionBundle 2.0 | contracts/single-prediction-bundle/2.0/schema.json |
| PI Mapper | `functions/_lib/piPredictionMapper.js` |
| CE Pipeline | services/win5-ai/platform/core-overlay/ai_platform/core/candidate_evaluation/ |
| ConfidenceBuilder | .../core/confidence/__init__.py |
| Web 理由 UI | public/assets/api/prediction-bind.js |
| Phase 1 E2E RC レポート | docs/ops/v2-explainability-phase1-e2e-report.md |
| Phase 2 実施レポート | docs/ops/v2-explainability-phase2-report.md |
| Phase 3 実施レポート | docs/ops/v2-explainability-phase3-report.md |
| **Final Report** | docs/releases/v2-explainability-final-report.md |

---

**Explainability Phase 1–3 完了。** Final Report 提出済み — 受領待ち。
