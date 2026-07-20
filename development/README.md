# Development — AI 改善専用ワークスペース

**Production コード・サービスをここで実行しないこと。**

入力は **`evidence/improvement/`** のみ（正本）。

| ディレクトリ | 用途 |
|--------------|------|
| `index/` | Evidence Index（実装後） |
| `analysis/` | Root Cause（event_type 分離）+ Analyzer Registry |
| `proposals/` | 改善設計書（コード禁止） |
| `canary/configs/` | Canary Config |
| `canary/reports/` | Canary Report（要約） |
| `canary/criteria/` | Success / Rollback Criteria |
| `canary/results/` | **Canary Result**（I-4 独立成果物） |
| `release-candidates/` | RC Gate 合格時のみ（Manifest 付き） |

## 設計正本

- Pipeline: [`docs/ops/ai-improvement-pipeline.md`](../docs/ops/ai-improvement-pipeline.md)
- Runbook: [`docs/ops/ai-improvement-runbook.md`](../docs/ops/ai-improvement-runbook.md)

## フロー（運用）

```bash
npm run evidence:sync -- --date YYYY-MM-DD
npm run improve:index -- --date YYYY-MM-DD   # I-1
npm run improve:analyze -- --date YYYY-MM-DD # I-2
# I-3+ after review approval
```

詳細:

- I-1: [`docs/ops/improve-i1-evidence-index.md`](../docs/ops/improve-i1-evidence-index.md)
- I-2: [`docs/ops/improve-i2-analyzer-registry.md`](../docs/ops/improve-i2-analyzer-registry.md)
- I-3: [`docs/ops/improve-i3-proposal-generator.md`](../docs/ops/improve-i3-proposal-generator.md)
- I-4: [`docs/ops/improve-i4-canary.md`](../docs/ops/improve-i4-canary.md)
- I-5: [`docs/ops/improve-i5-rc-gate.md`](../docs/ops/improve-i5-rc-gate.md)

```
evidence/improvement → Index (I-1) → Analyzer (I-2) → Proposal (I-3) → Canary Result (I-4) → …
```

禁止:

- 本番 DB への書き込み
- Production 上での Prediction Core 変更
- Proposal へのコード生成
- Canary FAIL の RC 化
- 大量 CSV のコミット
