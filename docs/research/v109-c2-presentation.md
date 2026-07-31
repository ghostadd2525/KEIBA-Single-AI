# Version109 Phase C2 — Presentation Layer

**Date:** 2026-07-28  
**Status:** Implemented (library) · Flag default OFF · Shadow via `force` / `force_presentation`  
**Parents:** PLATFORM-V1-CONTRACT · C1 Consumer API · ADR-010 · V103 MS-6

---

## 責務（実装）

| 項目 | モジュール |
|---|---|
| Presentation DTO | `app/consumer/presentation/dto.py` |
| Presentation Mapper | `app/consumer/presentation/mapper.py` |
| Presentation Renderer | `app/consumer/presentation/renderer.py` |
| Localization Contract | `app/consumer/presentation/localization.py` |
| Integration | `app/consumer/single_api.py` + `tests/consumer/test_c2_presentation.py` |

表示順: `world → near_miss → affinity → explanation_confidence → exclusion → transition`

---

## 禁止（遵守）

| 禁止 | 結果 |
|---|---|
| Prediction 変更 | PASS（除外＋非改変テスト） |
| Policy 変更 | PASS（registry policy_id 不変） |
| Ticket 生成 | PASS（null / C3） |
| Natural Explanation 生成 | PASS（常に null） |
| Semantic 変更 | PASS（読取マッピングのみ） |

EC は `not_win_probability=true` + disclaimer（ADR-010）。

---

## Flag

| Flag | 既定 |
|---|---|
| `W_CONSUMER_PRESENTATION_ENABLED` | **OFF** |
| Shadow | `force_presentation=True` または Consumer `force=True` + `include_presentation=True` |

---

## Localization Contract

`localization_contract()` → `presentation-i18n/v1`  
locales: `ja` / `en`  
`natural_explanation: forbidden_in_c2`

---

## Next

C3 Ticket Policy  
