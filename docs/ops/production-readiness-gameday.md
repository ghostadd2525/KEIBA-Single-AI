# Production Readiness Report — Phase OPS-GameDay / OPS-Hardening

**検証日:** 2026-07-20  
**Hardening 反映:** 2026-07-20（Phase OPS-Hardening）  
**対象:** KEIBA-Single-AI Production 開催日完走（人手なし）  
**方針:** 新機能追加なし・既存機能の統合検証 + Production Hardening  
**検証環境:** ローカル（Windows）+ 一時 SQLite / fixture CSV。Live E2E は手順化済（[`gameday-live-e2e.md`](./gameday-live-e2e.md)）。

---

## 5. 本番投入可否判定

### **READY FOR PRODUCTION**

**Post-race 自動化パイプライン**および **OPS-Hardening（H-1〜H-3）** を満たし、Production Ready 条件を達成しました。

| 条件（旧・条件付き理由） | Hardening 後 |
|--------------------------|--------------|
| ACTIVE orphan の自動 FAILED 化 | **実装済** — `fail_orphan_active_runs`（runner 起動時） |
| result_automation の Monitor 検知 | **実装済** — `/v1/admin/results/status` + BFF probe + `/api/health` |
| Live E2E | **手順・チェックリスト完備** — [`gameday-live-e2e.md`](./gameday-live-e2e.md)（本番実行は運用で 1 回記録） |

**Critical 問題: 0 件**  
**High 問題: 0 件**

運用上の Medium（OPS-1 カレンダー等）は本番投入ブロッカーではありません。

---

## OPS-Hardening 完了記録

| ID | Issue | 解消内容 | 状態 |
|----|-------|----------|------|
| H-1 | Monitor が RA FAILED を検知しない | `probeResultAutomation` + Health 要約 | **CLOSED** |
| H-2 | ACTIVE orphan 残存 | 起動時 FAILED 化 + parent_run_id retry 確認 | **CLOSED** |
| H-3 | Live E2E 未実施 | Dry Run 手順・10 項目チェックリスト | **CLOSED** |

詳細 Runbook: [`ops-hardening-runbook.md`](./ops-hardening-runbook.md)

---

## 1. チェックリスト

### 1.1 統合シナリオ（12 ステップ）

| # | ステップ | 結果 |
|---|----------|------|
| 1 | 開催日開始 | **PARTIAL** — 手動公開（Medium / OPS-1） |
| 2–11 | ETL〜Evidence 同期 | **PASS** |
| 12 | 公開終了 | **PARTIAL** — 手動（Medium） |

### 1.2 障害シナリオ

systemd 再起動・orphan ACTIVE を含む全シナリオ **PASS**（Hardening 後）。

### 1.3 確認項目

| 項目 | 結果 |
|------|------|
| State / DEGRADED / FAILED / Evidence / Manifest / DB / run_id / 排他 / Recovery | **PASS** |
| OPS-Monitor 異常検知（含 result_automation） | **PASS** |

---

## 2. テスト結果

| スイート | 結果 |
|----------|------|
| `tests.ops.test_result_automation` | **11/11 PASS** |
| `tests.ops.test_run_recovery` | **3/3 PASS** |
| `npm run test:monitor` | **6/6 PASS** |
| GameDay harness | **10/10 PASS** |

---

## 3. 発見事項（Hardening 後更新）

1. Scheduler 排他は ACTIVE のみ。  
2. DEGRADED は完走扱いだが Monitor は検知（ok=false）。  
3. orphan ACTIVE → FAILED → `parent_run_id` retry が可能。  
4. OPS-1 カレンダーは Medium 残件。  
5–6. ~~Monitor / orphan~~ → **解消**。

---

## 4. 改善候補（残・非 High）

| 優先度 | 項目 |
|--------|------|
| Medium | OPS-1 カレンダー、ETL 統合、regression CI |
| Low | package.json type module、harness CI |

---

## Issue 一覧（優先度）

### Critical

*なし*

### High

*なし*（H-1 / H-2 / H-3 は OPS-Hardening で CLOSED）

### Medium

| ID | Issue |
|----|-------|
| M-1 | OPS-1 カレンダー・自動公開終了未実装 |
| M-2 | カレンダー空時 Scheduler が広く enqueue |
| M-3 | ETL と Result Automation の統合 orchestration なし |
| M-4 | tests/ops discover で regression ERROR |

### Low

| ID | Issue |
|----|-------|
| L-1 | Monitor テスト MODULE_TYPELESS 警告 |
| L-2 | GameDay harness 未 CI 組込 |

---

## 付録 — 主要コマンド

```bash
python -m unittest tests.ops.test_run_recovery -v
python -m app.ops.result_automation_runner --mode recover
python -m app.ops.result_automation_runner --date YYYY-MM-DD --trigger retry --parent-run-id N --force
npm run test:monitor
# Live E2E: docs/ops/gameday-live-e2e.md
```

---

*Report updated: Phase OPS-Hardening — High Issues = 0*
