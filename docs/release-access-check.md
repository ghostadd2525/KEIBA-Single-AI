# Release Access Check（M1）

**Phase12 Release Gate Closure**  
**目的:** Cloudflare Access が招待制βの外周として正しく適用されていることを、公開前に確認する  
**範囲:** 手順・確認項目のみ（IaC 構造変更なし。apply は管理者）

関連: [`phase9-a-access-infrastructure.md`](./phase9-a-access-infrastructure.md) · [`infra/cloudflare/README.md`](../infra/cloudflare/README.md)

---

## 前提

- Terraform / ダッシュボード操作は **管理者のみ**
- `allowed_emails` / `allowed_email_domains` が **両方空のまま apply すると Everyone になる**（`access.tf`）— **禁止**
- 本チェックの全項目が PASS になるまで β URL をテスターに配布しない

---

## 1. Everyone Policy が存在しない

| # | 確認 | 方法 | 期待 | 結果 |
|---|------|------|------|------|
| 1.1 | Pages Access Application の Allow に `Everyone` が無い | Zero Trust → Access → Applications → Pages アプリ → Policies | Include は **メール / グループ / ドメインのみ** | ☐ |
| 1.2 | AI hostname Access Application にブラウザ用 Everyone Allow が無い | 同上（AI アプリ） | **Service Auth（Service Token）のみ**。Identity Everyone なし | ☐ |
| 1.3 | Terraform tfvars | `allowed_emails` または `allowed_email_domains` が非空 | 空配列のまま apply していない | ☐ |
| 1.4 | Bypass / Bypass all ポリシー | ダッシュボード | 本番に Bypass Everyone が無い | ☐ |

**FAIL 時:** テスター招待を中止。許可リストを設定してから再確認。

---

## 2. 許可グループのみ

| # | 確認 | 方法 | 期待 | 結果 |
|---|------|------|------|------|
| 2.1 | 許可メール一覧が βテスターと一致 | Access Policy Include | 余分な個人・広すぎるドメインなし | ☐ |
| 2.2 | グループ運用の場合 | IdP グループ | βグループのみ。全社員グループを誤設定していない | ☐ |
| 2.3 | （推奨）WARP Require | Pages ポリシー | Require WARP が有効（チーム方針に従う） | ☐ |
| 2.4 | 未許可アカウント | 別メールで Pages URL | Access ログイン後も拒否、またはアプリ未到達 | ☐ |

---

## 3. Tunnel の接続確認

| # | 確認 | 方法 | 期待 | 結果 |
|---|------|------|------|------|
| 3.1 | Python が loopback のみ | AI ホストで `ss` / `netstat` | `127.0.0.1:8000` のみ。`0.0.0.0` でない | ☐ |
| 3.2 | `AI_ALLOW_PUBLIC_BIND` | 環境変数 | 未設定または `0` | ☐ |
| 3.3 | cloudflared 稼働 | `systemctl status` / プロセス | Healthy / Connected | ☐ |
| 3.4 | ローカルヘルス | `curl http://127.0.0.1:8000/health` | ok | ☐ |
| 3.5 | パブリック IP:8000 | 外部から curl | タイムアウト / 接続拒否 | ☐ |
| 3.6 | Tunnel ホスト名 | Cloudflare Tunnel ダッシュボード | AI 用 hostname が登録済み | ☐ |

---

## 4. Workers（Pages Functions）→ Python 到達確認

| # | 確認 | 方法 | 期待 | 結果 |
|---|------|------|------|------|
| 4.1 | Pages Secrets | `AI_BASE_URL` | Tunnel の `https://ai-...`（公開 IP 直ではない） | ☐ |
| 4.2 | Service Token | `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` | staging/prod に設定済み | ☐ |
| 4.3 | （推奨）`AI_API_KEY` | Pages + Python 同一 | 設定済み | ☐ |
| 4.4 | アプリ経由スモーク | Access 通過後にレース一覧・詳細 | 200 相当・契約どおり表示 | ☐ |
| 4.5 | AI hostname 直アクセス | ブラウザ / curl（Token なし） | 302/403（Access）。予測 JSON が取れない | ☐ |

```bash
# Token なし（拒否されること）
curl -sS -o /dev/null -w "%{http_code}\n" "https://<ai_private_hostname>/health"

# Token あり（管理者のみ・秘密をログに残さない）
curl -sS -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
  "https://<ai_private_hostname>/health"
```

---

## 5. Access JWT / Service Auth が期待どおり動作すること

本構成の BFF→AI は **Access Service Token**（Client ID/Secret ヘッダ）を使用する。ブラウザの Cf-Access-Jwt-Assertion は Pages 外周で消費され、Python には通常到達しない。

| # | 確認 | 方法 | 期待 | 結果 |
|---|------|------|------|------|
| 5.1 | 未認証で Pages | シークレットウィンドウ | Access チャレンジ。BFF/UI に到達しない | ☐ |
| 5.2 | 認証後セッション | 許可ユーザー | Pages / `/api/*` に到達 | ☐ |
| 5.3 | Service Token 欠落 | 一時的に Secret を外したデプロイ（検証後必ず戻す） | BFF→AI 失敗（502 等）。AI が匿名で応答しない | ☐ |
| 5.4 | 不正 Token | 誤った Client Secret | Access 拒否 | ☐ |
| 5.5 | Token ローテーション手順 | 運用メモ | 新旧切替手順が分かっている | ☐ |

---

## サインオフ

| 項目 | 記入 |
|------|------|
| 環境（staging / production） | |
| 実施者 | |
| 実施日 | |
| 全項目 PASS | ☐ Yes / ☐ No |
| 特記事項 | |

**M1 ゲート:** 上記サインオフが Yes のとき完了。未実施のまま公開 URL を配布してはならない。

---

## チェックリスト短縮版（公開直前）

1. Everyone なし・許可リストのみ  
2. 未許可ユーザーが Pages に入れない  
3. Python が外部から見えない  
4. Tunnel Healthy  
5. BFF から予測が取れる  
6. AI hostname 直は Access で拒否  
