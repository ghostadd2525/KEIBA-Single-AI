# Rollback Runbook（Phase13）

**目的:** β公開失敗・重大障害時に、被害を最小化して安全な状態へ戻す  
**原則:** 迷ったら **メンテ ON** → 原因切り分け → 必要ならデプロイ/Access/Tunnel を戻す  
**禁止:** その場での新機能実装・契約変更・IaC 構造の大規模変更

関連: [`launch-day-runbook.md`](./launch-day-runbook.md) · [`ai-incident-runbook.md`](./ai-incident-runbook.md)

---

## 1. いつ Rollback するか

| トリガー | 緊急度 | 第一手 |
|----------|--------|--------|
| Access が Everyone / 未保護で到達可能 | Critical | Access ポリシー即修正 or Pages をメンテ/デプロイ停止 |
| Python が外部から到達可能 | Critical | プロセス停止・bind 修正・FW |
| 予測が全面モックのみ / AI 全断 | High | `maintenance_mode: true` |
| デプロイ後にログイン/setup 全滅 | High | 前バージョン Pages デプロイに戻す |
| 招待の大量再利用・不正アカウント疑い | High | 該当 invite/user disable + メンテ検討 |
| 限定的な 1 API 不調 | Medium | メンテは任意。監視強化 |

---

## 2. 即座の被害止め（5 分以内）

1. **`maintenance_mode: true`**  
   - `config/beta.json` と `public/config/beta.json` を同期  
   - Pages をデプロイ  
   - Auth 一部以外の `/api/*` が 503  
2. テスターへ「メンテナンス中。利用停止」を連絡  
3. 新規の一時ID配布を停止  
4. 必要なら Access で許可を一時的に運営メールのみに縮小（ダッシュボード。構造変更ではなくポリシー値の縮小）

---

## 3. 系統別 Rollback

### 3.1 Cloudflare Pages（UI + Functions）

| 手順 | 内容 |
|------|------|
| 1 | Cloudflare Dashboard → Workers & Pages → 対象プロジェクト → Deployments |
| 2 | **直近の正常デプロイ**を Retry deployment / Rollback（UI の表記に従う） |
| 3 | または Git で前タグを production ブランチに戻して再デプロイ |
| 4 | デプロイ後に [`health-checklist.md`](./health-checklist.md) |
| 5 | seed（`invitations.json` / `users.json`）が意図した内容か確認 |

**注意:** Functions と静的資産は同一デプロイ単位。片側だけ戻さない。

### 3.2 Secrets

| 症状 | 復旧 |
|------|------|
| `AI_BASE_URL` 誤り | 正しい Tunnel URL に `wrangler pages secret put` → 再デプロイ（secret 反映は再デプロイが必要な場合あり） |
| Service Token 誤り | Terraform output / Zero Trust から正しい ID/Secret を再設定 |
| 鍵ローテ失敗 | 旧 Token が残っていれば一旦戻す。AI 側 `AI_API_KEY` と揃える |

### 3.3 Tunnel / cloudflared

| 手順 | 内容 |
|------|------|
| 1 | AI ホストで `cloudflared` 再起動 |
| 2 | それでもダメなら前回稼働していた token / 設定に戻す（バックアップから） |
| 3 | `curl http://127.0.0.1:8000/health` が先に OK であること |
| 4 | CF ダッシュボードで Tunnel status |

Tunnel を止めれば BFF→AI は死ぬ。公開継続する場合はメンテのまま復旧作業。

### 3.4 Python AI

| 手順 | 内容 |
|------|------|
| 1 | プロセス停止 → `AI_HOST=127.0.0.1` `AI_ALLOW_PUBLIC_BIND=0` で再起動 |
| 2 | 依存・ログを確認。壊れたデプロイなら前バージョンのアプリディレクトリに戻す |
| 3 | health OK 後に Tunnel 経由スモーク |

**絶対に** 障害対応中に `0.0.0.0` 公開バインドしない。

### 3.5 Terraform / Access

| 状況 | 復旧 |
|------|------|
| 誤って Everyone | ダッシュボードで即 Allow を許可リストに戻す。可能なら直前の tfstate に対応する `plan` で是正 apply（**構造変更ではなくポリシー修正**） |
| 誤って AI をブラウザ公開 | AI アプリを Service Token のみに戻す |
| apply 自体が失敗 | 半適用なら `plan` で差分確認。無理に再 apply 連打しない。Cloudflare サポート/既存手順に従う |

IaC **構造**（モジュール分割の作り直し等）は Rollback 中に行わない。

### 3.6 Invitation / アカウント

```bash
npm run beta -- disable <INVITE_ID>
npm run beta -- disable --user <USER_ID>
# デプロイ必須
```

不正利用疑い時は該当をすべて disable し、Access ログを確認。

---

## 4. 復旧後の再開手順

1. [`health-checklist.md`](./health-checklist.md) 全 PASS  
2. [`release-access-check.md`](./release-access-check.md) の短縮版を再実施  
3. `maintenance_mode: false` → デプロイ  
4. テスターへ再開連絡（必要なら新規一時IDを issue）  
5. インシデントメモ（時刻・原因・実施した Rollback・再発防止）を残す  

---

## 5. Rollback 判定フロー（簡易）

```text
障害検知
  → メンテ ON（必須に近い）
  → Access / 外部公開の危険あり？
       Yes → Access・bind を最優先で塞ぐ
       No  → Pages / Secrets / Tunnel / Python のどこか
  → 系統別 Rollback
  → Health PASS？
       Yes → メンテ OFF → 再開
       No  → メンテ継続・エスカレーション
```

---

## 6. 連絡テンプレ

**停止:**

> Expect β は只今メンテナンス中です。復旧まで予想機能の利用を停止してください。

**再開:**

> メンテナンスを終了しました。ページを再読み込みのうえご利用ください。問題が続く場合は運営まで。
