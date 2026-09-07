# Version109 Phase C6 — Rollback Report

**Date:** 2026-07-29  
**Check:** `rollback` · **PASS**

---

## 手順（実証）

```text
1. W_CONSUMER_SINGLE/PRESENTATION/TICKET = ON
2. build_single_response(include_tickets/presentation=True)
3. 全 Consumer Flag = OFF
4. build_single_response(force=True)  # harness; 入口は同一
```

---

## 結果

| 項目 | 結果 |
|---|---|
| 即時復帰 | **Yes**（再デプロイ不要・Flag のみ） |
| mode | **LEGACY** |
| presentation | null |
| ticket | null |
| Core fingerprint | 切替前後で **一致** |
| policy_id | Staging 前後で **安定** |

---

## 結論

**Rollback = Flag OFF。** Core / Contract / Prediction を戻す操作は不要。
