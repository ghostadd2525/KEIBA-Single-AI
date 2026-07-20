# Deployment Guide — KEIBA-Single-AI

**Baseline:** v1.0.0-beta  
**対象:** Cloudflare Pages（フロント + BFF）と AWS EC2 上の Python AI

関連: [`aws-deployment.md`](./aws-deployment.md) · [`aws-architecture.md`](./aws-architecture.md)

---

## 1. リポジトリ内のバックエンド所在

| 項目 | 値 |
|------|-----|
| パス | `services/win5-ai/` |
| 実装 | Python **標準ライブラリ** HTTP（`ThreadingHTTPServer`） |
| 契約 | PredictionBundle / Analysis / Kaoba（既存） |
| FastAPI | **未使用**（将来候補のみ。現行は uvicorn 不要） |

エントリポイント:

| 方法 | コマンド |
|------|----------|
| リポジトリルートから | `python services/win5-ai/run.py` |
| パッケージとして | `cd services/win5-ai && python -m app.main` |
| モジュール直実行 | `cd services/win5-ai && python -m app`（`__main__.py`） |

環境変数:

```bash
AI_HOST=127.0.0.1          # 必須（Tunnel 背後）。公開 bind 禁止が既定
AI_PORT=8000
AI_ALLOW_PUBLIC_BIND=0     # 1 にしない（EC2 本番）
AI_API_KEY=...               # 任意（BFF と一致）
AI_PLATFORM_ROOT=...         # 任意（隣接 ai_platform がある場合）
```

ヘルスチェック: `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`

---

## 2. 推奨起動コマンド（systemd）

`/etc/systemd/system/expect-ai.service` 例:

```ini
[Unit]
Description=Expect Python AI (v1.0.0-beta)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=expect-ai
Group=expect-ai
WorkingDirectory=/opt/expect-ai/current
EnvironmentFile=-/opt/expect-ai/shared/.env
ExecStart=/opt/expect-ai/shared/venv/bin/python /opt/expect-ai/current/services/win5-ai/run.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`.env` 例:

```bash
AI_HOST=127.0.0.1
AI_PORT=8000
AI_ALLOW_PUBLIC_BIND=0
```

cloudflared は別 unit（既存 `infra/cloudflare/cloudflared/systemd/cloudflared-expect-ai.service`）。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now expect-ai
sudo systemctl enable --now cloudflared-expect-ai
curl -sS http://127.0.0.1:8000/health
```

---

## 3. EC2 へデプロイ（git clone → 依存関係 → 起動）

前提: Ubuntu 24.04、Git、Python 3.11+、cloudflared 導入済み。

### 3.1 初回

```bash
sudo useradd --system --home /opt/expect-ai --shell /usr/sbin/nologin expect-ai || true
sudo mkdir -p /opt/expect-ai/{releases,shared} /var/log/expect-ai
sudo chown -R expect-ai:expect-ai /opt/expect-ai /var/log/expect-ai

# アプリ配置（例: 直接 clone）
sudo -u expect-ai git clone https://github.com/ghostadd2525/KEIBA-Single-AI.git /opt/expect-ai/releases/current-src
sudo -u expect-ai ln -sfn /opt/expect-ai/releases/current-src /opt/expect-ai/current

cd /opt/expect-ai/current/services/win5-ai
sudo -u expect-ai python3 -m venv /opt/expect-ai/shared/venv
sudo -u expect-ai /opt/expect-ai/shared/venv/bin/pip install -U pip
sudo -u expect-ai /opt/expect-ai/shared/venv/bin/pip install -r requirements.txt

sudo tee /opt/expect-ai/shared/.env >/dev/null <<'EOF'
AI_HOST=127.0.0.1
AI_PORT=8000
AI_ALLOW_PUBLIC_BIND=0
AI_ENGINE=real
EOF
sudo chown expect-ai:expect-ai /opt/expect-ai/shared/.env
sudo chmod 640 /opt/expect-ai/shared/.env

# systemd unit を配置してから:
sudo systemctl enable --now expect-ai
curl -sS http://127.0.0.1:8000/health
```

### 3.2 更新（pull → restart）

```bash
cd /opt/expect-ai/current
sudo -u expect-ai git fetch --prune
sudo -u expect-ai git checkout main
sudo -u expect-ai git pull --ff-only origin main
sudo -u expect-ai /opt/expect-ai/shared/venv/bin/pip install -r services/win5-ai/requirements.txt
sudo systemctl restart expect-ai
curl -sf http://127.0.0.1:8000/health
```

### 3.3 依存関係について

`services/win5-ai/requirements.txt` は **現行ランタイムでは実質空**（stdlib のみ）。  
`pip install -r requirements.txt` は成功し、追加パッケージは入りません。これが正常です。

---

## 4. Cloudflare Pages（フロント）

| 項目 | 値 |
|------|-----|
| Build output directory | `public` |
| Functions | `functions/`（リポジトリに含まれる場合） |

詳細: ルートの [`deployment_guide.md`](../deployment_guide.md) / [`cloudflare_pages_setup.md`](../cloudflare_pages_setup.md)

---

## 5. ローカル開発（AI）

```bash
# リポジトリルート
python services/win5-ai/run.py
# 別ターミナル
npm run dev:ai   # Pages + AI_BASE_URL=http://127.0.0.1:8000
```

---

## 6. 確認チェックリスト

- [ ] GitHub に `services/win5-ai/` がある
- [ ] GitHub に `functions/` がある（`1b8bea5` 以降）
- [ ] `requirements.txt` がある
- [ ] `curl 127.0.0.1:8000/health` が ok
- [ ] `ss` 等で listen が `127.0.0.1:8000` のみ
- [ ] cloudflared が Connected
- [ ] Pages の `AI_BASE_URL` が Tunnel ホストを指す（無いと `bff_mock`）
- [ ] `/api/predictions` の `engine_source` が `real_ai` または `mock_fallback`

同期詳細: [`ops/sync-github-cloudflare-ec2.md`](./ops/sync-github-cloudflare-ec2.md)