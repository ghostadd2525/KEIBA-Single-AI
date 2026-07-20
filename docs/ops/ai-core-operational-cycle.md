# AI-Core Operational Cycle — Runbook

**Phase:** AI-Core Operational Cycle  
**入力:** `evidence/improvement/`（同期済みのみ）  
**Production / Prediction Core:** 本サイクルでは変更しない

---

## 1. フロー

```
Evidence Sync (npm run evidence:sync)
  ↓
npm run improve:cycle [--date YYYY-MM-DD]
  ↓
Evidence Index → Analyzer → Proposal
  ↓
Human Review (development/reviews/{proposal_id}.json)
  ↓
再実行 improve:cycle → Canary
  ↓
Release Candidate（Canary pass のみ）
  ↓
Production Deploy（別手順・人手）
```

---

## 2. Evidence 0 件

| 動作 | 内容 |
|------|------|
| Verdict | **No Improvement Required** |
| Proposal | 作成しない |
| Canary | 実行しない |
| RC | 生成しない |
| Core | 変更しない |

```bash
npm run improve:cycle
# → verdict: "No Improvement Required"
```

---

## 3. Evidence あり

```bash
npm run evidence:sync -- --date 2026-07-19
npm run improve:cycle -- --date 2026-07-19
```

### Human Review（Canary 前）

`development/reviews/IMP-....json`:

```json
{
  "proposal_id": "IMP-20260719-miss-001",
  "status": "approved",
  "reviewed_by": "admin",
  "reviewed_at": "2026-07-20T12:00:00.000Z"
}
```

承認後に再実行:

```bash
npm run improve:cycle -- --date 2026-07-19
```

---

## 4. Execution Summary

毎回出力:

| フィールド | 説明 |
|------------|------|
| `verdict` | 判定文 |
| `evidence_count` | Evidence 件数 |
| `proposal_count` | 今回作成 Proposal 数 |
| `canary[]` | 各 Proposal の Canary 状態 |
| `release_candidate_count` | RC ディレクトリ総数 |
| `release_candidate_new` | 今回新規 RC |

保存先:

- `development/runs/{run_id}/execution-summary.json`
- `development/runs/latest-execution-summary.json`

---

## 5. 禁止事項

- Evidence 0 で Proposal / Canary / RC を生成しない（スクリプトが拒否）
- Canary pass 前の Prediction Core 変更
- OPS-Monitor / Result Automation の無効化

---

## 6. テスト

```bash
npm run test:improve
```
