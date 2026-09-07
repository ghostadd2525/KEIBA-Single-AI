# Version 1.1 Auto Maintenance 平日動作確認

- **環境**: http://127.0.0.1:8788
- **日時**: 2026-07-21 (月) JST
- **Flag**: 11_auto_maintenance = true
- **public-status**: HTTP 200 / ops_mode=CLOSED / 
eason=auto_calendar
- **総合判定**: **PASS**

## ① ADMIN — PASS

| 項目 | 遷移先 / Status | 判定 |
|------|-----------------|------|
| ログイン | /api/auth/login **200** | PASS |
| トップ | /（maintenance へ行かない） | PASS |
| Race | /race | PASS |
| Chat | /chat | PASS |
| Analysis | /analysis | PASS |
| Prediction API | **200** | PASS |
| Conversation API | **200**（OPS_CLOSED ではない） | PASS |

スクショ: screenshots/verify-admin-*.png

## ② 一時ID — PASS

| 項目 | 遷移先 / Status | 判定 |
|------|-----------------|------|
| invite/start | **200** | PASS |
| 一時ID → setup | /login → /setup | PASS |
| setup 完了後 | **/maintenance** | PASS |
| Race 直接 | /race → **/maintenance** | PASS |
| Prediction API | **503** OPS_CLOSED | PASS |
| Conversation API | **503** OPS_CLOSED | PASS |

スクショ: screenshots/verify-invite-*.png

## ③ USER — PASS

| 項目 | 遷移先 / Status | 判定 |
|------|-----------------|------|
| ログイン | **200** | PASS |
| ログイン後 | **/maintenance** | PASS |
| Race 直接 | /race → **/maintenance** | PASS |
| Prediction API | **503** OPS_CLOSED | PASS |
| Conversation API | **503** OPS_CLOSED | PASS |

スクショ: screenshots/verify-user-*.png

## ④ 手動優先 — PASS

| 設定 | public-status | Prediction | 判定 |
|------|---------------|------------|------|
| maintenance_mode=true | CLOSED / manual_maintenance_mode | **503** OPS_CLOSED | PASS |
| ops_mode=CLOSED | CLOSED / manual_ops_mode | **503** OPS_CLOSED | PASS |
| ops_mode=PUBLIC | PUBLIC / manual_ops_mode | **200** | PASS |
| 復元（auto） | CLOSED / uto_calendar | **503** | PASS |

詳細 JSON: manual-priority.json / pi-results.json
