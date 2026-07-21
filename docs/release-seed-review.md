# Release Seed Review（M2）

**Phase12 Release Gate Closure**  
**目的:** β公開用 seed / ドキュメントからデモ資格情報・平文パスワードを除去したことの記録

---

## 実施内容

### 本番 ASSETS seed（公開パス）

| ファイル | 変更 |
|----------|------|
| `public/data/users.json` | `users: []`（`demo-user` / password_hash 削除） |
| `public/data/invitations.json` | `invitations: []`（発行済みデモ一時ID削除） |

運用開始時は CLI で招待のみ追加する:

```bash
npm run beta -- issue BETA-XXXX-YYYY --note "tester"
# デプロイ後にテスターへ一時IDのみ共有（パスワードは作らせる）
```

### ドキュメント

| ファイル | 変更 |
|----------|------|
| `docs/phase9-b-invitation-auth.md` | `demo-user` / `demo-pass` 記載削除 |
| `docs/phase9-invitation-auth.md` | 同上・例示をプレースホルダ化 |
| `docs/auth-service.md` | デモ平文削除 |
| `docs/beta-operation.md` | 例を `<USER_ID>` に変更 |
| `docs/integration-check/body-login*.json` | 平文パスワードを `<REDACTED>` |
| `docs/integration-check/body-invite.json` | 実招待ID削除 |

### 契約フィクスチャ（非本番・スキーマ検証用）

| ファイル | 変更 |
|----------|------|
| `fixtures/auth/user-record.json` | `fixture-user`（平文パスワード非記載。ログイン用途ではない） |
| `fixtures/auth/invitation-record.json` | `FIXTURE-INVITE-*` |
| `fixtures/auth/login-response.json` / `me-response.json` | `fixture-user` |
| `fixtures/auth/invite-start-response.json` | `FIXTURE-INVITE-01` |

---

## 確認項目（レビュー結果）

| 確認 | 結果 |
|------|------|
| `demo-user` が本番 seed に無い | **PASS**（`users.json` 空） |
| `demo-pass` がリポジトリに平文で残っていない | **PASS**（grep: 運用 docs の監査記述以外は除去。監査履歴 `phase11` の指摘文言のみ残存） |
| README に平文資格情報なし | **PASS** |
| docs に平文パスワードなし | **PASS**（プレースホルダ `<REDACTED>` のみ） |
| サンプル / seed JSON にログイン可能なデモ無し | **PASS** |
| 契約フィクスチャに平文パスワード無し | **PASS** |

### 残存してよいもの

- `docs/phase11-release-audit.md` 内の **監査指摘としての** `demo-user` / `demo-pass` 言及（歴史記録）
- `docs/integration-check/p9-*.json` 等の過去キャプチャ（トークンは期限切れ想定。平文パスワードは含まない）。必要なら再キャプチャ時に `fixture-user` 化
- `login.html` のプレースホルダ文字列（UI変更禁止のため未変更。seed 空のためそのIDでは利用不可）

---

## 公開前オペレータ確認

- [ ] デプロイ対象ブランチの `public/data/users.json` / `invitations.json` が空（または意図した招待のみ）
- [ ] 誤って古いデモ seed をマージしていない
- [ ] テスターへ渡すのは **一時IDのみ**（パスワードを運営が決め打ちしない）

**M2 ゲート:** 上記 seed / docs 整理完了 → **完了**
