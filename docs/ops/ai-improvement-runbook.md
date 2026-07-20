# AI-Improvement Pipeline — Runbook

**対象:** Development（Local）。Production では実行しない。  
**設計正本:** [`ai-improvement-pipeline.md`](./ai-improvement-pipeline.md)

---

## 0. 前提チェック

- [ ] `evidence/improvement/` に対象日の Evidence / Manifest がある
- [ ] Prediction Core / 本番 DB に書き込まない
- [ ] 作業ブランチは Development 用（例: `dev/improvement-*`）

```bash
# Evidence 同期（Production 側で生成後）
npm run evidence:sync -- --date YYYY-MM-DD
```

---

## 1. 日常フロー（手動・設計フェーズ）

### Step 1 — Evidence Index（実装後は CLI）

現状（設計レビュー前）:

1. `evidence/improvement/{event_type}/{date}/` を列挙
2. 件数・fingerprint をメモ（将来: `development/index/`）

### Step 2 — Root Cause Analysis

event_type ごとに分離して分析する。

| event_type | 出力先（設計） |
|------------|----------------|
| miss | `development/analysis/miss/` |
| feature_missing | `development/analysis/feature_missing/` |
| prediction_failed | `development/analysis/prediction_failed/` |
| result_sync_failed | `development/analysis/result_sync_failed/` |

未知 type はスキップし、Issue に「Analyzer 未登録」と記録。

### Step 3 — Improvement Proposal（I-3）

```bash
npm run improve:propose -- --date YYYY-MM-DD
```

生成物: `development/proposals/{IMP-...}.json` + `.md`（`status=DRAFT`）

必須チェック:

1. 5 項目（目的 / 対象 / 期待効果 / 副作用 / 評価方法）
2. **`evidence_refs` ≥ 1**（`event_id` / `event_type` / `path`）
3. **`analysis_refs`**（Analyzer 参照。`confidence` は advisory）
4. **コード・パッチを書かない**
5. Lifecycle 埋め込み。採否は Human Review（confidence 単独禁止）

手動テンプレート: `development/proposals/_TEMPLATE.md`

### Step 4 — Canary（I-4）

```bash
npm run improve:canary -- --proposal IMP-...
```

成果物:

```
canary/configs/{proposal_id}.json
canary/criteria/{proposal_id}.json
canary/results/{proposal_id}/{run_id}.json   # 独立 Canary Result
canary/results/{proposal_id}/latest.json
canary/reports/{proposal_id}.json            # 要約
```

テンプレート: `development/canary/**/_TEMPLATE.json`（Result: `canary/results/_TEMPLATE.json`）

### Step 5 — Canary 評価

Human Review `approved` 後に CLI / Cycle がゲート評価し **Canary Result** を生成。

- critical 全 pass → `PASS` または warning のみ fail → `PASS_WITH_WARNING`
- critical fail → `FAIL`
- Proposal 本文は不変。Lifecycle は Result 根拠で `CANARY_PASS` / `CANARY_FAIL`

### Step 6 — Release Candidate（I-5 RC Gate）

```bash
npm run improve:rc -- --proposal IMP-...
```

**RC Gate 必須条件（Canary Result 正本参照）:**

- Canary `PASS` または `PASS_WITH_WARNING`
- Human Review `approved`
- `evidence_refs` 有効
- Proposal Lifecycle `CANARY_PASS`

```
development/release-candidates/{proposal_id}/
  candidate.json
  manifest.json      # RC Manifest（proposal_id / result_id 相互参照）
  checklist.md
  links.json
```

FAIL / Gate 不合格の Proposal を RC に入れない。

### Step 7 — Human Review

チェックリストを埋め、承認者・日時を記録。

- Approve → 既存 Production デプロイ手順へ
- Reject / Revise → Proposal に差し戻し

### Step 8 — Production Deploy

承認済み RC のみ。Deploy 後は OPS-Monitor で健全性確認。問題時は Rollback Criteria に従う。

---

## 2. ゲート早見表

| ゲート | 条件 |
|--------|------|
| Proposal 作成可 | Evidence / RCA あり |
| Canary 開始可 | Proposal 5 項目充足・コードなし |
| RC 出力可 | RC Gate 全 structural pass + Canary Result 正本 |
| Deploy 可 | Human `approved` |

---

## 3. 禁止事項

- Production での改善実行
- Proposal への実装コード混入
- Canary 未実施 / FAIL の RC 化
- OPS-Monitor / Result Automation 設定の「改善のための恒久無効化」

---

## 4. トラブルシュート

| 症状 | 対応 |
|------|------|
| Evidence が空 | Result Automation / `evidence:sync` 確認 |
| 未知 event_type | Analyzer Registry に追加（実装フェーズ） |
| Canary 曖昧 | Success / Rollback を定量化して criteria を更新 |
| Deploy 後劣化 | Rollback Criteria → 前版デプロイ + Monitor |

---

## 5. 実装後コマンド（予約）

```text
# 設計承認後に追加予定（現時点では未実装）
npm run improve:index -- --date YYYY-MM-DD
npm run improve:analyze -- --date YYYY-MM-DD
npm run improve:propose -- --date YYYY-MM-DD
npm run improve:propose -- --event-type miss
npm run improve:propose -- --cluster <fingerprint>
npm run improve:canary -- --proposal IMP-...
npm run improve:rc -- --proposal IMP-...   # pass のみ
```
