# Global HTTP budget (staging)

Production apply is out of scope. Defaults do not authorize live Netkeiba HTTP.
`W3W5_LIVE_HTTP` remains default `0`. This document names only functions that
exist on the current git tree, plus snapshot-only callers that are **not**
imported here.

## Shared hook

| Function | File | Transport |
|---|---|---|
| `NetkeibaClient.fetch` | `pi_keibanet/netkeiba/client.py` | `self._opener` default `urllib.request.urlopen` |
| `NetkeibaClient.fetch_jra_odds_json` | same | same opener (own Request) |

Reserve runs immediately before the opener. Interval sleep uses
`time.monotonic()`. The UTC day window uses wall-clock UTC.

Timeout: `PI_NETKEIBA_TIMEOUT` default 25s.
Interval: `PI_NETKEIBA_MIN_INTERVAL_SEC` default 1.0s.

## Call hierarchy (git tree)

### P1 / race refresh

- Timer (git unit only): `infra/aws/systemd/expect-pi-race-refresh.timer` every 15 min, JST 08–20
- `race_refresh.run_refresh` → `NetkeibaClient(component="p1")`
- `discover_published_races` → `fetch_race_list` (1–2 GET: sub + sp)
- per published race → `fetch_shutuba` (PC then SP fallback)
- `process_race_pipeline` → `fetch_horse_history` (ajax then db.sp, 1–2 GET)
- Per-run HTTP is data-dependent (no global cap before this PR)
- Existing P1 lock is **not** a Global budget

### P1 API / service

- `PiKeibaNetService` → `fetch_race_list`, `fetch_shutuba`, `fetch_jra_odds_json`
- `horse_history()` → `fetch_horse_history` with worker `min_interval_sec=0.15`

### C4 PAGE-A1

- On this tree: `c4_calendar/config.py` (`max_requests_per_run=4`) + `page_a1_store.persist_page_a1_after_fetch`
- HTTP would be `NetkeibaClient.fetch_race_list_result` (1–2 GET)
- `c4_calendar/runner.py` / `run_c4_shadow` is **not on main** (snapshot only)
- C4 `HEALTHY` only remains a W3-A supply gate (P0)

### W2

- On this tree: `w2_haron/{config,p1_lock,source_health}.py`
- `RESULT_URL`, `max_races_per_run=5`, P1 lock `p1_allows_w2`
- Runner is **not on main**

### W3-C

- Timer (git unit only): `expect-w3c-page-c-maiden.timer` `*:05/30`
- `scripts/w3_maiden_page_c_acquire_run.py:main` → `run_w3c_acquire`
- `net.fetch(PAGE_C_RESULT_URL)` = 1 GET / race
- Caps: max 2 races / 2 HTTP / run
- `W3W5_LIVE_HTTP` default 0 disables fetch before any reserve
- Yields to P1 lock / W2 / C4 systemd busy (not a Global budget)

### W4

- **Not on this git tree.** Snapshot names only:
  - `pi_keibanet.w4_horse.acquisition.run_w4cd_acquire`
  - `NetkeibaClient.fetch(D1_URL|D2_URL)`
  - `D1_URL = https://db.netkeiba.com/horse/{horse_id}/`
  - `D2_URL = https://db.netkeiba.com/horse/ped/{horse_id}/`
  - max 2 horses / 4 HTTP / run
- Staging probe: `scripts/w4_global_budget_deny_probe.py` (component `w4`)

### W5

- Timer (git unit only): `expect-w5-maiden-history.timer` `:10` and `:40`
- `scripts/w5_maiden_history_acquire_run.py:main` → `run_w5_acquire`
- `fetch_horse_history(net, hid)` → 1–2 GET
- Caps: max 2 horses / 4 HTTP / run, max 3 attempts, retry allowlist (P0)
- `W3W5_LIVE_HTTP` default 0 disables fetch

### Scripts that use NetkeibaClient (budgeted if they call fetch)

- `scripts/run_pipeline.py`, `run_day_e2e.py`, `diagnose_20260725.py`,
  `probe_shutuba.py`, `probe_netkeiba.py`

## Unbudgeted HTTP paths (not hidden)

Direct `urllib.request.urlopen` (not `NetkeibaClient.fetch`):

- `scripts/probe_netkeiba_api.py`
- `scripts/probe_full_list.py`
- `scripts/verify_sub_list.py`
- `scripts/prod_smoke.py` (local API, not netkeiba)

Other trees:

- `services/win5-ai/app/ops/netkeiba_results.py`
- `services/win5-ai/app/research/collector/netkeiba_client.py`
- `services/win5-ai/app/research/collector/pi_client.py`
- `services/win5-ai/app/data/collect/keibanet/client.py`
- `services/win5-ai/app/conversation/v4/ollama_client.py` (not netkeiba)

No `requests` / `httpx` in `pi_keibanet`.

## State / lock

- SQLite file on local disk (`GLOBAL_HTTP_BUDGET_STATE_PATH`)
- `BEGIN IMMEDIATE` + `PRAGMA busy_timeout` + WAL + `synchronous=FULL`
- Crash after reserve: row stays `consumed=1` (`result=pending`)
- If HTTP is never sent after reserve: `result=reserved_no_http`, still consumed
- Missing state: fail-closed (research and P1/C4)
- Corrupt / schema mismatch / busy timeout: fail-closed
- Ledger prune: UTC windows older than `LEDGER_RETENTION_DAYS` (default 3)

## Priority

Reserved capacity for P1/C4. W2/W3-C/W4/W5/unknown may use only the remainder.
Priority numbers do not pre-book future slots.

Defaults: total 0, reserved 0, every component limit 0, bootstrap 0.
Staging tests set small positive numbers only.
