# Version109 Phase UI1 — Component Mapping

**Date:** 2026-07-29  
**Status:** ADOPTED · 既存コンポーネント再利用

---

## 再利用（変更なし）

| Component | Path | UI1 |
|---|---|---|
| ExpectApi.Prediction | `public/assets/api/prediction.js` | **再利用** |
| ExpectPredictionBind | `public/assets/api/prediction-bind.js` | **再利用・非改修** |
| ExpectAnalysisBind | `public/assets/api/analysis-bind.js` | 評価内訳 · Bundle 派生 |
| race.html AI tab | `public/race.html` | **レイアウト非変更** |
| races.html / index.html | list cards | **非変更** |
| PredictionAdapter | `functions/_lib/adapters/predictionAdapter.js` | 既存経路維持 |

## 追加（View のみ）

| Component | Path | 役割 |
|---|---|---|
| Python Mapper | `app/ui_adaptation/single_to_bundle.py` | Single→Bundle |
| Python HTTP | `POST /v1/ui/prediction-bundle` | Mapper API |
| BFF Mapper | `functions/_lib/singleToBundleMapper.js` | 同一投影（local fallback） |
| BFF Route | `POST /api/ui/prediction-bundle` | same-origin |

## 未配線のまま（意図的）

| Component | 理由 |
|---|---|
| `ExpectApi.Single` | 既存 Prediction UI を置換しない |
| presentation renderer | 内部用語カードを出さない |
| ticket UI | UI1 範囲外 |

---

## コンポーネント対応表

| 既存 UI 部品 | 入力契約 | UI1 供給 |
|---|---|---|
| `marksSectionHtml` | Bundle runners.mark | Mapper ranks→mark |
| `pickCardsHtml` | Bundle runners | 同上 |
| `raceConfidenceDetailHtml` | Bundle.ai_confidence | base_bundle 維持 |
| `reasonsSectionHtml` | Bundle.explain | base_bundle 維持（空可） |
| `applyFromPredictionBundle` | ability_scores | base_bundle 再利用 |
| `applyHomeHonmeiCard` | Bundle | Mapper Bundle |
| `raceCardHtml` / summary | Bundle / RaceCardSummary | Mapper Bundle |
