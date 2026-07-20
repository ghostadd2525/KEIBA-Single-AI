# I-5 RC Gate — Implementation Notes

**Status:** Implemented (awaiting RC Gate & Release Candidate flow review)  
**Depends:** I-4 Canary (approved)  
**Boundary:** Development only. Production / Prediction Core 非変更。

---

## コマンド

```bash
npm run improve:rc -- --proposal IMP-20260719-miss-001
npm run improve:rc -- --proposal IMP-... --date 2026-07-19
npm run improve:rc -- --proposal IMP-... --skip-lifecycle
npm run test:improve:i5
```

| フラグ | 意味 |
|--------|------|
| `--proposal` | **必須** — 対象 Proposal ID |
| `--date` | Evidence 日付フィルタ |
| `--skip-lifecycle` | RC 生成のみ、`RC_CREATED` 遷移スキップ |
| `--kpi-regression` | KPI Regression gates 有効化（将来実装・現状は registry のみ） |
| `--evidence-root` / `--dev-root` | パス上書き（テスト用） |

Cycle: `npm run improve:cycle` が batch `emitReleaseCandidates` を内包。

---

## 設計原則

1. **Canary Result が正本** — `development/canary/results/{proposal_id}/latest.json` を disk から読み込み。Proposal の `metadata.latest_canary_verdict` 等から判定を**推測しない**。
2. **RC Gate 合格後のみ** Release Candidate パッケージを生成。
3. **RC Manifest** で `proposal_id` / `result_id` / `canary_result` を相互参照。
4. **KPI Regression gates** は registry で拡張可能（デフォルト disabled）。

---

## 必須 Structural Gates

| Gate ID | 条件 |
|---------|------|
| `canary_verdict_eligible` | Canary Result `evaluation_status=completed` かつ verdict ∈ {PASS, PASS_WITH_WARNING} |
| `human_review_approved` | `development/reviews/{proposal_id}.json` の `status=approved` |
| `evidence_refs_valid` | Proposal 構造検証 + evidence ファイル存在 + corpus リンク |
| `lifecycle_canary_pass` | Proposal `status=CANARY_PASS` |

いずれか critical fail → RC **拒否**（`rc-rejected` manifest を run dir に記録）。

---

## 成果物

| ファイル | 説明 |
|----------|------|
| `release-candidates/{proposal_id}/candidate.json` | Release Candidate |
| `release-candidates/{proposal_id}/manifest.json` | **RC Manifest**（ゲート結果・相互参照） |
| `release-candidates/{proposal_id}/links.json` | リンク集（`result_id` 含む） |
| `release-candidates/{proposal_id}/checklist.md` | 人手レビュー用 |
| `runs/{run_id}/rc-summary.json` | CLI / Cycle サマリー |

契約:

- `contracts/expect-rc-manifest/1.0/schema.json`
- `contracts/expect-release-candidate/1.0/schema.json`（`result_id`, `manifest_id` 追加）

---

## RC Manifest 相互参照

```json
{
  "manifest_id": "RCM-IMP-20260719-miss-001-{run_id}",
  "proposal_id": "IMP-20260719-miss-001",
  "result_id": "CAN-IMP-20260719-miss-001-{run_id}",
  "refs": {
    "proposal_path": "development/proposals/IMP-....json",
    "canary_result_path": "development/canary/results/IMP-.../latest.json",
    "candidate_path": "development/release-candidates/IMP-.../candidate.json",
    "manifest_path": "development/release-candidates/IMP-.../manifest.json"
  }
}
```

---

## Lifecycle 連携

```
CANARY_PASS ──(RC Gate pass)──► RC_CREATED
```

- `applyLifecycleFromRc` — Proposal 本文不変、`metadata.latest_rc_*` のみ更新
- 根拠: RC Manifest + Canary Result `result_id`

---

## KPI Regression 拡張（将来）

Registry（`KPI_REGRESSION_GATE_REGISTRY`）:

| Gate ID | 説明 | デフォルト |
|---------|------|------------|
| `kpi_hit_rate_non_regression` | hit_at_1 / 的中率 | disabled |
| `kpi_recovery_rate_non_regression` | 回収率 | disabled |
| `kpi_calibration_non_regression` | Calibration drift | disabled |

`--kpi-regression` または `kpiRegressionEnabled: true` で phase を有効化。実測 KPI 連携は将来フェーズ。

---

## テスト

```bash
npm run test:improve:i5
npm run test:improve:i4
npm run test:improve
```

---

## レビュー観点（I-5 完了時）

1. Canary Result 正本参照 — Proposal 推測なし
2. 4 必須 gate の妥当性
3. Manifest 相互参照の監査可能性
4. KPI gate 拡張ポイントの明確さ
