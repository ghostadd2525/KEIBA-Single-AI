# Version109 Phase C5.5 — Response Example

**Date:** 2026-07-29  
**Fixture:** `ux-r1` · mode=`SHADOW` · locale=`ja`  
**Full JSON:** `docs/research/v109-c55-response-example.json`

---

## 利用者に見せるべき要約（UI 想定）

| 順 | 表示 | 値（本例） |
|---|---|---|
| 1 | ワールド | 未充足（残余） |
| 2 | ニアミス | ニアミス → 近接: 混戦（rank7） |
| 3 | 親和度 | rank7 0.81 …（表示専用） |
| 4 | 説明確信度 | 総合 0.91（勝率ではない） |
| 5 | 除外理由 | rank7: must_field_chaos / core: n_insufficient |
| 6 | 遷移 | legacy→unsatisfied |
| — | 券 | BUY · 単勝 A · stake 50（保守 1 点） |

`natural_explanation` / `decision_reason` / `ticket.reason` = **null**

---

## Policy / Ticket（抜粋）

```json
{
  "registry": {
    "policy_id": "policy_near_miss_rank7_conservative",
    "world_id": "unsatisfied",
    "residual_class": "NEAR_MISS",
    "near_world": "rank7_world"
  },
  "ticket": {
    "template_id": "tpl_near_miss_conservative_top1",
    "action": "BUY",
    "legs": [{"type": "win", "horse_id": "A", "stake": 50.0}],
    "reason": null
  }
}
```

---

## UX 読み方（一文）

「このレースは未充足だが rank7 に近いニアミス。説明はそこそこ揃っている。買い目は本命1点の保守。」

（上記の物語文は **Response に含まれない**。UI が構造化フィールドから組む想定。）
