# Phase I2 — Release Checklist

**Date:** 2026-07-29  
**用途:** Production Cutover 前チェック。本票時点では **未充足項目あり → リリース禁止**。

---

## A. Product Locks（必須 · すべて PASS 必須）

| ID | 項目 | Status |
|---|---|---|
| A1 | `expect_race_list_cache_v4` 非変更 | PASS |
| A2 | `expect_pb_prefetch_v1` 非変更 | PASS |
| A3 | TTL 5分 非変更 | PASS |
| A4 | Cache 更新方法 非変更 | PASS |
| A5 | 一覧 HTTP 経路に Single なし | PASS |
| A6 | 一覧に single.js 未ロード | PASS |
| A7 | Core / Prediction / Consumer / Contract / UI layout 非変更（本 Gate） | PASS |

## B. Detail Cutover Preconditions

| ID | 項目 | Status |
|---|---|---|
| B1 | FE Feature Flag（詳細のみ）定義・配線 | **FAIL / 未実装** |
| B2 | Flag OFF → Prediction フォールバック | **FAIL / 未実装** |
| B3 | Timeout → フォールバック | **FAIL / 未実装** |
| B4 | UI1 Mapper 経由で Bundle 2.0 供給 | Mapper PASS · **配線 FAIL** |
| B5 | Staging で B1–B4 実地 | **FAIL** |

## C. Ops

| ID | 項目 | Status |
|---|---|---|
| C1 | Flag 運用手順書 | PASS（本シリーズ文書） |
| C2 | Rollback Checklist | PASS（文書） |
| C3 | Health endpoints | PASS |
| C4 | Metrics endpoint | PARTIAL |
| C5 | Alert rules 本番 | **FAIL** |
| C6 | On-call sign-off | **FAIL** |

## D. Go / No-Go

| 条件 | 結果 |
|---|---|
| A すべて PASS | Yes |
| B すべて PASS | **No** |
| C5 Alert PASS | **No** |
| **Release** | **NO-GO** |
