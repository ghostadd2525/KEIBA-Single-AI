# I-2 Analyzer Registry — Implementation Notes

**Status:** **Approved** → I-3 へ進済  
**Depends:** I-1 Evidence Index  
**Boundary:** Development only. Production / Prediction Core 非変更。

---

## コマンド

```bash
npm run improve:index -- --date YYYY-MM-DD
npm run improve:analyze -- --date YYYY-MM-DD
npm run test:improve:i2
```

`--skip-index` で Index 再生成を省略可。

---

## Analyzer 契約

Schema: `contracts/expect-root-cause/1.0/schema.json`

各 Analyzer は必ず返す:

| フィールド | 型 | 説明 |
|------------|-----|------|
| `root_cause` | string | 主因コード |
| `confidence` | number 0–1 | 確信度 |
| `reason` | string | 人間可読の根拠 |

実装 Analyzer（4 のみ）:

| event_type | 関数 |
|------------|------|
| miss | `analyzeMiss` |
| feature_missing | `analyzeFeatureMissing` |
| prediction_failed | `analyzePredictionFailed` |
| result_sync_failed | `analyzeResultSyncFailed` |

未知 type → `status=unsupported`（Index のみ、解析スキップ）。

出力: `development/analysis/{event_type}/{run_id}.json` + `latest.json`  
Registry: `development/analysis/_registry.json`

各結果の `evidence_refs[]` は `event_id` / `event_type` / `path` / **`fingerprint`** を保持。

---

## Index 拡張（追加要件）

| 次元 | パス |
|------|------|
| by-date | `development/index/by-date/` |
| by-event-type | `development/index/by-event-type/` |
| **by-model-version** | `development/index/by-model-version/`（将来拡張済み） |
| clusters | `development/index/clusters/` |

`latest.json` に `dimensions.by_model_version: true` と `counts_by_model_version` を含む。

---

## 非スコープ（I-2）

- ~~Proposal 生成（I-3）~~ → **I-3 DONE**
- Canary / RC
- Lifecycle 遷移の強制適用以外の運用 UI

---

## テスト

`tests/contract/improve-i2-analyzer.test.mjs`
