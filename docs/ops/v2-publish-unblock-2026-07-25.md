# Step1–2 Publish Unblock — 2026-07-25

**Date:** 2026-07-24  
**Scope:** V2 publish path only（A-05 / V3 / V4 未着手）  
**Host:** EC2 `ubuntu@13.231.5.5`

## Root cause

| Layer | Finding |
|-------|---------|
| Catalog `/v1/races` | 36 races（2歳新馬含む）OK |
| Features CSV (prod) | **9 races only**（特別戦） |
| Shadow CSV | **36 races** already generated 2026-07-24 13:29 · **not switched** |
| Prediction | `market_feature_missing` → UI「予想未公開」 |

## Action taken

1. `compare_daily_features.py` → **FAIL**（ガード特別戦の頭数減少・win5_leg 差分）  
   → **フル Shadow 切替は実施せず**（Addendum G1）
2. **欠落 27 race のみ** Shadow → Production CSV にマージ（ガード9レースは baseline 維持）
3. Backup: `demo_runners_pace_market_features.csv.bak.20260724205804`
4. Spot check: `2026-07-25-01-02` 等 `prediction_available=true`
5. BFF `/api/race-cards?date=2026-07-25` → **36 ready**

## Residual risk

- ガード特別戦は旧 headcount のまま（Shadow は現行 shutuba で減少）
- 後日、最終確定後にガード整合の再 Refresh が必要
- Timer は当日日付向き · 開催日前日は `--date` 明示 Refresh が必要

## Next

- Step3: クラス別 Hit / fallback 計測（着順確定後）
- Step4: A-05 Integration（未着手）
