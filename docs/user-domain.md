# User Domain — Phase U-1

AI（Prediction Core / Conversation）から独立した User Domain。

## テーブル（`004_user_domain.sql`）

| テーブル | 用途 |
|---------|------|
| `users` | ログイン ID / パスワード / ステータス |
| `profiles` | 表示名・アバター・設定 |
| `user_sessions` | セッション・トークンハッシュ |
| `favorites` | お気に入りレース（最大3件） |
| `prediction_history` | ユーザーが閲覧した予測 |
| `chat_sessions` / `chat_messages` | チャット履歴 |
| `notifications` | 通知 |
| `subscriptions` | サブスクリプション |

**Prediction Core は `user_id` を直接書き込まない。**  
予測閲覧履歴は User Service API 層（`GET /v1/predictions/:id` + Bearer）で記録。

## REST API（Python `services/win5-ai`）

| Method | Path | 説明 |
|--------|------|------|
| GET | `/v1/users/me` | 自分のプロフィール |
| PATCH | `/v1/users/me` | プロフィール更新 |
| GET | `/v1/favorites` | お気に入り一覧 |
| POST | `/v1/favorites` | お気に入り追加/削除 |
| GET | `/v1/history` | 予測閲覧履歴 |
| GET | `/v1/chat` | チャットセッション/メッセージ |
| POST | `/v1/auth/login` | ログイン |
| POST | `/v1/auth/logout` | ログアウト |
| POST | `/v1/auth/setup` | 初回セットアップ |
| GET | `/v1/admin/users` | 管理用ユーザー一覧 |

認証: `Authorization: Bearer stub.<payload>.<exp>`（BFF 互換）

## モジュール構成

```
app/user/
  auth.py       — トークン検証・ログイン
  password.py   — sha256 ハッシュ（BFF 互換）
  repository.py — 全 Repository
  service.py    — UserService
```

## テスト

```bash
cd services/win5-ai
python -m unittest tests.ops.test_user_domain -v
```

## BFF プロキシ

- `functions/api/users/me.js`
- `functions/api/v1/favorites.js`
- `functions/api/v1/history.js`
- `functions/api/v1/chat.js`

## 管理画面

`mypage.html` — プロフィール・履歴件数・チャットセッション数・Coverage パネル
