# GEN1 — Recovery Plan

## Fix this race (Immediate)
```bash
# on EC2
systemctl status expect-pi-race-refresh.timer expect-pi-race-refresh.service
journalctl -u expect-pi-race-refresh.service -n 200 --no-pager

cd /home/ubuntu/KEIBA-Single-AI/services/pi-keibanet-api
python3 scripts/prod_race_refresh.py --date 2026-08-01 --force

# if features_skipped_horse_number > 0, inspect integrity report under
# $PI_RACE_REFRESH_STATE_ROOT/2026-08-01/

# verify
# PI: prediction_available == true (not features_unavailable)
# BFF: GET /api/predictions/2026-08-01-01-02 → HTTP 200
```

## Stabilize today (Secondary)
- Force refresh `--date 2026-07-29 --force`
- Inspect horse_number / features_skipped / errors in report JSON
- Treat RA FAILED as separate ops ticket
- Do not confuse Collector `prediction_ready` (STATIC_CORE) with Bundle Ready

## Do not
- Change Core / Consumer / Prediction engine / Contracts for this audit recovery
- Expect UI retry alone to create Ready
- Expect Result Automation to generate predictions