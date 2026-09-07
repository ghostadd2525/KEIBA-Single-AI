# ADR-007 — AbilityScores CE Overlay Passthrough (Hard Lock Exception)

**Status:** Accepted · Version8.5.1 Certified Exception  
**Date:** 2026-07-27  
**Baseline:** Version8.5.1  
**Deciders:** Version8.5.1 Baseline Certification  
**Related:** docs/ops/v8-operations-baseline.md · docs/audit/v851-baseline-certification.md

---

## Context

Version8.5 Operations Baseline は **PE / CE / AI / Production ロジック変更を禁止**する。  
一方、評価内訳 UI は「モデル自信度」ではなく **馬の能力特徴量（％）** を表示する製品仕様が確定し、CE 行への AbilityScores 付帯が必要になった。

当該変更は作業ツリーおよび EC2 実行系に先行適用されていたが、git 正本・Hard Lock 文書への登録が無く、System Regression Audit で Baseline Integrity **FAIL** となった。

---

## Decision

Version8.5 Hard Lock の **例外（Exception）** として、次を **Version8.5.1 から正式採用**する。

| 項目 | 内容 |
|------|------|
| 対象 | services/win5-ai/platform/core-overlay/ai_platform/core/candidate_evaluation/__init__.py |
| 内容 | 
unners_frame から能力特徴量キーを読み、CE 行に AbilityScores を付与（透過） |
| BFF | unctions/_lib/piPredictionMapper.js が bility_scores へ投影 |
| UI | nalysis-bind.js が評価内訳バーに表示（既存） |

### なぜ Hard Lock 例外なのか

- Hard Lock の趣旨は **Rank / Confidence / Purchase / Prediction 判定ロジックの無断変更防止**である
- 本変更は **スコアリング式を変更せず**、既存特徴量を CE 契約へ **付帯フィールドとして透過**するだけである
- ただし CE 出力スキーマが変わるため、黙認ではなく **明示 Exception** とする

### PE を変更していない理由

- Purchase Engine / pool-entry / 購入選定ロジックには触れない
- ユーザー台帳・Challenge とも独立
- 能力値は表示・説明用途であり、購入エンジン入力を書き換えない

### CE Overlay のみであること

- 変更は **core-overlay の CandidateEvaluationProjector / CorePipeline 呼び出し引数**に限定
- Research 
esearch/ce-v2 は非変更（hash 同一方針を維持）
- Analyzer / Canary / 285R / Research Runner は非変更

### Version8.5.1 から正式採用する理由

1. 製品仕様（評価内訳＝能力特徴量％）として確定済み  
2. 差し戻しは本番 UX 回帰を招く  
3. Rank / Confidence 非変更が確認できる  
4. ADR + Baseline Registry + git 正本化により監査可能になる  

---

## Consequences

### Positive

- Baseline Integrity と製品仕様が一致する  
- 監査で「未コミット CE ドリフト」が解消される  

### Negative / Constraints

- CE JSON に AbilityScores が増える（後方互換: キー欠落は許容）  
- 今後の CE **ロジック**変更は引き続き Hard Lock（本 Exception の拡大解釈禁止）  

### Follow-ups

- EC2 overlay と git hash の定期照合  
- 署名付き JWT 移行は本 ADR の範囲外（Security Known Limitation）  

---

## Rejected Alternatives

| 案 | 却下理由 |
|----|----------|
| CE を HEAD へ差し戻す | 製品仕様・本番 UX に反する |
| PE 内で能力％を再計算 | PE Hard Lock と責務分離に反する |
| Exception 無しで黙認 | 監査不能・再発リスク |

---

## References

- docs/baselines/Version8.5.1.md
- docs/audit/v851-final-certification.md
