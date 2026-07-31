# Version 3 — A-05 Shadow 実行手順（Runbook）

**Date:** 2026-07-24  
**Status:** 実装済み · **評価窓は開始しない（本 Round 停止）**  
**Parent:** [`v3-a05-shadow-implementation.md`](./v3-a05-shadow-implementation.md)

---

## 1. 前提

- Lab パッケージ `research/v3_lab` のみ
- `F_V3_A05_ADM_FAVSAFE_ENABLED` 既定 OFF のまま
- Production / Prediction API / 購入に接続しない
- PRR HOLD · 評価窓開始は別承認

---

## 2. 設定（Rollout Plan 準拠）

| 変数 | S0 Dry-run | S1 Hard Gate | 備考 |
|------|------------|--------------|------|
| `WIN5_V3_A05_SHADOW_RUNTIME_ENABLED` | `true`（承認後） | `true` | 既定は未設定=false |
| `WIN5_V3_A05_SHADOW_PHASE` | `S0` | `S1` | |
| `WIN5_V3_A05_SHADOW_LOG_DIR` | 任意 | 任意 | 既定 `baselines/a05_shadow/logs` |

コード上の既定:

```python
from v3_lab.shadow import load_shadow_settings
s = load_shadow_settings()  # shadow_runtime_enabled=False, phase=S0
```

---

## 3. 単レース（API）

```python
from v3_lab.shadow import run_shadow_race, load_shadow_settings, ShadowLogger

settings = load_shadow_settings(shadow_runtime_enabled=True, phase="S0")
rec = run_shadow_race(
    context={"race_id": "...", "field_size": 16},
    runners=[...],                 # 本番と同一入力
    production_pick="HORSE_ID",    # Production Decision（変更しない）
    winner_id=None,                # 事後結合可
    winner_rank=None,
    settings=settings,
)
ShadowLogger(settings).write(rec)  # ログのみ · 購入なし
```

fail-open: Shadow 例外時も `control_pick` は保持され、例外は `shadow_error` に入る。

---

## 4. バッチ（Lab corpus）

```python
from v3_lab.shadow import load_shadow_settings
from v3_lab.shadow.harness import run_shadow_batch, write_shadow_artifacts

settings = load_shadow_settings(shadow_runtime_enabled=True, phase="S0")
result = run_shadow_batch(corpus, settings=settings, production_picks={...})
write_shadow_artifacts(result)
```

成果物: `research/v3_lab/baselines/a05_shadow/`

---

## 5. Acceptance 計測

```python
from v3_lab.shadow import aggregate_shadow_metrics, evaluate_acceptance

m = aggregate_shadow_metrics(records, settings=settings)
acc = evaluate_acceptance(m, settings=settings, window_days=14)
# acc["decision"] == PASS/FAIL （窓データが揃ってから）
```

---

## 6. 停止 / Rollback（運用）

| 操作 | 方法 |
|------|------|
| Shadow 停止 | `WIN5_V3_A05_SHADOW_RUNTIME_ENABLED` を外す / false |
| 本番 Flag | 触らない（既定 OFF） |
| 購入 | 元々実行していない |

---

## 7. 本 Round でやらないこと

- 実開催 Shadow 評価の開始
- Flag 既定 ON
- Production 配線
- Phase 3
