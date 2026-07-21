# β期間中 Monitoring（Phase13）

**目的:** 招待制β期間中に、毎日（および随時）確認する運用項目  
**前提:** 新機能開発停止。観測・招待運用・障害対応のみ  
**関連:** [`ai-incident-runbook.md`](./ai-incident-runbook.md) · [`invitation-operation.md`](./invitation-operation.md) · [`health-checklist.md`](./health-checklist.md)

---

## 1. 毎日チェック（営業日・レース開催日は必須）

所要目安: 10–20 分。結果を日付付きで残す（チャット/シート可）。

| # | 項目 | 方法 | 異常時 |
|---|------|------|--------|
| D1 | Python health | AI ホスト `curl 127.0.0.1:8000/health` | 再起動 → だめならメンテ |
| D2 | Tunnel | cloudflared / CF ダッシュボード | 再起動・[`rollback-runbook.md`](./rollback-runbook.md) |
| D3 | bind 確認（週数回で可） | `127.0.0.1` のみ | 即停止・修正 |
| D4 | Access | 未許可で入れないことを週次でも可。毎日は「許可ユーザーで到達」 | ポリシー確認 |
| D5 | Pages デプロイ | 意図しないデプロイが混ざっていない | 必要なら Rollback |
| D6 | スモーク | Prediction 1・Kaoba 1（Access 内） | メンテ検討 |
| D7 | `maintenance_mode` | 意図せず true/false になっていない | beta.json 修正デプロイ |
| D8 | 招待残 | `npm run beta -- list --status issued` | 不要な issued は disable |
| D9 | テスター問い合わせ | 未解決チケット | 優先対応 |
| D10 | CF Status | 広域障害の有無 | 告知・待機 |

### 毎日ログ（テンプレ）

```text
日付:
実施者:
Python health: OK / NG
Tunnel: OK / NG
Prediction スモーク: OK / NG
Kaoba スモーク: OK / NG
issued 招待数:
インシデント:
翌営業日への申し送り:
```

---

## 2. 週次チェック

| # | 項目 | 内容 |
|---|------|------|
| W1 | Access 許可リスト | 離脱テスターの削除。Everyone が混入していない |
| W2 | Service Token / API Key | 漏洩疑いが無いか。ローテ予定の確認 |
| W3 | 監査ログ収集 | wrangler/Logpush/保管先に `login_*` / `invitation_*` が残っている |
| W4 | seed / Git | `users.json` / `invitations.json` が運用と一致。デモ復帰が無い |
| W5 | [`release-access-check.md`](./release-access-check.md) 短縮版 | 1.x / 3.x / 4.x を抜粋再確認 |
| W6 | バックアップ | 直近タグ、audit JSONL の退避 |

---

## 3. 随時（イベント駆動）

| イベント | 確認 |
|----------|------|
| 新規テスター追加 | Access メール追加 → issue → デプロイ → 配布 → setup 後 disable |
| テスター離脱 | Access 削除 → `disable --user` → デプロイ |
| デプロイ実施後 | [`health-checklist.md`](./health-checklist.md) 5 分版 |
| 障害報告 | [`ai-incident-runbook.md`](./ai-incident-runbook.md) → 迷ったらメンテ |
| パスワード忘れ | `reset-password` → デプロイ → 安全な経路で通知 |

---

## 4. 監視の「見る場所」

| 対象 | 場所 |
|------|------|
| Pages / Functions | Cloudflare Dashboard → デプロイ・メトリクス・ログ |
| Access | Zero Trust → ログ / アプリケーション |
| Tunnel | Zero Trust → Tunnels |
| Python | ホストのプロセス・アプリログ |
| 監査（BFF） | `wrangler pages deployment tail` 等、または Logpush（`audit:true`） |
| 監査（CLI） | 運営端末 `logs/audit/beta-audit.jsonl` |
| メンテフラグ | `public/config/beta.json` |

---

## 5. エスカレーション

| レベル | 例 | 行動 |
|--------|----|------|
| L1 | 単発 502、1 テスターのみ | ログ確認。再現しなければ経過観察 |
| L2 | 複数テスターで Prediction 失敗 | メンテ ON。Tunnel/Python 確認 |
| L3 | Access 過許可・外部露出疑い | 即塞ぐ + Rollback 系統。関係者へ連絡 |

---

## 6. β終了・縮小時

- 新規 `issue` 停止  
- 残 `issued` をすべて `disable`  
- 必要なら `maintenance_mode: true`  
- Access 許可を運営のみに縮小  
- 監査・招待 JSON の最終バックアップ  

---

## 7. やらないこと（β期間）

- Prediction / Analysis / Kaoba / Auth の契約変更  
- UI デザイン変更・新機能  
- IaC 構造の作り直し  
- デモユーザーの seed 復帰  
- 平文パスワードのドキュメント記載  
