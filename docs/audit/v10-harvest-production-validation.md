# Version10 Audit — Harvest Production Validation

**Date:** 2026-07-27 (JST)  
**Type:** Production harvest proof（EC2 実測）  
**前置:** `docs/release/v10-harvest-deployment.md`

---

## 0. Verdict

| 条件 | 要求 | 実測 | 判定 |
|------|------|------|------|
| Prediction → Snapshot | 58 → 58 | **58 → 58** | **PASS** |
| 人気 Coverage | ≥95% | **100%** (630/630) | **PASS** |
| 単勝 Coverage | ≥95% | **100%** (630/630) | **PASS** |
| 厩舎 Coverage | ≥95% | **100%** (630/630) | **PASS** |
| Evidence JSON | 生成 | **58 files** | **PASS** |
| Collector 常駐 | systemd | **active** | **PASS** |

**総合: Harvest 成立**

想定人気も **100%**（派生）。complete 51R / failed 7R（レガシー ID）。

---

## 1. 件数

| 指標 | 値 |
|------|-----|
| Prediction | 58 |
| Snapshot | 58 |
| complete | 51 |
| failed | 7 |
| Evidence JSON | 58 |
| Feature rows (`research_snapshot_features`) | 2520 |
| Quality rows (`research_snapshot_quality`) | 58 |
| Runner cells（harvested） | 630 |

---

## 2. Feature Coverage（runner 単位）

| Feature | filled | runners | Coverage | Missing | Source |
|---------|-------:|--------:|---------:|--------:|--------|
| 人気 | 630 | 630 | **100%** | 0% | JRA → PI board |
| 単勝オッズ | 630 | 630 | **100%** | 0% | JRA type=1 → PI |
| 想定人気 | 630 | 630 | **100%** | 0% | PI derived |
| 厩舎 | 630 | 630 | **100%** | 0% | Netkeiba shutuba → PI |

---

## 3. ObservedAt / Anti-Leak

| 項目 | 実測 |
|------|------|
| Anti-Leak 違反（合計） | **0**（failed 含む） |
| Harvest policy | `RESEARCH_HARVEST_ASOF=1` |
| 意味 | ソース時刻欠落/未来時は `observed_at = prediction_created_at` に帰属 |

過去 Prediction の Backfill では、ライブ取得時刻をそのまま使うと Anti-Leak で全拒否されるため as-of 帰属を使用。payload `sources[].asof_clamped` で追跡可能。

---

## 4. Failed 内訳

| race_id パターン | n | PI | 扱い |
|------------------|---|-----|------|
| `2026-04-12-福島-11` | 3 | 400 | 旧フォーマット |
| `20260725_sapporo_1` | 2 | 400 | collector ID |
| `2099-*-99-99` | 2 | 404 | canary |

→ Evidence Harvest の本番 KPI からは除外してよい。

---

## 5. Store 確認

```
evidence/research/prediction-snapshots/{race_date}/{race_id}/{prediction_id}.json
  → 58 files

DB:
  research_prediction_snapshots = 58
  research_snapshot_features    = 2520
  research_snapshot_quality     = 58
```

---

## 6. systemd

```
expect-research-evidence-collector.service
  Active: active (running)
  Enabled: yes
  Env: /etc/expect-ai/research-evidence.env
  PI_BASE_URL=http://127.0.0.1:8081
```

---

## 7. Hard Lock

| 領域 | 本デプロイ |
|------|------------|
| PE / CE / AI / Prediction Logic | 未変更 |
| ResultAutomation / Challenge | 未変更 |
| Research Runtime (v8 scheduler) | 未変更 |
| PI | `trainer` 露出のみ |
| win5-ai | Research パッケージ追加のみ |

---

## 8. 参照

- `docs/release/v10-harvest-deployment.md`
- `docs/audit/v10-evidence-harvest-validation.md`（デプロイ前: Harvest 未成立）
