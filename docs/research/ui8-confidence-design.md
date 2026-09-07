# UI8 — Confidence Design

**Date:** 2026-07-30  
**Scope:** レース一覧・ホームの自信度 UX（BFF Mapping / UI Mapping のみ）

## 目的

「このレースは買う価値があるか」を ★ と日本語文言だけで直感判断できるようにする。  
内部概念（World / Near Miss / Affinity / Residual）は **画面に出さない**。

## 表示（ユーザー向け）

| ★ | 文言 |
|---|---|
| ★★★★★ | 高い |
| ★★★★☆ | やや高い |
| ★★★☆☆ | ふつう |
| ★★☆☆☆ | 低い |

## 算出（内部）

```
AI 内部ラベル + confidence score → 最終表示 band
```

内部ラベル（UI 非表示・コード内のみ）:

- `normal`（Normal）
- `near_miss`（Near Miss）
- `affinity_residual`（Affinity Residual）
- `pure_residual`（Pure Residual）

### 合成ルール

1. ラベルから **天井 band** を決める  
   - Normal → high  
   - Near Miss → rather_high  
   - Affinity Residual → medium  
   - Pure Residual → low  
2. score から UI7 と同じ閾値で score band を求める（≥0.75 / ≥0.60 / ≥0.35）  
3. **最終 band = min(天井, score band)**（保守側）

→ score だけでは決まらない。ラベル天井が効く（例: Near Miss + score 0.9 → ★★★★☆）。

### ラベル由来

| 優先 | ソース |
|---|---|
| 1 | PI `near_miss` / `affinity`（あれば） |
| 2 | PI / Bundle `evaluation.world`（CEW: core / midupper / midhole / rank7 / …） |
| 3 | score 帯フォールバック（非 CEW world や欠落時） |

ラベル文字列そのものは RaceCardSummary / 画面 DOM に載せない（G109-UI1-5 整合）。

## 変更境界

| 変更可 | 変更禁止 |
|---|---|
| BFF Mapping（band 算出） | Core / CE / Rank / Confidence Score 本体 |
| UI Mapping（★・文言・本命選出） | Prediction Logic / Candidate Evaluation |
| Home Today's Pick | Race List Cache / 新規 HTTP API |

## 実装入口

- `functions/_lib/confidenceBands.js` — `resolveInternalLabel` / `confidenceBandFromLabelAndScore`
- `functions/_lib/piPredictionMapper.js` / `raceCardSummary.js` — band 適用
- `public/assets/api/prediction-bind.js` — 一覧・ホーム表示
