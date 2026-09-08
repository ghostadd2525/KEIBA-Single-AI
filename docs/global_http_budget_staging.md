# Global HTTP budget (staging, PR-C1)

Production apply is out of scope. `PRODUCTION_APPLY_READY=NO`.
`W3W5_LIVE_HTTP` remains default `0` and always wins over budget mode.
Default budget mode is `off` so a code-only deploy does not stop existing P1.

## Rollout mode

| Mode | HTTP | State missing / corrupt |
|---|---|---|
| `off` (default, invalid values too) | Existing P1/C4/W2/W4 behavior. Research is not extra-enabled. | Do not stop P1 |
| `observe` | Unchanged. Reserve judgment is audited with `consumed=0`. | Do not stop HTTP |
| `enforce` | Budget forced when state/schema/config are valid | HTTP 0 |

`GLOBAL_HTTP_BUDGET_ENABLED=0` forces `off`.
Switching Production to `enforce` is a separate Owner approval.

## Short-window rate limit

Daily UTC quota is unchanged. Extra burst control is a rolling UTC window:

- `GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC` (0 = unset, no extra cap)
- `GLOBAL_HTTP_BUDGET_SHORT_LIMIT` (cross-component)
- `GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST` (per host)

Production numbers stay 0 / unset. Staging tests only use small values.
Rolling `reserved_at` comparison blocks UTC-midnight double burst.
P1/C4 and `win5_results` reserved slices are applied inside the short window
the same way as the daily remainder rule.

## Shared hook

`NetkeibaClient.fetch` / `fetch_jra_odds_json` call `reserve_for_request`
immediately before the opener. Component is set by the real runner:

| Runner | component |
|---|---|
| P1 race refresh / service | `p1` |
| C4 `run_c4_shadow` | `c4` |
| W2 `run_w2_shadow` | `w2` |
| W3-C `run_w3c_acquire` | `w3c` |
| W4 `run_w4cd_acquire` | `w4` |
| W5 `run_w5_acquire` | `w5` |
| Win5 Result Sync `NetkeibaHttp.fetch` | `win5_results` |
| Win5 research `ResearchNetkeibaClient.fetch` | `win5_research` |

Budget deny on C4/W2/W3-C/W4/W5 sets `stopped_global_budget` and exit `5`.
Fake `w4_global_budget_deny_probe.py` is removed.

## Win5 classification

| Path | Class |
|---|---|
| `app/ops/netkeiba_results.py` `NetkeibaHttp` | Netkeiba HTTP → `win5_results` |
| `app/research/collector/netkeiba_client.py` | Netkeiba HTTP → `win5_research` |
| `fetch_pi_race_catalog` / `fetch_pi_prediction_bundle` | localhost PI, not Netkeiba |
| `research/collector/pi_client.py` | internal PI API |
| `data/collect/keibanet/client.py` | internal KeibaNet/PI |
| `data/sources/api_source.py` | internal data API |
| `conversation/v4/ollama_client.py` | not Netkeiba |

## Direct probes

`probe_netkeiba_api.py`, `probe_full_list.py`, `verify_sub_list.py`:
refused in Production (`EXPECT_PRODUCTION=1` or `PI_DATA_ROOT` under
`/opt/expect-ai`) and unless `GLOBAL_HTTP_BUDGET_ALLOW_PROBES=1`.
When allowed they go through `NetkeibaClient`.

`prod_smoke.py` is localhost PI only and is not a Netkeiba path.
