#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "02_powershell" / "prediction_smoke_readonly.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
FLAGS = ROOT / "FLAGS.txt"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = PY.read_text(encoding="utf-8")
    ps = PS1.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    tree = ast.parse(src)

    posts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name.lower() in {"post", "urlopen"} and "POST" in ast.dump(node):
                posts.append(node)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "prediction-runs" in node.value:
                posts.append(node)

    expect("prediction-runs" not in src.split("Never")[0] or "Never call /v1/prediction-runs" in src, "docs_forbid_post", failures)
    expect("POST /v1/prediction-runs" in src or "Never call /v1/prediction-runs" in src, "never_post_doc", failures)
    expect("method=\"POST\"" not in src and "method='POST'" not in src, "no_post_method", failures)
    expect("Request(url, method=\"GET\"" in src or 'method="GET"' in src, "get_only_request", failures)
    expect("127.0.0.1:8000" in src, "loopback_only", failures)
    expect("mode=ro" in src, "sqlite_ro", failures)
    expect("PRAGMA query_only" in src, "query_only", failures)
    expect("INSERT" not in src and "UPDATE " not in src and "DELETE " not in src, "no_sql_write", failures)
    expect("migrate(" not in src, "no_migrate", failures)
    expect("systemctl start" not in src, "no_systemd_start", failures)
    expect("systemctl restart" not in src, "no_systemd_restart", failures)
    expect("systemctl stop" not in src, "no_systemd_stop", failures)
    expect('"systemctl", "show"' in src, "systemd_show", failures)
    expect('"systemctl", "status"' in src, "systemd_status", failures)
    expect('"journalctl"' in src, "journal_ro", failures)
    expect("conversation" not in src.lower() or "CONVERSATION_TOUCHED" in src, "no_conversation_write", failures)
    expect("result-automation" not in src, "no_ra_http", failures)
    expect("scp " not in ps.lower(), "ps_no_scp", failures)
    expect("??" not in ps, "ps51_no_null_coalesce", failures)
    expect(" && " not in ps, "ps51_no_andand", failures)
    expect(" || " not in ps, "ps51_no_oror", failures)
    expect("python3 -" in ps, "stdin_python", failures)
    expect("POST_ENDPOINT_CALLED=NO" in ps, "ps_no_post_flag", failures)
    expect("PRODUCTION_CHANGED=NO" in flags, "flags_prod_no", failures)
    expect("POST_ENDPOINT_CALLED=NO" in flags, "flags_post_no", failures)
    expect("FRONTEND_API_TARGET_CONFIRMED=YES" in flags, "frontend_confirmed", failures)

    sys.path.insert(0, str(PY.parent))
    import prediction_smoke_readonly as smoke  # type: ignore

    good = {
        "schema_version": "single-prediction-bundle/2.0",
        "race_id": "2026-07-19-04-11",
        "race_info": {"race_id": "2026-07-19-04-11", "date": "2026-07-19", "venue": "阪神", "race_no": 11},
        "evaluation": {
            "runners": [
                {"horse_number": 7, "win_prob": 0.22, "model_rank": 1, "mark": "honmei"},
                {"horse_number": 3, "win_prob": 0.15, "model_rank": 2, "mark": "taikou"},
            ]
        },
        "ai_confidence": {"score": 0.5},
        "explain": {"meta": {}},
        "betting_recommendations": {"items": []},
    }
    ok = smoke.validate_bundle(good, "2026-07-19-04-11", {"engine_source": "real_ai", "model_version": "v2"})
    expect(ok["BUNDLE_SCHEMA_VALID"] is True, "valid_bundle", failures)
    expect(ok["REAL_AI_CONFIRMED"] is True, "real_ai_yes", failures)
    expect(ok["FALLBACK_USED"] is False, "fallback_no", failures)
    expect(ok["RUNNER_COUNT"] == 2, "runner_count", failures)

    mock = dict(good)
    bad = smoke.validate_bundle(mock, "2026-07-19-04-11", {"engine_source": "mock_fallback", "fallback_reason": "platform_missing"})
    expect(bad["REAL_AI_CONFIRMED"] is False, "mock_not_real", failures)
    expect(bad["FALLBACK_USED"] is True, "fallback_yes", failures)

    dup = json.loads(json.dumps(good))
    dup["evaluation"]["runners"][1]["horse_number"] = 7
    d = smoke.validate_bundle(dup, "2026-07-19-04-11", {"engine_source": "real_ai"})
    expect(d["HORSE_NUMBER_UNIQUE"] is False, "dup_horse", failures)

    inv = json.loads(json.dumps(good))
    inv["evaluation"]["runners"][0]["win_prob"] = 0.10
    inv["evaluation"]["runners"][0]["model_rank"] = 1
    inv["evaluation"]["runners"][1]["win_prob"] = 0.20
    inv["evaluation"]["runners"][1]["model_rank"] = 2
    i = smoke.validate_bundle(inv, "2026-07-19-04-11", {"engine_source": "real_ai"})
    expect(i["MODEL_RANK_VALID"] is False, "rank_inversion", failures)

    picked, src = smoke.pick_existing_race_id([good], [])
    expect(picked == "2026-07-19-04-11", "pick_from_list", failures)
    expect(src.startswith("api_list"), "pick_source_list", failures)
    picked2, src2 = smoke.pick_existing_race_id([], ["2026-08-01-01-02"])
    expect(picked2 == "2026-08-01-01-02" and src2 == "readonly_db_existing", "pick_from_db", failures)
    picked3, src3 = smoke.pick_existing_race_id([], [])
    expect(picked3 is None and src3 == "none_found", "pick_none", failures)

    expect("20260910_hanshin" not in src and "invent" not in src.lower(), "no_invented_literal", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
