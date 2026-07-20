# I-3 Proposal Generator — Implementation Notes

**Status:** Implemented (awaiting Lifecycle / evidence_refs re-review)  
**Depends:** I-2 Analyzer Registry (approved)  
**Boundary:** Development only. Production / Prediction Core 非変更。

---

## コマンド

```bash
npm run improve:index -- --date YYYY-MM-DD
npm run improve:analyze -- --date YYYY-MM-DD
npm run improve:propose -- --date YYYY-MM-DD
npm run improve:propose -- --event-type miss
npm run improve:propose -- --cluster sha256:...
npm run improve:propose -- --reuse-analysis
npm run test:improve:i3
```

| フラグ | 意味 |
|--------|------|
| `--date` | Evidence 日付フィルタ |
| `--event-type` | 単一 event_type のみ Proposal 化 |
| `--cluster` | fingerprint 一致の Evidence のみ参照 |
| `--reuse-analysis` | `development/analysis/*/latest.json` を再利用（無ければ Analyzer 再実行） |
| `--skip-index` | Index 再生成スキップ（latest Index または scan を利用） |
| `--evidence-root` / `--dev-root` | パス上書き（テスト用） |

0 Evidence → Proposal 0 件（空コーパス）。

---

## Proposal 契約（追加要件対応）

Schema: `contracts/expect-improvement-proposal/1.0/schema.json`

### evidence_refs（必須）

| フィールド | 必須 |
|------------|------|
| `event_id` | ✓ |
| `event_type` | ✓ |
| `path` | ✓ |
| fingerprint / race_date / race_id / cluster_id | 任意 |

`evidence_refs.length < 1` の Proposal は **生成・検証とも拒否**。

### analysis_refs（構造化）

Analyzer（`expect-root-cause/1.0`）結果への参照:

| フィールド | 必須 | 説明 |
|------------|------|------|
| `analysis_id` | ✓ | Analyzer 出力 ID |
| `event_type` | ✓ | |
| `path` | ✓ | `development/analysis/{type}/{run_id}.json` |
| `root_cause` | 任意 | コピー |
| `confidence` | 任意 | **advisory only** |
| `reason` | 任意 | |

後方互換: 読取時はレガシーな文字列 path も `normalizeAnalysisRef` でオブジェクト化可能。

### confidence 採否ポリシー

```
metadata.confidence_policy.role = "advisory_only"
acceptance_requires = ["evidence_refs", "human_review", "lifecycle_transition"]
```

- Analyzer `confidence` は `metadata.analyzer_confidence` / `analysis_refs[].confidence` に記録可
- `review_priority_hint` はレビュー優先度のヒントのみ
- **confidence の高低だけで DRAFT 生成スキップ・APPROVED/REJECTED は行わない**
- Lifecycle 遷移 API も confidence を参照しない

### 後方互換（拡張フィールド）

- ルート `additionalProperties: true`
- 任意 `metadata` オブジェクト（追加キー許容）
- `evidence_refs` / `analysis_refs` の各要素も `additionalProperties: true`

---

## Lifecycle（I-3 強制）

実装: `scripts/ops/improvement/lib/lifecycle.mjs`

生成時: `status=DRAFT` + 埋め込み `lifecycle`（`expect-proposal-lifecycle/1.0`）

```
DRAFT → UNDER_REVIEW → APPROVED → CANARY_RUNNING
  → CANARY_PASS → RC_CREATED → DEPLOYED
分岐: CANARY_FAIL | REJECTED | ARCHIVED
```

`transitionStoredProposal(devRoot, id, nextStatus)` が合法遷移のみ許可。

---

## 成果物

| パス | 内容 |
|------|------|
| `development/proposals/{IMP-...}.json` | 機械可読 Proposal |
| `development/proposals/{IMP-...}.md` | 設計書（コード禁止） |
| `development/runs/{run_id}/propose-summary.json` | 実行サマリ |
| `development/runs/latest-propose-summary.json` | 最新サマリ |

---

## 非スコープ（I-3）

- Canary 4 点セット評価（I-4）
- RC 出力（I-5）
- Prediction Core / Production 変更
- Proposal からのコード生成

---

## テスト

`tests/contract/improve-i3-proposal.test.mjs`
