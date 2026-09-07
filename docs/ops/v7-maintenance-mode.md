# Version7 Maintenance Mode（Research Week）

**Status:** Active  
**Schedule (JST, server truth):** **日曜 21:00 → 土曜 00:00**  
**PE / CE / AI / ResultAutomation / Research / Challenge:** unchanged

---

## Maintenance Schedule

| | 変更前 | **変更後** |
|--|--------|------------|
| 開始 | 日曜 21:00 | 日曜 21:00（同じ） |
| 終了 | 金曜 00:00 | **土曜 00:00** |
| 一般公開 | 金 0:00 〜 日 21:00 | **土 0:00 〜 日 21:00** |

正本: `functions/_lib/maintenanceSchedule.js`

---

## 新しいタイムライン（JST）

```
Sun 21:00 ──── CLOSED（Research Week / USER メンテ）──── Sat 00:00
                                                      │
                                                      ▼
                                              PUBLIC（一般公開）
Sat 00:00 ──── PUBLIC ──── Sun 21:00
```

| 曜日 | 状態 |
|------|------|
| 日曜 0:00–20:59 | PUBLIC |
| 日曜 21:00– | CLOSED |
| 月〜金 | CLOSED |
| 土曜 0:00– | PUBLIC |

---

## ADMIN 確認結果

| 項目 | 結果 | 根拠 |
|------|------|------|
| ADMIN ログイン可能 | **PASS** | `/api/auth/login` exempt |
| JWT 維持 / 強制ログアウト対象外 | **PASS** | `isOpsBypassUser` + `canBypassOpsMode(ADMIN)`。クライアントは bypass 時に `forceLogout` しない |
| Maintenance 画面対象外 | **PASS** | bypass → `index.html` / 通常画面。`ops.html` は `data-skip-auto-maintenance` |
| `/ops` 利用可能 | **PASS** | ページ skip + ADMIN requireAuth |
| 管理 API 利用可能 | **PASS** | CLOSED でも `role_bypass`（例: `/api/ops/dashboard`）。`/api/ops/monitor`・`/api/admin/invitations` は exempt |

契約テスト: `V7 ADMIN vs USER during CLOSED` — PASS

---

## USER 確認結果

| 項目 | 結果 | 根拠 |
|------|------|------|
| 強制ログアウト | **PASS** | `auto-maintenance.js` → `forceClearAuthState` → `/login.html` |
| maintenance 画面 | **PASS** | 未認証の保護ページ → `maintenance.html` |
| USER API 503 | **PASS** | middleware `OPS_CLOSED`（`evaluateOpsAccess` allow=false） |

---

## ①〜② 判定フロー（要約）

- サーバー: `resolveOpsModeDetailed` → Research Week スケジュール
- USER + CLOSED → 503 / 強制 logout
- ADMIN + CLOSED → bypass（JWT 維持）

---

## 修正ファイル

- `functions/_lib/maintenanceSchedule.js` — 終了を **Sat 00:00**
- `functions/_lib/opsMode.js` — コメント
- `functions/api/ops/public-status.js` / `_middleware.js`
- `public/assets/auto-maintenance.js` — 文言・ADMIN 明示
- `public/maintenance.html` — 文言修復
- `public/ops.html` — `data-skip-auto-maintenance`
- `config/beta.json` / `public/config/beta.json` — メッセージ
- `tests/contract/ops-auto-maintenance.test.mjs`
- `scripts/ops/canary-v1.1-auto-maint.mjs`
- `docs/ops/v7-maintenance-mode.md`（本ファイル）

---

## 本番確認結果（ローカル）

```bash
node --test tests/contract/ops-auto-maintenance.test.mjs
node scripts/ops/canary-v1.1-auto-maint.mjs
```

| スイート | 期待 |
|----------|------|
| Schedule Sat 00:00 end | PASS |
| Fri = CLOSED / Sat = PUBLIC | PASS |
| ADMIN bypass / USER 503 | PASS |
| canary harness | PASS |

**Live 期待:** 土曜 0:00（JST）以降 `maintenance: false`。それまで USER はメンテ、ADMIN は通常運用可。
