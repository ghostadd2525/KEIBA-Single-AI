# W-S0 — Feature Flags（未使用）

**Stage:** W-S0  
**Default:** Production-safe OFF / legacy

| Flag | Default | W-S0 behavior |
|---|---|---|
| `W_TRIGGER_SHADOW` | `false` | Dual-Eval **disabled**（S1+） |
| `W_TRIGGER_PATH` | `legacy` | Production path forced legacy via `production_path()` |
| `W_DEFAULT_CORE` | `true` | Legacy DEFAULT→core residual **retained**（S7 removes） |

Env overrides exist for tests; W-S0 eval forces legacy-safe values.

Module: `ai_platform/core/world/trigger_migration_flags.py`
