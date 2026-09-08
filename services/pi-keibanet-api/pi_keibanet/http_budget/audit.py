# -*- coding: utf-8 -*-
"""Classified Netkeiba / non-Netkeiba HTTP paths from real code only."""

# Common hook: every PI NetkeibaClient GET must reserve here.
BUDGETED_FUNCTIONS = (
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_jra_odds_json",
)

# Real callers that reach Netkeiba HTTP through a budgeted client.
BUDGETED_CALLERS = (
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_race_list_result",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_race_list",
    "pi_keibanet.netkeiba.client.NetkeibaClient.fetch_shutuba",
    "pi_keibanet.netkeiba.horse_history.fetch_horse_history",
    "pi_keibanet.race_refresh.discover_published_races",
    "pi_keibanet.race_refresh.process_race_pipeline",
    "pi_keibanet.race_refresh.run_refresh",
    "pi_keibanet.service.PiKeibaNetService",
    "pi_keibanet.c4_calendar.runner.run_c4_shadow",
    "pi_keibanet.w2_haron.runner.run_w2_shadow",
    "pi_keibanet.w3_maiden.acquisition.run_w3c_acquire",
    "pi_keibanet.w4_horse.acquisition.run_w4cd_acquire",
    "pi_keibanet.w5_maiden_history.acquisition.run_w5_acquire",
    "scripts/c4_calendar_shadow_run.py:main",
    "scripts/w2_haron_shadow_run.py:main",
    "scripts/w3_maiden_page_c_acquire_run.py:main",
    "scripts/w4_horse_d1d2_acquire_run.py:main",
    "scripts/w5_maiden_history_acquire_run.py:main",
    "scripts/run_pipeline.py",
    "scripts/run_day_e2e.py",
    "scripts/diagnose_20260725.py",
    "scripts/probe_shutuba.py",
    "scripts/probe_netkeiba.py",
    "win5-ai app.ops.netkeiba_results.NetkeibaHttp.fetch",
    "win5-ai app.research.collector.netkeiba_client.ResearchNetkeibaClient.fetch",
)

# Production-reachable Netkeiba HTTP that is wired to Global budget.
WIN5_NETKEIBA_BUDGETED = (
    "services/win5-ai/app/ops/netkeiba_results.py:NetkeibaHttp.fetch",
    "services/win5-ai/app/research/collector/netkeiba_client.py:ResearchNetkeibaClient.fetch",
)

# Localhost / internal API only — not Netkeiba, not Global budget.
INTERNAL_API_ONLY = (
    "services/win5-ai/app/ops/netkeiba_results.py:fetch_pi_race_catalog",
    "services/win5-ai/app/ops/netkeiba_results.py:fetch_pi_prediction_bundle",
    "services/win5-ai/app/research/collector/pi_client.py",
    "services/win5-ai/app/research/collector/__init__.py",
    "services/win5-ai/app/data/collect/keibanet/client.py",
    "services/win5-ai/app/data/sources/api_source.py",
    "services/pi-keibanet-api/scripts/prod_smoke.py",
)

# Not Netkeiba. Do not mix into UNBUDGETED_NETKEIBA_PATHS.
NON_NETKEIBA_HTTP = (
    "services/win5-ai/app/conversation/v4/ollama_client.py",
)

# Direct Netkeiba urlopen scripts — Production-refused unless allowlisted + budgeted.
DIRECT_NETKEIBA_PROBES = (
    "services/pi-keibanet-api/scripts/probe_netkeiba_api.py",
    "services/pi-keibanet-api/scripts/probe_full_list.py",
    "services/pi-keibanet-api/scripts/verify_sub_list.py",
)

# Active Production-reachable Netkeiba HTTP that is not reserved. Must stay empty.
UNBUDGETED_NETKEIBA_PATHS: tuple[str, ...] = ()

# Legacy name kept so older tests fail closed if they still import it.
UNBUDGETED_HTTP_PATHS = UNBUDGETED_NETKEIBA_PATHS
