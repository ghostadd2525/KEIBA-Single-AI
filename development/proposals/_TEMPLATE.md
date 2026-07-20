# Improvement Proposal — IMP-YYYYMMDD-{type}-{seq}

> **コード生成禁止。** 本ファイルは設計書のみ。パッチ・実装・スクリプトを貼らないこと。  
> Schema: `expect-improvement-proposal/1.0` · Lifecycle: `DRAFT` …  
> **Confidence:** Analyzer 値は参考情報。採否は Human Review + Lifecycle のみ。

| 項目 | 値 |
|------|-----|
| proposal_id | `IMP-________-____-___` |
| status | `DRAFT` |
| event_types | `miss` / `feature_missing` / `prediction_failed` / `result_sync_failed` / \<future\> |
| fingerprints | |
| evidence_refs | （1 件以上必須） |
| analysis_refs | （Analyzer 参照・推奨） |
| created_at | |

---

## 1. 目的（purpose）

（何を良くしたいか。1〜3 文）

## 2. 対象（target）

（コンポーネント・データ経路・運用手順。Production Core 直書きは書かない）

## 3. 期待効果（expected_effect）

（定量があれば望ましい。例: miss_top1 率、feature 充足率）

## 4. 副作用（side_effects）

- （最低 1 件。無しの場合「想定副作用なし（要 Canary で確認）」と明記）

## 5. 評価方法（evaluation_method）

（どの Evidence / 指標 / Canary ゲートで判断するか）

---

## 非目標（non_goals）

- Production 上での即時 Core 変更
- Analyzer confidence のみでの採否
- （その他）

## Evidence refs（必須）

- `event_id` / `event_type` / `path`（+ fingerprint 推奨）

## Analysis refs

- `analysis_id` / `event_type` / `path`（+ root_cause / confidence advisory）

## metadata（任意・拡張用）

```json
{
  "confidence_policy": { "role": "advisory_only" },
  "analyzer_confidence": null
}
```

## Canary への引き継ぎ

- Config: `development/canary/configs/{proposal_id}.json`
- Criteria: `development/canary/criteria/{proposal_id}.json`
