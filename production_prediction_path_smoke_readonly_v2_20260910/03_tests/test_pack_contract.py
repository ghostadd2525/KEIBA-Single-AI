#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "02_powershell" / "prediction_smoke_readonly.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
FLAGS = ROOT / "FLAGS.txt"
V1BAN = ROOT / "V1_DO_NOT_RUN.txt"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = PY.read_text(encoding="utf-8")
    ps = PS1.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    ban = V1BAN.read_text(encoding="utf-8")

    expect("readonly_db_existing" not in src, "no_db_race_fallback", failures)
    expect("existing_race_ids_from_db" not in src, "no_db_race_query", failures)
    expect("SELECT race_id" not in src, "no_select_race_id", failures)
    expect("SELECT COUNT(*) FROM predictions" in src, "count_only", failures)
    expect("Never call /v1/prediction-runs" in src, "never_post_doc", failures)
    expect("method=\"POST\"" not in src and "method='POST'" not in src, "no_post_method", failures)
    expect('method="GET"' in src, "get_only_request", failures)
    expect("127.0.0.1:8000" in src, "loopback_only", failures)
    expect("mode=ro" in src, "sqlite_ro", failures)
    expect("INSERT" not in src and "UPDATE " not in src and "DELETE " not in src, "no_sql_write", failures)
    expect("systemctl start" not in src, "no_systemd_start", failures)
    expect("systemctl restart" not in src, "no_systemd_restart", failures)
    expect("V1_DO_NOT_RUN=YES" in ps, "ps_v1_ban", failures)
    expect("HISTORICAL_DB_RACE_LIVE_INFERENCE_ALLOWED=NO" in ps, "ps_no_hist", failures)
    expect("DETAIL_GET_ONLY_FROM_CURRENT_LIST=YES" in ps, "ps_list_only", failures)
    expect("??" not in ps, "ps51_no_null_coalesce", failures)
    expect(" && " not in ps, "ps51_no_andand", failures)
    expect(" || " not in ps, "ps51_no_oror", failures)
    expect("CURRENT_PRODUCTION_PREDICTION_HTTP_OK=N_A_OPS_CLOSED" in flags, "flag_http_na", failures)
    expect("PUBLIC_PREDICTION_GATE_STATUS=EXPECTED_OPS_CLOSED" in flags, "flag_ops", failures)
    expect("OWNER_PACK_SAFE_RACE_SELECTION=YES" in flags, "flag_safe", failures)
    expect("PR23_MERGED=NO" in flags, "flag_pr23", failures)
    expect("DO NOT RUN v1" in ban, "v1_ban_file", failures)

    sys.path.insert(0, str(PY.parent))
    import prediction_smoke_readonly as smoke  # type: ignore

    empty, why = smoke.pick_detail_race_id([])
    expect(empty is None and why == "NO_CURRENT_RACE", "empty_list_skip", failures)

    good = {
        "race_id": "2026-07-19-04-11",
        "race_info": {"race_id": "2026-07-19-04-11", "date": "2026-07-19"},
        "evaluation": {"runners": [{"horse_number": 1, "win_prob": 0.2, "model_rank": 1, "mark": "honmei"}]},
    }
    picked, src_pick = smoke.pick_detail_race_id([good])
    expect(picked == "2026-07-19-04-11", "pick_from_current_list", failures)
    expect(src_pick.startswith("current_list"), "pick_source_list", failures)
    expect("db" not in src_pick, "pick_source_not_db", failures)

    no_runners = {"race_id": "2026-08-01-01-02", "evaluation": {"runners": []}}
    picked2, src2 = smoke.pick_detail_race_id([no_runners])
    expect(picked2 == "2026-08-01-01-02" and src2 == "current_list_first", "list_id_even_if_empty_runners", failures)

    stop, reason = smoke.list_should_stop({"timeout": True, "status": 0, "nbytes": 0, "elapsed_sec": 1}, 0)
    expect(stop and reason == "TIMEOUT", "stop_timeout", failures)
    stop, reason = smoke.list_should_stop({"timeout": False, "status": 500, "nbytes": 10, "elapsed_sec": 1}, 0)
    expect(stop and reason == "INTERNAL_ERROR", "stop_500", failures)
    stop, reason = smoke.list_should_stop({"timeout": False, "status": 200, "nbytes": 3000000, "elapsed_sec": 1}, 1)
    expect(stop and reason == "OVERSIZE", "stop_oversize", failures)
    stop, reason = smoke.list_should_stop({"timeout": False, "status": 200, "nbytes": 100, "elapsed_sec": 91}, 1)
    expect(stop and reason == "OVERLOAD_ELAPSED", "stop_elapsed", failures)
    stop, reason = smoke.list_should_stop({"timeout": False, "status": 200, "nbytes": 100, "elapsed_sec": 1}, 81)
    expect(stop and reason == "OVERLOAD_ITEM_COUNT", "stop_item_count", failures)
    stop, reason = smoke.list_should_stop({"timeout": False, "status": 200, "nbytes": 100, "elapsed_sec": 1}, 0)
    expect((not stop) and reason == "", "empty_200_not_stop", failures)

    expect(smoke.pick_detail_race_id.__doc__ and "Never DB" in smoke.pick_detail_race_id.__doc__, "doc_never_db", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
