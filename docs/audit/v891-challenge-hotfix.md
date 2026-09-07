# Version8.9.1 Challenge Hotfix Audit

**Date:** 2026-07-27  
**Scope:** Challenge / Progress / UserAuth / HTTP Error Handling / StatsRepository（`get_overall_aggregate`）  
**Out of scope (unchanged):** PE / CE / AI 推論 / Research / ResultAutomation / Boundary

---

## 原因

Challenge の集計本体（`ChallengeCompareService.ai_monthly`）は正常だった。

障害は `compare()` 末尾の `progress.ensure(user_id)` で発生:

1. BFF stub 認証（例: `admin-20260721`）は AI SQLite `users` に未ミラーでも通る
2. `user_progress.user_id` は `users(user_id)` への FOREIGN KEY
3. 未登録 user へ `INSERT INTO user_progress` → `sqlite3.IntegrityError: FOREIGN KEY constraint failed`
4. `BaseHTTPRequestHandler.do_GET` が例外を握っていない → **Empty reply**
5. Pages → Tunnel 経由で接続切断 → Cloudflare **`origin_bad_gateway`** → Browser 502

`ai_monthly("2026-07")` 単体は事前調査で成功（例: 51R / profit `-54380`）。

関連（独立）: `stats/summary?period=month` が欠落メソッド `StatsRepository.get_overall_aggregate` を呼び `AttributeError` → 同様に Empty reply。

---

## 修正内容

### P0

| # | 変更 | ファイル |
|---|------|----------|
| ① | stub 認証成功時、AI `users` (+ `profiles`) を最小 UPSERT | `app/user/auth.py`, `app/user/repository.py` (`ensure_stub_mirror`) |
| ② | `progress.ensure` は親 user を先に生成し、IntegrityError を外へ出さない | `app/user/repository.py` |
| ③ | `compare()` は progress 失敗時も default progress で集計を返す | `app/challenge/service.py` (`_safe_progress`) |
| ④ | GET 全体を try/except。例外時 HTTP 500 JSON（`code` / `message` / `trace_id`）。Empty reply 禁止 | `app/main.py` |

UPSERT 最小項目:

- `users`: `user_id`, `login_id`, stub sentinel `password_hash`, `status=active`, `created_at` / `updated_at`
- `profiles`: `display_name`, `preferences_json.role`（users に role 列が無いため）

### P1

| # | 変更 | ファイル |
|---|------|----------|
| ⑤ | `get_overall_aggregate` / `get_aggregates` を live `race_evaluations` から実装 | `app/stats/repository.py` |

---

## 影響範囲

**変更あり**

- `services/win5-ai/app/user/auth.py`
- `services/win5-ai/app/user/repository.py`
- `services/win5-ai/app/challenge/service.py`
- `services/win5-ai/app/main.py`（GET エラーハンドリングのみ）
- `services/win5-ai/app/stats/repository.py`（欠落メソッド追加）

**変更なし**

- Prediction Engine / Core Engine / AI 推論パイプライン
- Research Logic / ResultAutomation
- BFF Functions / Cloudflare 設定（今回の障害は AI 側）
- Boundary 契約

---

## 再発防止

1. **Auth ミラー:** stub 成功時に AI `users` を必ず用意（FK 前提を満たす）
2. **Progress 防御:** `ensure` は例外を握りつぶし default を返す
3. **Challenge 分離:** 集計成功と progress 付与を分離（progress は付帯）
4. **Empty reply 禁止:** GET トップレベルで 500 JSON + `trace_id`（運用追跡可能）
5. **Stats API:** 参照メソッドは Repository に実体を置く（AttributeError 禁止）

推奨フォロー（本リリース外）:

- POST/PATCH も同様のトップレベル try/except
- BFF 側で AI Empty reply 時は必ず `AI_UNAVAILABLE` を返すことの回帰テスト

---

## 検証結果

### EC2 AI（`127.0.0.1:8000`）— 2026-07-27

対象ユーザー: admin stub / general stub / 新規 stub / 既存 user（`ra-v7-canary-user`）

| Endpoint | admin | general | new | existing |
|----------|-------|---------|-----|----------|
| `GET /v1/challenge/monthly?month=2026-07` | 200 | 200 | 200 | 200 |
| `GET /v1/user/progress` | 200 | 200 | 200 | 200 |
| `GET /v1/user-race-results` | 200 | 200 | 200 | 200 |
| `GET /v1/history` | 200 | 200 | 200 | 200 |
| `GET /v1/favorites` | 200 | 200 | 200 | 200 |
| `GET /v1/stats/summary?period=month` | 200 | 200 | 200 | 200 |

ユニット確認:

- 全ケースで `users` 行作成済み
- `compare` の `ai_profit=-54380`（集計継続）
- `progress` キー付与成功

### 本番 BFF（`https://expect-keiba.com`）— 2026-07-27

ADMIN stub Bearer で実測:

| Endpoint | 結果 |
|----------|------|
| `GET /api/v1/challenge/monthly?month=2026-07` | **200** `ok=true`（611ms） |
| `GET /api/v1/user/progress` | **200** |
| `GET /api/v1/history` | **200** |
| `GET /api/v1/favorites` | **200** |
| `GET /api/v1/stats/summary?period=month` | **200** |

Cloudflare `origin_bad_gateway` は解消。

---

## 判定

**Version8.9.1 Hotfix — PASS（AI 直検証）**

Challenge Empty reply / FK 障害は解消。PE/CE/AI推論/Research/RA には未接触。
