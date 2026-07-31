# Phase I5 — Rollback Validation

**Date:** 2026-07-29

---

## Production と同手順

| Step | Action | Rehearsal Result |
|---|---|---|
| 1 | Flag ON で Single path 使用 | PASS（harness） |
| 2 | `single_ai_detail: false`（Rollback） | PASS — Single HTTP 停止 |
| 3 | 詳細は Prediction 継続 | PASS |
| 4 | 一覧 / Race List Cache | **無操作・非変更** PASS |

## Failure-path rollback（Flag は ON のまま）

| Trigger | Expected | Result |
|---|---|---|
| Timeout / Abort | Prediction fallback | **PASS** |
| HTTP 5xx / error body | Prediction fallback | **PASS** |

## Hard rules verified

- 一覧に Single を繋がない
- Cache キー操作なし
- committed `beta.json` は **false のまま**（Flag left ON = false）

## Conclusion

Rollback 手順は **即時有効**。Cutover 後の第一対応は Flag OFF。
