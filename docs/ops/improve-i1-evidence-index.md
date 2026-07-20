# I-1 Evidence Index — Implementation Notes

**Status:** Implemented (awaiting review)  
**Scope:** Evidence Index CLI only. Analyzer / Proposal / Canary / RC は未実装（I-2+）。  
**Boundary:** Production は `evidence/improvement` を書くだけ。Development は Index を読む・書く。

---

## コマンド

```bash
npm run evidence:sync -- --date YYYY-MM-DD   # Production → Git path
npm run improve:index -- --date YYYY-MM-DD   # I-1
npm run test:improve:i1
```

---

## 出力

| パス | 内容 |
|------|------|
| `development/index/latest.json` | 全体 Index |
| `development/index/by-date/{date}.json` | 日次 |
| `development/index/by-event-type/{type}.json` | 種別 |
| `development/index/by-event-type/summary.json` | 集計 |
| `development/index/clusters/{cluster_id}.json` | 指紋クラスタ |

Schema: `contracts/expect-evidence-index/1.0/schema.json`

各 `events[]` 要素は Proposal 追跡用に:

- `event_id`
- `event_type`
- `path`（`evidence/improvement/...`）
- `fingerprint`

を持つ。

---

## 追加要件（スキーマ先行・I-3 で強制）

### Proposal Lifecycle

契約: `contracts/expect-proposal-lifecycle/1.0/schema.json`  
実装: `scripts/ops/improvement/lib/lifecycle.mjs`

```
DRAFT → UNDER_REVIEW → APPROVED → CANARY_RUNNING
  → CANARY_PASS → RC_CREATED → DEPLOYED
  → CANARY_FAIL | REJECTED | ARCHIVED
```

### Evidence 参照

`expect-improvement-proposal/1.0` の `evidence_refs` を **必須** に更新。

各 ref: `event_id`, `event_type`, `path`（+ 任意 race_date / fingerprint / cluster_id）

---

## 非スコープ（I-1）

- Analyzer 実行
- Proposal 生成
- Canary / RC
- Prediction Core / Production 変更

---

## テスト

`tests/contract/improve-i1-index.test.mjs`
