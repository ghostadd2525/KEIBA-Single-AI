# GitHub / Cloudflare / EC2 同期手順

**目的:** `functions/` の欠落誤解を解消し、Pages が EC2 Python AI を呼ぶ状態にする。

## 現状（確認済み）

| 場所 | 状態 |
|------|------|
| GitHub `main` | `functions/` **あり**（導入コミット `1b8bea5` 以降。tip はそれより新しい） |
| `.gitignore` | `functions/` は **除外していない** |
| EC2 が `d57f519` のまま | `functions/` が見えないのは **古い tip**（`d57f519` は services マーカーのみ） |
| Pages `/api/predictions` | Functions は動いているが `provider=mock` / `engine_source=bff_mock` → **`AI_BASE_URL` 未設定** |

## EC2（functions を取得）

```bash
cd /opt/expect-ai/current   # または clone 先
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse --short HEAD   # 1b8bea5 より新しいこと
ls functions/api/predictions
```

`functions/` は **Cloudflare 上で動く BFF** です。EC2 では主に `services/win5-ai` を動かします。

## EC2 Python（実推論メタ用）

`/opt/expect-ai/shared/.env`:

```bash
AI_HOST=127.0.0.1
AI_PORT=8000
AI_ALLOW_PUBLIC_BIND=0
AI_ENGINE=real
# AI_API_KEY=...  # Pages と一致させる場合
```

```bash
sudo systemctl restart expect-ai
curl -sS http://127.0.0.1:8000/health
```

## Cloudflare Pages → EC2（必須）

Pages Functions は `AI_BASE_URL` が空だと **必ず bff_mock** になります。

Tunnel の AI ホスト名（例 `https://ai-xxxx.example.com`）を設定:

```bash
# ローカル（管理者・要 wrangler login または CLOUDFLARE_API_TOKEN）
export CLOUDFLARE_API_TOKEN=...
node scripts/set-pages-ai-url.mjs https://<YOUR_TUNNEL_AI_HOSTNAME>

# Access Service Token も使う場合
export CF_ACCESS_CLIENT_ID=...
export CF_ACCESS_CLIENT_SECRET=...
node scripts/set-pages-ai-url.mjs https://<YOUR_TUNNEL_AI_HOSTNAME> --with-access
```

Dashboard でも可: Workers & Pages → `keiba-single-ai` → Settings → Environment variables  
（Production）に `AI_BASE_URL` を追加し、再デプロイ。

## 期待する API メタ

```text
GET https://keiba-single-ai.pages.dev/api/predictions

meta.provider = "python"
meta.items[].engine_source = "real_ai" または "mock_fallback"
# bff_mock であってはならない
```

## 切り分け

| 症状 | 原因 |
|------|------|
| EC2 に `functions/` が無い | `git pull` 不足（`d57f519` 止まり） |
| `provider=mock` / `bff_mock` | Pages に `AI_BASE_URL` が無い |
| `502` / AI_UNAVAILABLE | Tunnel / Access Token / Python down |
| `provider=python` だが全部 `mock_fallback` | EC2 で `AI_ENGINE=real` かつ Core 未接続（想定内） |
