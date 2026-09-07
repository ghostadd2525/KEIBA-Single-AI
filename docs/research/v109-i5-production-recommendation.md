# Phase I5 — Production Recommendation

**Date:** 2026-07-29  
**Question:** Production Cutover（Flag ON）してよいか？

---

## Recommendation

| 判定 | **NO-GO（Cutover 延期）** |
|---|---|
| Confidence | High |

## Why

1. **本番に I3 Detail Wiring 未デプロイ**（`race.html` が Prediction のみ）
2. **本番に I4 Ops endpoint 到達不可**（Research Week `OPS_CLOSED`）
3. **本番 beta に `single_ai_detail` 未掲載**（DEFAULT OFF・運用キー未導入）
4. Live traffic 下の Alert 緑・Dashboard 実測が未取得

Repo / harness 上の手順リハーサルは **PASS**。これは「切替設計と FE/Ops ロジックは準備済み」を意味するが、**本番同環境での Flag ON 実地は未完了**。

## Required before Cutover（順序）

1. **Deploy** I3 + I4（Flag **OFF** のまま）to staging/production Pages
2. beta に `single_ai_detail: false` 明示キー追加（デプロイ時）
3. Staging（またはメンテ明け）で **Flag ON rehearse**（実 race_id + 可能なら core）
4. `/api/ops/single-detail` 緑 · ALT 誤報なし
5. I2 Gate 再々評価 → 明示承認後のみ Flag ON

## Explicit non-actions

- 今すぐ本番 Flag ON しない
- Race List / Cache に触れない
- Core / Consumer / Prediction / UI を変えない

## If deploy-only (no Flag ON)

I3/I4 を Flag OFF で出すのは **低リスク**（詳細は現状どおり Prediction）。Cutover とは別承認。
