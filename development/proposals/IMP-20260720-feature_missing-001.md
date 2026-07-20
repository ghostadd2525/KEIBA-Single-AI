# Improvement Proposal — IMP-20260720-feature_missing-001

> **コード生成禁止。** Prediction Core は本 Proposal の対象外。  
> Schema: `expect-improvement-proposal/1.0`

| 項目 | 値 |
|------|-----|
| proposal_id | `IMP-20260720-feature_missing-001` |
| status | `ready_for_canary` |
| event_types | `feature_missing` |
| fingerprints | `F-ETL-LATE`, `F-MARKET`, `F-META-NONE` |
| created_at | 2026-07-20T11:35:00Z |

---

## 1. 目的（purpose）

`feature_missing` の発生をデータ供給・メタ付与の設計で削減し、mock/fallback 依存を減らす。欠落下の miss を Core 問題と誤認しない運用境界を明確化する。

## 2. 対象（target）

- ETL / Feature 供給の完了定義（開催日ゲート）
- `fallback_reason` / `feature_source` の正規化方針
- 公開前の「Feature 充足チェック」設計（BFF/運用。Core 非変更）

## 3. 期待効果（expected_effect）

- 同条件開催日で `feature_missing` イベント件数がベースライン以下
- `engine_source=mock_fallback` かつ feature 起因の比率が非増加
- miss との併発率が改善または非悪化

## 4. 副作用（side_effects）

- 充足ゲートを厳しくすると公開開始が遅れる可能性
- メタ正規化により過去 Evidence とのラベル比較がずれる
- Monitor アラートが増える短期ノイズ

## 5. 評価方法（evaluation_method）

1. Feature 欠落検出ルールに一致する fixture / 実 Evidence でベースライン計測
2. Canary Criteria の供給系ゲートで評価（Core メトリクスは参照のみ）
3. PASS 後の実装対象は **データ供給・メタ・運用ゲート**（Prediction Core は含めない）

---

## 非目標（non_goals）

- Prediction Core の重み・ランキング変更
- feature 欠落を隠すための無音 mock 成功の恒久化
- Result Automation / OPS-Monitor の無効化

## Evidence / Analysis 参照

- analysis: `development/analysis/feature_missing/2026-07-20-root-cause.md`

## Canary への引き継ぎ

- Config / Criteria / Report: `IMP-20260720-feature_missing-001`
