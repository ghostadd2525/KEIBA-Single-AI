# Version109 Phase C5.5 — API Example（Shadow）

**Date:** 2026-07-29  
**Mode:** Shadow only · Production HTTP 未配線  
**呼び出し:** `build_single_response`（`consumer-api/single/v1`）

---

## Logical Request

```json
{
  "endpoint_logical": "ConsumerSingleAPI / build_single_response",
  "request": {
    "race_id": "ux-r1",
    "options": {
      "include_tickets": true,
      "include_presentation": true,
      "locale": "ja"
    },
    "shadow": true,
    "flags": "W_CONSUMER_* default OFF; force=True for Shadow"
  }
}
```

## Python（Shadow）

```python
from app.consumer import InMemoryCoreClient, build_single_response

client = InMemoryCoreClient()
client.put_for_test("ux-r1", core_payload)  # read-only Core
resp = build_single_response(
    client,
    "ux-r1",
    force=True,                      # Shadow
    include_tickets=True,
    include_presentation=True,
    locale="ja",
)
```

## Response Top-Level Keys

```text
schema
mode
version
core_ref
core_payload
registry
policy_metadata
selectors
presentation
ticket
flags_snapshot
warnings
natural_explanation   # always null
decision_reason       # always null
single_response_schema
```

## Legacy 互換呼び出し

```python
resp = build_single_response(client, "ux-r1", force=True)
# presentation=None, ticket=None, mode=LEGACY
```

## 注記

- Production ルート / 公開 HTTP は **未配線**（C5.5 でも禁止）。  
- 本 Example はライブラリ Shadow 入口のみ。
