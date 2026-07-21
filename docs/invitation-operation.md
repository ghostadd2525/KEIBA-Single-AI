# Invitation Operation（M3）

**Phase12 Release Gate Closure**  
**目的:** Invitation の永続化を **運用手順** で担保する（本 Phase は実装変更なし）  
**背景:** Workers 上の `activate` / `createUser` は Isolate メモリのみ。ASSETS JSON を更新してデプロイしないと、コールド後に同一一時IDを再利用され得る。

関連: [`beta-operation.md`](./beta-operation.md) · CLI: `npm run beta`

---

## 原則

1. **正本はリポジトリの** `public/data/invitations.json` / `users.json`（デプロイされた ASSETS）
2. ランタイムのメモリ状態は **一時的**。公開βでは「メモリだけ」に依存しない
3. 1 一時ID = 1 ユーザー。activate 後は必ず正本を更新してデプロイする
4. 平文パスワードをチケット・チャット・docs に残さない

---

## 1. 招待発行

```bash
npm run beta -- issue <INVITE_ID> --note "<tester>" [--expires ISO8601]
git add public/data/invitations.json
# レビュー後コミット・デプロイ（Pages）
npm run beta -- show <INVITE_ID>
```

| 項目 | ルール |
|------|--------|
| ID形式 | 推測困難（例 `BETA-` + ランダム）。連番禁止 |
| 共有 | Access 通過可能なテスターへ一時IDのみ |
| 確認 | `list --status issued` |

監査: `logs/audit/beta-audit.jsonl` に `invitation_issued`

---

## 2. Activate（初回設定完了後）

テスターが `invite/start` → `setup` に成功した直後:

### 必須手順（β運用）

1. テスターから **ログインID**（setup で選んだ ID）を受け取る（パスワードは受け取らない）
2. 正本を更新する（どちらか）:

**A. CLI でユーザー行を追加（推奨フロー）**

- `invitations.json` の該当行を `status: activated`、`activated_user_id`、`activated_at` に更新  
  （`npm run beta` に activate サブコマンドが無い場合は JSON を手編集、または同等の編集を行う）
- `users.json` にユーザーを追加するには、setup 時点の hash が Isolate にしか無い点に注意  
  → **β推奨:** setup 成功後、運営が `reset-password` で **仮パスワードを設定し**、テスターに再設定を依頼するか、テスターに setup 直後のログインができるうちに運営が JSON へ password_hash を同期する運用を取らない  
  → **実務的なβ手順（シンプル）:**

### β推奨オペレーション（同時利用者を制御）

| モード | 手順 |
|--------|------|
| **厳格（推奨）** | 招待は **1件ずつ** 発行・デプロイ。テスターが setup 完了したら、即 `disable <INVITE_ID>` を正本に反映してデプロイ（再利用防止）。ユーザー永続は次デプロイまでにログインできることを確認し、必要なら `users.json` へ行追加（hash は `reset-password` で再発行して同期） |
| **簡易** | 同時に **issued は最大1件**。setup 完了を確認したらその ID を `disable` してデプロイ。次のテスター用に新規 `issue` |

```bash
# setup 完了を確認したら即座に失効（再利用防止）
npm run beta -- disable <INVITE_ID>
# デプロイ必須
```

ユーザー継続利用:

```bash
# パスワードを運営側で再設定して users.json に残す（テスターへ安全な経路で通知）
npm run beta -- reset-password <USER_ID> <NEW_PASSWORD>
# デプロイ必須
```

> setup で作られたメモリ上ユーザーはデプロイで消える。**正本 `users.json` に載せたアカウントだけが再デプロイ後もログイン可能。**

---

## 3. 失効

### 招待の失効

```bash
npm run beta -- disable <INVITE_ID>
# デプロイ
```

| 状態 | 意味 |
|------|------|
| `disabled` | invite/start 不可 |
| `expired` | `expires_at` 経過（再 enable 不可） |

### アカウント停止

```bash
npm run beta -- disable --user <USER_ID>
# デプロイ
```

再開: `enable` / `enable --user` の後デプロイ。

---

## 4. バックアップ

| 対象 | 方法 |
|------|------|
| 招待・ユーザー正本 | Git 履歴（`public/data/*.json`） |
| 監査 CLI | `logs/audit/beta-audit.jsonl`（ローカル。必要なら別ストレージへコピー） |
| デプロイ直前 | タグまたはリリースブランチを切る |

バックアップ頻度: **issue / disable / reset-password / ユーザー追加のたびにコミット**

---

## 5. 復旧

| 障害 | 復旧 |
|------|------|
| 誤って招待を消した | Git の前リビジョンから `invitations.json` を復元 → デプロイ。必要なら `enable` |
| ユーザーがログインできない（デプロイで消えた） | `users.json` に行が無ければ `reset-password` で再作成相当（行追加 + hash）→ デプロイ。招待は `disabled` のまま |
| 一時ID再利用が疑われる | 当該 ID を `disable`、関連ユーザーを `disable --user`、Access ログ確認 |
| リポジトリ破損 | 直近タグから `public/data` をチェックアウトして再デプロイ |

---

## 運用チェックリスト（毎回）

- [ ] issue 後にデプロイした  
- [ ] setup 完了後、当該 invite を disable（または activated を正本反映）してデプロイした  
- [ ] 継続ユーザーは `users.json` に存在する  
- [ ] パスワードをチャットに残していない  
- [ ] `show` / `list` で状態が期待どおり  

**M3 ゲート:** 本手順を運営が理解し、公開時の標準オペレーションとする → **完了**（実装による永続化は将来課題・残リスク）
