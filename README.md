# KEIBA-Single-AI — Expect UI + API BFF

競馬予想 UI（Expect）と **Cloudflare Pages Functions（BFF）**、**Python WIN5 AI** を JSON API で疎結合した構成です。

```
UI → PredictionBundle（PredictionService）
      ├─ race_id → Analysis / Confidence / Ticket / Kaoba
      └─ Bundle 内投影（ai_confidence / betting_recommendations）
```

- **共通契約は PredictionBundle**（`single-prediction-bundle/2.0`）。
- 他サービスは `race_id` キーで参照。フロント入口も Bundle のみ。
- ブラウザは Python を直接呼びません（同オリジン `/api` のみ）。
- API 仕様: [`docs/api.md`](./docs/api.md)
- **このリポジトリ直下**が Cloudflare Pages の Root です。

---

## Cloudflare Pages 設定（必須）

| 項目 | 値 |
|---|---|
| Framework preset | **None** |
| Build command | **（空）** |
| Build output directory | **`public`** |
| Root directory | **（空）** ← リポジトリ直下をそのまま使う |

ルートの `wrangler.toml` に `pages_build_output_dir = "public"` を記載しているため、  
Cloudflare は本リポジトリを **Worker ではなく Pages** として認識します。

> **Worker として認識された / `npx wrangler deploy` が設定された場合**  
> 既存の Worker プロジェクトを削除し、**Workers & Pages → Create → Pages タブ → Connect to Git** で作り直してください。詳細は [`cloudflare_pages_setup.md`](./cloudflare_pages_setup.md) §0/§2。

公開 URL 例: `https://keiba-single-ai.pages.dev`  
（プロジェクト名 `KEIBA-Single-AI` は Pages 上で `keiba-single-ai` に正規化されます）

詳細手順: [`cloudflare_pages_setup.md`](./cloudflare_pages_setup.md) / [`deployment_guide.md`](./deployment_guide.md)

---

## クイックスタート

### API 付きローカル（推奨）

```bash
# 1) Python WIN5 AI
python services/win5-ai/run.py

# 2) Pages + Functions（別ターミナル）
npm install
copy .dev.vars.example .dev.vars   # Windows
npm run dev
# http://localhost:8788/ など（wrangler が表示する URL）
```

### 静的のみ（Functions なし）

```bash
cd public
python -m http.server 8080
```

`ExpectApi` は `/api` 不通時に `public/data/mocks/` へフォールバックします。

### Web に公開する

1. 本リポジトリを GitHub に配置（直下に `public/` と `functions/` があること）
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git
3. 上記「Cloudflare Pages 設定」どおりに入力 → Save and Deploy
4. Pages の環境変数に `AI_BASE_URL` / `AI_API_KEY` を設定（Python サービス URL）

---

## 画面

| 画面 | ファイル | 内容 |
|---|---|---|
| 開催一覧 / レース一覧 | `public/index.html` | 開催日・競馬場・レースの選択（hash 遷移） |
| レース詳細 | `public/race.html?race_id=...` | 予想パッケージの表示 |

レース詳細の並び（Prototype v2 / P0 反映）:

1. 印（◎ ○ ▲ △）
2. AI本命（三連単 #1）カード
3. 残りのおすすめ（三連単 #2-5 / 三連複 TOP5 タブ）
4. AI信頼度（1行 + 折りたたみ）
5. 解説（短文 + 「詳細を見る」）

---

## ディレクトリ構成

```text
KEIBA-Single-AI/
├─ public/                 # UI（Pages 配信）
│  ├─ assets/api/          # ExpectApi / adapters
│  └─ data/mocks/          # BFF・静的フォールバック用 JSON
├─ functions/              # Pages Functions BFF（/api/*）
├─ services/win5-ai/       # Python WIN5 AI（/v1/*）
├─ docs/api.md             # API 仕様
├─ wrangler.toml
└─ package.json
```

詳細は [`docs/api.md`](./docs/api.md) / [`github_structure.md`](./github_structure.md)。

---

## データについて

- 契約の中核は **PredictionBundle**（`single-prediction-bundle/2.0`）。
- 本番経路: `ExpectApi.race(id)` → `/api/race/:id` → Python `/v1/races/{id}/bundle`
- 開発フォールバック: `public/data/mocks/` および `sample_prediction_bundle.json`
- **招待制β:** `public/data/users.json` / `invitations.json` は空 seed。招待は `npm run beta -- issue`（[`docs/invitation-operation.md`](./docs/invitation-operation.md)）
- **公開判定:** [`docs/release-readiness.md`](./docs/release-readiness.md)

---

## スコープ外

- ログイン / 認証
- DB / 実データ API
- AI 推論
- オッズ・購入・リアルタイム更新
