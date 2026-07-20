# I-4 Canary — Implementation Notes

**Status:** Implemented (awaiting evaluation criteria & Lifecycle linkage review)  
**Depends:** I-3 Proposal Generator (approved)  
**Boundary:** Development only. Production / Prediction Core 非変更。

---

## コマンド

```bash
npm run improve:canary -- --proposal IMP-20260719-miss-001
npm run improve:canary -- --proposal IMP-... --date 2026-07-19
npm run improve:canary -- --proposal IMP-... --skip-lifecycle
npm run test:improve:i4
```

| フラグ | 意味 |
|--------|------|
| `--proposal` | **必須** — 対象 Proposal ID |
| `--date` | Evidence 日付フィルタ |
| `--skip-lifecycle` | Canary Result のみ生成し Lifecycle 遷移をスキップ |
| `--evidence-root` / `--dev-root` | パス上書き（テスト用） |

Cycle 一括実行: `npm run improve:cycle`（Canary は batch `runCanary` を内包）。

---

## 入出力

| 入力 | 説明 |
|------|------|
| `development/proposals/{proposal_id}.json` | I-3 Proposal |
| `development/reviews/{proposal_id}.json` | Human Review（`status=approved` で評価実行） |
| Evidence corpus | `evidence/improvement/**`（scan + index） |

| 出力（独立成果物） | パス |
|--------------------|------|
| **Canary Result** | `development/canary/results/{proposal_id}/{run_id}.json` |
| **Latest pointer** | `development/canary/results/{proposal_id}/latest.json` |
| Config / Criteria | `development/canary/configs\|criteria/{proposal_id}.json` |
| Report（要約・レガシー） | `development/canary/reports/{proposal_id}.json` |
| Run summary | `development/runs/{run_id}/canary-summary.json` |

Schema: `contracts/expect-canary-result/1.0/schema.json`

---

## 相互追跡（proposal_id）

- Canary Result は `proposal_id` を必須保持
- `result_id` は `CAN-{proposal_id}-{run_id}` 形式
- `refs.proposal_path` → Proposal JSON
- Proposal 側は **本文を書き換えず** `metadata` にポインタのみ追加:
  - `latest_canary_result_id`
  - `latest_canary_result_path`
  - `latest_canary_verdict`
  - `latest_canary_evaluated_at`

---

## 判定（3 状態）

| Verdict | 意味 | Lifecycle（Human Review 済 + 遷移可能時） |
|---------|------|---------------------------------------------|
| `PASS` | 全 critical gate 合格 | → `CANARY_PASS` |
| `PASS_WITH_WARNING` | critical 合格・warning gate のみ失敗 | → `CANARY_PASS` |
| `FAIL` | critical gate 失敗 | → `CANARY_FAIL` |

Human Review 未承認時:

- `evaluation_status: pending_human_review`
- `verdict: null`
- Lifecycle **不更新**（Canary Result は pending として記録）

---

## 評価ゲート（オフライン構造 Canary）

| Gate ID | Severity | 条件 |
|---------|----------|------|
| `corpus_documented` | critical | 対象 event_type の Evidence ≥ 1 |
| `no_core_change_in_canary` | critical | オフライン評価 — Core 不変（常時 pass） |
| `proposal_evidence_linked` | critical | Proposal `evidence_refs` が corpus path と 1 件以上一致 |
| `analysis_refs_present` | warning | `analysis_refs.length ≥ 1` |
| `miss_categories_enumerated` | critical（miss のみ） | payload に miss_category 分布 |
| `feature_signals_present` | warning（feature_missing のみ） | `fallback_reason` または `feature_source` |

Verdict 導出:

1. critical いずれか fail → **FAIL**
2. critical 全 pass + warning fail → **PASS_WITH_WARNING**
3. それ以外 → **PASS**

Analyzer `confidence` は Canary 判定に**使用しない**（`metadata.confidence_policy` と同様 advisory only）。

---

## Lifecycle 連携

```
APPROVED ──(Canary start)──► CANARY_RUNNING ──► CANARY_PASS | CANARY_FAIL
                                      ▲
                                      └── 根拠: Canary Result（本文は不変）
```

- `applyLifecycleFromCanaryResult` が Result を読み、`transitionProposal` のみ実行
- `purpose` / `target` / `evidence_refs` / `analysis_refs` 等は **触らない**
- `lifecycle_applied` を Result に記録（監査用）

RC 出力（I-5 前提）:

- `PASS` と `PASS_WITH_WARNING` のみ RC 生成可（`isCanaryRcEligible`）
- RC `links.canary_result` が Canary Result を参照

---

## テスト

```bash
npm run test:improve:i4    # I-4 契約・3 状態・Lifecycle・CLI
npm run test:improve:i3    # I-3 回帰
npm run test:improve       # Cycle 回帰
```

---

## レビュー観点（I-4 完了時）

1. ゲート定義は Development オフライン Canary として妥当か
2. `PASS_WITH_WARNING` を `CANARY_PASS` に寄せる設計は RC 前の運用と整合するか
3. Proposal 非書換 + metadata ポインタのみの監査可能性
4. Human Review ゲートと Canary 実行タイミング
