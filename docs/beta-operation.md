# Expect KEIBA AI — β運営マニュアル（Phase10）

**対象:** 招待制β版の開始・日常運営・障害対応  
**管理UI:** なし（CLI + Cloudflare ダッシュボード）  
**前提:** Phase9-A（Access）/ Phase9-B（Invitation Auth）完了

関連:

- Access 確認: [`release-access-check.md`](./release-access-check.md)
- 招待永続化運用: [`invitation-operation.md`](./invitation-operation.md)
- AI 障害: [`ai-incident-runbook.md`](./ai-incident-runbook.md)
- 公開判定: [`release-readiness.md`](./release-readiness.md)
- Access: [`phase9-a-access-infrastructure.md`](./phase9-a-access-infrastructure.md)
- Invitation: [`phase9-b-invitation-auth.md`](./phase9-b-invitation-auth.md)

---

## 1. 招待コード発行

リポジトリルートで:

```bash
npm run beta -- issue BETA-XXXX-YYYY --note "テスターA" --expires 2026-12-31T00:00:00+09:00
```

互換（旧コマンド）:

```bash
node scripts/issue-invite.mjs BETA-XXXX-YYYY --note "テスターA"
```

発行後:

1. `public/data/invitations.json` が更新される
2. Pages にデプロイ（またはローカル `npm run dev` で ASSETS 反映）
3. テスターへ一時IDのみ共有（パスワードは作らせない）
4. 監査: `logs/audit/beta-audit.jsonl` に `invitation_issued`

確認:

```bash
npm run beta -- show BETA-XXXX-YYYY
npm run beta -- list --status issued
```

---

## 2. 利用開始（テスター）

1. Cloudflare Access を通過できること（Phase9-A）
2. `login.html` → 「一時ID（初回）」タブ
3. 一時ID入力 → `setup.html` でログインID / パスワード / 規約同意
4. 以後は正式ログイン（ログインID + パスワード）

運営側の確認:

```bash
npm run beta -- show BETA-XXXX-YYYY
# activated_user_id が入っていれば初回設定完了（本番はデプロイ済み seed を確認）
```

※ Workers 実行時の activate は Isolate メモリ上。恒久反映は `invitations.json` / `users.json` の更新デプロイ、または将来 KV/D1。

---

## 3. 停止

### 招待の停止

```bash
npm run beta -- disable BETA-XXXX-YYYY
```

未使用の issued を無効化。再有効化:

```bash
npm run beta -- enable BETA-XXXX-YYYY
```

### アカウント停止

```bash
npm run beta -- disable --user <USER_ID>
npm run beta -- enable --user <USER_ID>
```

停止後はログインが `USER_DISABLED`（403）。監査イベント: `account_disabled` / `account_enabled`。

### メンテナンス（全体）

1. `config/beta.json` と `public/config/beta.json` の `maintenance_mode` を `true`
2. デプロイ
3. Auth 系以外の `/api/*` は `503 MAINTENANCE`

---

## 4. パスワードリセット

```bash
npm run beta -- reset-password <USER_ID> <NEW_PASSWORD>
```

- 8文字以上
- `users.json` 更新後にデプロイが必要
- 監査: `password_reset`

---

## 5. 障害対応

| 症状 | 確認 | 対処 |
|------|------|------|
| Access で弾かれる | Cloudflare Zero Trust ポリシー / IdP | 許可メール・グループを確認。IaC 変更は承認後のみ |
| 一時IDが使えない | `show` / status | disabled・expired・activated を確認。必要なら `enable` または再 `issue` |
| ログインできない | パスワード / status | `reset-password` または `enable --user` |
| Prediction 502 | `AI_BASE_URL` / Tunnel / Service Token | Python AI・Tunnel 生存確認。公開バインド禁止 |
| Kaoba 失敗 | BFF ログ / Python | race 付きは auto→rule フォールバックを確認 |
| メンテナンスのまま | `beta.json` | `maintenance_mode: false` にして再デプロイ |
| 監査が無い | wrangler tail / `logs/audit/` | CLI はローカル JSONL。Workers は console JSON（`audit:true`） |

緊急時の最小対応:

1. `maintenance_mode: true` で書き込み・予測 API を止める
2. 問題のある invite / user を `disable`
3. Access で新規到達を絞る（ダッシュボード。IaC 勝手変更禁止）

---

## 6. Cloudflare Access 運用

- **変更禁止（Phase10）:** `infra/cloudflare` の勝手な apply / DNS 変更
- 日常: Zero Trust ダッシュボードで許可ユーザー追加・削除
- Service Token（BFF→AI）のローテーションは秘密を Pages secrets / `.dev.vars` に反映
- ブラウザ経路と Service Token 経路を混同しない

詳細: [`phase9-a-access-infrastructure.md`](./phase9-a-access-infrastructure.md)

---

## 7. Python AI 更新

1. `services/win5-ai` または連携先 `ai_platform/single` を更新
2. ローカル: `npm run ai`（`127.0.0.1` のみ。`0.0.0.0` 禁止）
3. ステージング/本番: Tunnel 経由ホストへデプロイ。**公開インターネット直バインド禁止**
4. BFF の `AI_BASE_URL` + Access Service Token が新ホストを向いているか確認
5. 契約テスト: `npm test`（PredictionBundle / Analysis / Kaoba 契約を壊していないこと）
6. スモーク: `/api/predictions`, `/api/analysis/:id`, `/api/kaoba/chat`

---

## 8. CLI 早見

```text
npm run beta -- issue <ID> [--note] [--expires]
npm run beta -- list [--status]
npm run beta -- disable <ID>
npm run beta -- disable --user <USER_ID>
npm run beta -- enable <ID>
npm run beta -- enable --user <USER_ID>
npm run beta -- show <ID>
npm run beta -- reset-password <USER_ID> <NEW_PASSWORD>
```

テスト用にデータルートを分離する場合: `BETA_ADMIN_ROOT=/path/to/tmp npm run beta -- ...`

---

## 9. 設定（beta.json）

| キー | 意味 |
|------|------|
| `beta_name` | β名称（表示・識別） |
| `maintenance_mode` | true で API をメンテ（Auth 一部除外） |
| `terms_version` | 初回設定で記録する規約版 |
| `invitation_required` | 招待制フラグ（現状 true。将来の開放用） |
| `max_concurrent_sessions` | 将来用（現状 null / 未強制） |
| `audit.enabled` | 利用監査の ON/OFF |

`config/beta.json` を正本とし、デプロイ前に `public/config/beta.json` へ同期すること。
