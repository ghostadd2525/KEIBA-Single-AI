# -*- coding: utf-8 -*-
"""Audited Netkeiba HTTP paths on this git tree. Names are from real code only."""

# Common hook: every NetkeibaClient GET must reserve here.
BUDGETED_FUNCTIONS = (
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_jra_odds_json",
)

# Callers that reach HTTP only through NetkeibaClient (budgeted once wired).
BUDGETED_CALLERS = (
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_race_list_result",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_race_list",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_shutuba",
    "pi_keibanet.netkeiba.horse_history.fetch_horse_history",
    "pi_keibanet.race_refresh.discover_published_races",
    "pi_keibanet.race_refresh.process_race_pipeline",
    "pi_keibanet.race_refresh.run_refresh",
    "pi_keibanet.service.PiKeibaNetService",
    "pi_keibanet.w3_maiden.acquisition.run_w3c_acquire",
    "pi_keibanet.w5_maiden_history.acquisition.run_w5_acquire",
    "scripts/w3_maiden_page_c_acquire_run.py:main",
    "scripts/w5_maiden_history_acquire_run.py:main",
    "scripts/run_pipeline.py",
    "scripts/run_day_e2e.py",
    "scripts/diagnose_20260725.py",
    "scripts/probe_shutuba.py",
    "scripts/probe_netkeiba.py",
)

# Real urlopen / other HTTP that does NOT go through NetkeibaClient.fetch.
# Listed so they cannot be treated as PASS. This PR does not hide them.
UNBUDGETED_HTTP_PATHS = (
    "services/pi-keibanet-api/scripts/probe_netkeiba_api.py",
    "services/pi-keibanet-api/scripts/probe_full_list.py",
    "services/pi-keibanet-api/scripts/verify_sub_list.py",
    "services/pi-keibanet-api/scripts/prod_smoke.py",
    "services/win5-ai/app/ops/netkeiba_results.py",
    "services/win5-ai/app/research/collector/netkeiba_client.py",
    "services/win5-ai/app/research/collector/pi_client.py",
    "services/win5-ai/app/research/collector/__init__.py",
    "services/win5-ai/app/data/collect/keibanet/client.py",
    "services/win5-ai/app/data/sources/api_source.py",
    "services/win5-ai/app/conversation/v4/ollama_client.py",
)

# Present on Production snapshot only — not in this git tree. When added they
# must use NetkeibaClient.fetch (already budgeted). Do not invent wrappers.
SNAPSHOT_ONLY_CLIENT_CALLERS = (
    "pi_keibanet.c4_calendar.runner.run_c4_shadow → NetkeibaClient.fetch_race_list_result",
    "pi_keibanet.w2_haron.runner (not on main)",
    "pi_keibanet.w4_horse.acquisition.run_w4cd_acquire → NetkeibaClient.fetch(D1_URL|D2_URL)",
)
