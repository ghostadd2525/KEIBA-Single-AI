# Version 3 — A-05 Shadow Implementation Report

**Date:** 2026-07-24  
**Status:** Implementation Complete · **Shadow 評価窓は未開始**  
**Design:** [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md) · PASS  
**PRR:** HOLD 継続  
**Production wiring:** **False**  
**`F_V3_A05_ADM_FAVSAFE_ENABLED` 既定:** **OFF（未変更）**

---

## 1. 目的

A-05 を Shadow モードで並列評価可能にする。  
本番 Decision / Purchase は変更しない。fail-open。ログ出力のみ。

---

## 2. Shadow 実装一覧

| コンポーネント | モジュール | 責務 |
|----------------|------------|------|
| Shadow Config | `research/v3_lab/shadow/config.py` | 独立 runtime 設定（既定 OFF）· Phase S0/S1/S2 |
| Shadow Runner | `research/v3_lab/shadow/runner.py` | Control 記録 + A-05 並列 · fail-open · Flag 復元 |
| Shadow Logger | `research/v3_lab/shadow/logger.py` | JSONL 追記 · 購入禁止フラグ強制 |
| Shadow Comparator | `research/v3_lab/shadow/comparator.py` | Control/Shadow Diff 分類 |
| Shadow Metrics | `research/v3_lab/shadow/metrics.py` | Hit/Purchase*/ROI*/churn/wr1 · Acceptance 計測 |
| Shadow Harness | `research/v3_lab/shadow/harness.py` | バッチ · 成果物出力 |
| Package | `research/v3_lab/shadow/__init__.py` | 公開 API |

\* Purchase / ROI は **仮想**（本番購入は実行しない）。

---

## 3. 変更ファイル一覧

| ファイル | 変更 |
|----------|------|
| `research/v3_lab/shadow/*` | **新規** Shadow 実装 |
| `research/v3_lab/tests/test_a05_shadow.py` | **新規** fail-open / 既定 OFF テスト |
| `docs/releases/v3-a05-shadow-implementation.md` | 本文書 |
| `docs/releases/v3-a05-shadow-runbook.md` | 実行手順 |
| `docs/releases/v3-a05-shadow-log-spec.md` | ログ仕様 |
| `docs/releases/v3-a05-shadow-comparator-report.md` | Comparator Report |

**未変更:**

- `flags.py` の `F_V3_A05_ADM_FAVSAFE_ENABLED` 既定（False）
- Prediction API / UI / Ops / Explainability
- 購入処理（本番）
- Production 配線

---

## 4. Feature Flag / 独立設定

| 設定 | 既定 | 役割 |
|------|------|------|
| `F_V3_A05_ADM_FAVSAFE_ENABLED` | **False** | 本番/Lab Admission Flag · **変更禁止** |
| `WIN5_V3_A05_SHADOW_RUNTIME_ENABLED` | **false** | Shadow harness 実行許可（独立） |
| `WIN5_V3_A05_SHADOW_PHASE` | `S0` | Rollout 相（S0/S1/S2） |
| `WIN5_V3_A05_SHADOW_LOG_DIR` | `baselines/a05_shadow/logs` | ログ出力先 |

Shadow Runner は評価中のみ in-process で A-05 を一時 ON し、**終了時に必ず `reset_flags_to_default()`** する。

---

## 5. アーキテクチャ対応

```text
Control pick (= production_pick または Lab identity)
        → 記録のみ（Purchase 非実行）

同一入力
        → Shadow Runner (A-05)
        → Prediction (Lab pipeline top-1)
        → Logger / Comparator / Metrics
        → 購入禁止 · fail-open
```

---

## 6. 停止条件の遵守

| 項目 | 状態 |
|------|------|
| Shadow 実装 | **完了** |
| Shadow 評価窓（S1） | **未開始** |
| Production 配線 | **なし** |
| Feature Flag 既定 ON | **なし** |
| Phase 3 | **未着手** |

---

## 7. 関連提出物

- [`v3-a05-shadow-runbook.md`](./v3-a05-shadow-runbook.md)
- [`v3-a05-shadow-log-spec.md`](./v3-a05-shadow-log-spec.md)
- [`v3-a05-shadow-comparator-report.md`](./v3-a05-shadow-comparator-report.md)
