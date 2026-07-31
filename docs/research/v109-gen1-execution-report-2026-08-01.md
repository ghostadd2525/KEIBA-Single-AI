# GEN1 Execution Report — race_refresh 2026-08-01

**Executed at:** 2026-07-29 15:35 JST  
**Host:** `ubuntu@13.231.5.5` (`ip-172-31-40-147`)  
**Command:**

```bash
cd /home/ubuntu/KEIBA-Single-AI/services/pi-keibanet-api
export PI_KEIBANET_MIN_INTERVAL_SEC=1.0 \
  PI_AI_PLATFORM_ROOT=/opt/expect-ai/platform \
  PI_DATA_ROOT=/opt/expect-ai/platform/data \
  PI_RACE_REFRESH_STATE_ROOT=/opt/expect-ai/platform/data/var/race_refresh
python3 scripts/prod_race_refresh.py --date 2026-08-01 --force
```

**Report JSON:** `/opt/expect-ai/platform/data/var/race_refresh/2026-08-01/logs/refresh_2026-07-29T153515.669736_0900.json`  
**Stdout log:** `/tmp/gen1-refresh-2026-08-01.log`

---

## Counts（実測）

| Metric | Value |
|---|---|
| 対象レース数（published / processed） | **13** |
| meetings | 3 |
| 成功件数（features_generated） | **0** |
| 失敗件数（feature_blocked / horse_number skip） | **13** |
| Prediction Ready（PI `prediction_available=true`） | **0** |
| Bundle Ready（BFF HTTP 200 PredictionBundle） | **0** |
| updated_count（runners 更新） | 13 |
| features_skipped_horse_number | 13 |
| error_count | 13 |
| feature_ready_race_ids | `[]` |

Target `2026-08-01-01-02` ∈ `feature_blocked_race_ids`.

---

## Error cause（実ログ）

全 13 レース共通:

```text
Race Refresh Incomplete
Horse Number Not Ready
Frame Number Not Ready
```

Target 例:

```text
Horse Number Not Ready: race_id=2026-08-01-01-02 missing_horse_number=3 fallback=0 missing_horse_id=0
Frame Number Not Ready: race_id=2026-08-01-01-02 missing_frame=3
```

結果:

```text
[race-refresh] Race Refresh Incomplete: blocked=13 ready=0
[race-refresh] Horse Number Not Ready: Feature CSV generation skipped
[race-refresh] features_generated=0
```

Features CSV 実体:

```text
/opt/expect-ai/platform/data/demo_daily_outputs/2026-08-01/demo_runners_pace_market_features.csv
rows=0  (header only)
has target race_id=False
```

PI probe（localhost:8081）:

```text
2026-08-01-01-02 available=False error=features_unavailable message=market_feature_missing
```

---

## Post-check: Prediction / Bundle Ready

| Check | Result |
|---|---|
| `GET https://expect-keiba.com/api/predictions/2026-08-01-01-02` | **HTTP 202** `PREDICTION_PENDING` |
| race-cards `2026-08-01` | 13 cards, all `prediction.status=missing` |
| UI detail | 「AI予想を生成しています」のまま（Pending 維持） |
| 通常 AI 予想表示への遷移 | **未達**（Ready Bundle 無し） |

---

## UI verification

URL: `https://expect-keiba.com/race?race_id=2026-08-01-01-02`

- 契約エラーカード: なし（UI4 正常）
- Pending 文言: 「AI予想を生成しています」
- Ready 描画（印・本命）: **なし**

---

## Conclusion

1. EC2 での `--force` refresh は **実行完了**。  
2. しかし **馬番・枠番未確定**のため integrity ゲートが全レースをブロックし、**Features 0 件**。  
3. よって Prediction Ready / Bundle Ready は **0**。UI も Pending のまま。  
4. 次の条件: netkeiba 出馬表で正式馬番・枠番が揃った後に再実行。

---

## Next action

```bash
# 馬番確定後に再実行
python3 scripts/prod_race_refresh.py --date 2026-08-01 --force
# 期待: features_generated > 0 / feature_ready に 2026-08-01-01-02
# 確認: curl PI + BFF → HTTP 200
```
