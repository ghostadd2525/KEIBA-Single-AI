# Version109 Phase UI1 — UI Mapping

**Date:** 2026-07-29  
**Status:** ADOPTED · Existing UI 主役 · Single AI はデータ供給のみ  
**PredictionBundle:** `single-prediction-bundle/2.0` **維持**

---

## 原則

| 原則 | 内容 |
|---|---|
| UI 主役 | 既存画面構成・デザイン・導線を維持 |
| AI 従属 | Single AI 結果を既存スロットへ投影 |
| 契約 | PredictionBundle 2.0 を壊さない |
| 非表示 | World / Near Miss / Affinity / Explanation Confidence |

---

## 対象画面 → Bundle スロット

| 画面 | 既存 UI スロット | Bundle フィールド | Single 由来 |
|---|---|---|---|
| レース一覧 | カード本命・自信度 | `race_info` · `evaluation.runners` · `ai_confidence` | ranks→marks · confidence は base_bundle 維持 |
| レース詳細 | AI予想タブ全体 | Bundle 全体 | View Mapper 出力 |
| 印（◎○▲△） | `#marksSectionBody` | `evaluation.runners[].mark` | `core_payload.prediction.ranks` 順位→印 |
| 対抗・穴 | `#pickCardsBody` | mark=`taikou`/`ana`/`chuuken` | 同上 |
| 評価内訳 | `#chartCard` / score-list | honmei `ability_scores` | **base_bundle から再利用**（Presentation には無い） |
| このレースの自信度 | `#raceConfidenceDetail` | `ai_confidence.score/band/component_scores` | **EC 禁止** · base Product confidence |

---

## 印マッピング（既存 Product と同じ）

| model_rank | mark | 表示 |
|---|---|---|
| 1 | honmei | ◎ |
| 2 | taikou | ○ |
| 3 | ana | ▲ |
| 4 | chuuken | △ |
| 他 | none | — |

---

## 明示的にマップしない

| Single / Core フィールド | UI |
|---|---|
| `world_id` / presentation.world | **表示しない**（`evaluation.world=null`） |
| near_miss / affinity | **表示しない** |
| explanation_confidence | **自信度に使わない** |
| natural_explanation / decision_reason | null 維持 |
| ticket | 既存買い目 UI を置換しない |

---

## フロー

```text
SingleResponse / core_payload
        │
        ▼
UI1 View Mapper (single_to_prediction_bundle)
        │
        ▼
PredictionBundle 2.0  （world=null sanitize）
        │
        ▼
ExpectApi.Prediction 経路と同じ bind
ExpectPredictionBind.*  （レイアウト変更なし）
```
