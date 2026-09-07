# Version8.9 — Operations Console Audit

**Date:** 2026-07-27  
**Scope:** `/ops` Operations Console wiring（PE/CE/AI/RA/Research Logic 非変更）

---

## 完了条件チェック

| 条件 | 結果 |
|------|------|
| `/ops` で Research / Approval / Deploy / Knowledge / Reports / History / Evidence / Health / Audit を確認できる | ✅ |
| 表示は実データ / No Data / Pending のみ | ✅ |
| Production 自動適用なし | ✅ `production_auto_apply: false` |
| Boundary 維持 | ✅ Research → Approval → Deploy Note → Human Deploy |
| PE/CE/AI/RA/Research Logic 非変更 | ✅ Publish / BFF / UI のみ |

---

## カード追跡（抜粋）

| Card | Display | API | Publish | Runner | Source |
|------|---------|-----|---------|--------|--------|
| Approval Queue | counts + table | `/api/ops/approvals` | `approval-queue.json` | approval-queue + publish | `development/approvals/` |
| Current Week | week_id | `/api/ops/portal` / console | `portal-snapshot.json` | publishScheduler | `weekly-runner.json` |
| Next Run | ISO+09:00 | research-scheduler | `research-scheduler.json` | nextRunHintJst | scheduler state |
| Decision | decision | portal + artifacts | `artifacts/*/decision.json` | fri-decision（既存） | weekly fri-decision |
| deploy-note | path/action | portal | `deploy.json` + artifacts | Approve → note | `sat-deploy/` |
| Knowledge | counts | portal | `knowledge.json` + artifacts/knowledge | publishKnowledge | `development/knowledge/` |
| Weekly Report | week_id | portal | `reports.json` + artifacts | publishReports | `weekly/*/reports/` |
| PI / Pages / AI | Live status | `/api/ops/monitor-live` `/api/health` | — | — | live probes |
| ResultAutomation | run.status | `/api/ops/result-automation` | — | — | AI status（読取） |
| Timeline | steps | `/api/ops/timeline` | `timeline.json` | phases + publish | scheduler |
| Audit | matrix | console-audit | `console-audit.json` | publishConsoleLayer | docs |

フル一覧は Publish 成果物 `public/ops-data/console-audit.json`。

---

## Evidence リンク

| 領域 | 根拠 |
|------|------|
| Research | proposal-validation / ranked-run / baseline-285r / decision |
| Knowledge | accepted_patterns.json / rejected_patterns.json |
| Deploy | deploy-note.json / .md |
| Reports | weekly-ops-report / boundary-audit / incident |

公開パス: `/ops-data/artifacts/...`（Publish 時コピー）

---

## Approval Timeout

| 表示 | 値 |
|------|-----|
| Expire | `expires_at` |
| Remaining | 計算日数（欠損時 No Data） |
| Timeout 行 | Status=Timeout / Rejected + `reason=approval_timeout` + `auto=true` |

---

## Live Monitor ステータス語彙

| 語 | 意味 |
|----|------|
| Healthy | probe ok / status ok |
| Pending | skipped / pending |
| Failed | ok=false / unhealthy / FAILED |
| No Data | 取得不可・キーなし |

---

## 修正・追加ファイル

- `scripts/ops/v8/publish-console-v89.mjs`
- `scripts/ops/v8/publish-ops-snapshot.mjs`（console layer 呼び出し）
- `functions/_lib/opsConsole.js`
- `functions/api/ops/console.js` / `history.js` / `timeline.js` / `evidence.js` / `search.js` / `monitor-live.js`
- `public/ops.html` / `assets/ops-console-v89.js` / `assets/ops-console.css`
- `docs/ops/v8.9-operations-console.md`

---

## 検証手順

1. `npm run v8:publish`
2. ADMIN で `/ops` を開く
3. Approval が先頭タブであること
4. Timeline / Evidence / Download / Audit が Publish 実ファイルを指すこと
5. View JSON で Publish + API を確認できること
