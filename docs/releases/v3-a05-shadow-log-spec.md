# Version 3 — A-05 Shadow ログ仕様

**Date:** 2026-07-24  
**Schema:** `v3-a05-shadow-race/1.0`  
**Format:** JSONL（1 レース 1 行）  
**Logger:** `research/v3_lab/shadow/logger.py`

---

## 1. ファイル配置

```text
{log_dir}/a05_shadow_YYYYMMDD.jsonl
```

既定 `log_dir`: `research/v3_lab/baselines/a05_shadow/logs`

---

## 2. レコード必須フィールド

| Field | Type | 説明 |
|-------|------|------|
| `ts_utc` | string | 書込時刻 ISO8601 |
| `schema` | string | `v3-a05-shadow-race/1.0` |
| `phase` | string | S0 / S1 / S2 |
| `race_id` | string | レース ID |
| `control_pick` | string | Production Decision / Control |
| `control_policy` | string | `production_control` または `identity` |
| `shadow_pick` | string\|null | A-05 top-1 |
| `shadow_policy` | string\|null | `AP-V3-A05-favorite-safe-coverage` |
| `shadow_ok` | bool | Shadow 成功 |
| `shadow_error` | string\|null | fail-open 時のエラー |
| `a05_promote` | bool | journal.promote |
| `favsafe_blocked` | bool | |
| `favsafe_reason` | string | |
| `field_size` | number | |
| `top_margin` | number\|null | |
| `top_odds` | number\|null | |
| `winner_id` | string\|null | 事後結合 |
| `winner_rank` | number\|null | 事後結合 |
| `control_hit` | bool\|null | 事後 |
| `shadow_hit` | bool\|null | 事後 |
| `pick_changed` | bool\|null | |
| `control_odds` | number | 仮想 ROI 用 |
| `shadow_odds` | number\|null | 仮想 ROI 用 |
| `purchase_forbidden` | bool | 常に true |
| `purchase_executed` | bool | 常に false |
| `fail_open` | bool | |
| `elapsed_ms` | number | |

---

## 3. 禁止事項

- 購入指示・決済 ID をログに書かない
- 結果列を Shadow **入力**に使わない（winner は事後結合フィールドのみ）
- Production API レスポンスを上書きする用途に使わない

---

## 4. 例

```json
{
  "ts_utc": "2026-07-24T09:00:00+00:00",
  "schema": "v3-a05-shadow-race/1.0",
  "phase": "S0",
  "race_id": "2026-07-24-東京-11",
  "control_pick": "2021100001",
  "control_policy": "production_control",
  "shadow_pick": "2021100008",
  "shadow_policy": "AP-V3-A05-favorite-safe-coverage",
  "shadow_ok": true,
  "a05_promote": true,
  "favsafe_blocked": false,
  "purchase_forbidden": true,
  "purchase_executed": false
}
```
