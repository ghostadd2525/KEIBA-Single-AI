# Phase OPS-1A — Admin Bypass

**Status:** Implemented  
**前提:** OPS-1 公開制御（`maintenance_mode` / `ops_mode`）を拡張。Prediction Core・OPS-Monitor・Result Automation は変更しない。

---

## 1. 目的

管理者アカウントは **公開モード（OPS Mode）に関係なく** API にアクセスできる。

| ロール | OPS Mode 制御 | 備考 |
|--------|---------------|------|
| **USER** | 対象（CLOSED 時 503） | 一般ユーザー |
| **ADMIN** | **常時 bypass** | 本フェーズ |
| **OPS** | bypass（予約） | 将来 |
| **DEVELOPER** | bypass（予約） | 将来 |

---

## 2. 認可フロー（順序厳守）

```
1. requireAuth          … 認証
2. resolveAuthorization … ロール解決・bypass 権限（公開制御より先）
3. evaluateOpsAccess    … PUBLIC / CLOSED
4. handler
```

権限判定が公開制御より先に実行されるため、CLOSED 中でも ADMIN は `role_bypass` で通過する。

---

## 3. Middleware

`functions/_middleware.js`

- exempt: `/api/health`, `/api/ops/monitor`, auth 系 → **OPS-Monitor 非影響**
- USER + CLOSED → `OPS_CLOSED` 503
- ADMIN（等）+ CLOSED → 許可 + 監査 `ops_admin_bypass`

Result Automation は Python/EC2 側のため本 Middleware の対象外（従来どおり独立）。

---

## 4. ロール付与

優先順位:

1. `public/data/users.json` の `role`
2. トークン内 `role`（stub、任意）
3. `beta.json` の `admin_user_ids` または env `EXPECT_ADMIN_USER_IDS`

例（users.json）:

```json
{
  "user_id": "admin",
  "role": "ADMIN",
  "status": "active",
  "password_hash": "..."
}
```

例（beta.json）:

```json
{
  "maintenance_mode": true,
  "ops_mode": "CLOSED",
  "admin_user_ids": ["admin"]
}
```

---

## 5. 動作確認

| シナリオ | 期待 |
|----------|------|
| CLOSED + USER + `/api/predictions` | 503 `OPS_CLOSED` |
| CLOSED + ADMIN + `/api/predictions` | 200（下流次第） |
| CLOSED + `/api/ops/monitor` | 200（exempt） |
| PUBLIC + USER | 従来どおり利用可 |

```bash
npm run test -- tests/contract/ops-1a-admin-bypass.test.mjs
# または
node --test tests/contract/ops-1a-admin-bypass.test.mjs
```

---

## 6. 関連ファイル

| パス | 役割 |
|------|------|
| `functions/_lib/roles.js` | Role / Privilege |
| `functions/_lib/opsMode.js` | PUBLIC/CLOSED + evaluateOpsAccess |
| `functions/_lib/authorization.js` | ロール解決 |
| `functions/_middleware.js` | フロー統合 |
| `tests/contract/ops-1a-admin-bypass.test.mjs` | 単体テスト |
