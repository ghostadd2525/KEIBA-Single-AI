# Version109 Phase C1 — Decision Registry + Consumer API Skeleton

**Date:** 2026-07-28  
**Status:** Implemented (library) · Flag default OFF · HTTP 未配線  
**Parents:** V109 Migration C1 · ADR-011 · PLATFORM-V1-CONTRACT

---

## 実装

| モジュール | Path | 役割 |
|---|---|---|
| Core client | `app/consumer/core_client.py` | Core read-only（deep copy） |
| Core payload | `app/consumer/core_payload.py` | fingerprint / schema v1 |
| Decision Registry | `app/consumer/registry.py` | Policy のみ（Prediction 非保持） |
| Single Consumer API | `app/consumer/single_api.py` | `consumer-api/single/v1` 骨格 |
| Flags | `app/consumer/flags.py` | `W_CONSUMER_SINGLE_ENABLED` 既定 OFF |
| Tests | `tests/consumer/test_c1_registry_consumer_api.py` | 契約・非改変 |

---

## 契約遵守

| 規則 | 結果 |
|---|---|
| Core Payload 変更しない | PASS（deep copy + テスト） |
| Registry が Core を書き換えない | PASS |
| Registry が Prediction を保持しない | PASS（resolve は world/nm のみ） |
| Consumer が Core を read-only 利用 | PASS |
| Ticket / Presentation | null（C2/C3） |

---

## 利用例

```python
from app.consumer import InMemoryCoreClient, build_single_response

client = InMemoryCoreClient()
client.put_for_test("r1", core_payload_dict)
resp = build_single_response(client, "r1", force=True)  # or enable flag
# resp["registry"]["policy_id"]
```

---

## Next

- C2 Presentation  
- C3 Ticket Policy  
- PROMOTE Gate（別）  
- HTTP ルートは Product 配線の別 Gate  
