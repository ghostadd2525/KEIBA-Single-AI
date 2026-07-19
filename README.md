# KEIBA-Single-AI — Web Prototype (Static)

競馬予想パッケージ **PredictionBundle** を「開催 → レース → 詳細」で閲覧する静的 Web プロトタイプです。  
AI・API・DB は含みません。表示のみ。

- レース詳細は **1レース分の PredictionBundle**（ダミー JSON）を読み込んで描画します。
- ローカル（`file://`）でも Cloudflare Pages でも動作します。
- **このリポジトリ直下**が Cloudflare Pages の Root です（ネストした `single-10-cloudflare-deploy/` はありません）。

---

## Cloudflare Pages 設定（必須）

| 項目 | 値 |
|---|---|
| Framework preset | **None** |
| Build command | **（空）** |
| Build output directory | **`public`** |
| Root directory | **（空）** ← リポジトリ直下をそのまま使う |

公開 URL 例: `https://keiba-single-ai.pages.dev`  
（プロジェクト名 `KEIBA-Single-AI` は Pages 上で `keiba-single-ai` に正規化されます）

詳細手順: [`cloudflare_pages_setup.md`](./cloudflare_pages_setup.md) / [`deployment_guide.md`](./deployment_guide.md)

---

## クイックスタート

### 手元で見る（最短）

`public/index.html` をブラウザで開くだけ。

### HTTP で見る

```bash
cd public
python -m http.server 8080
# http://localhost:8080/
```

### Web に公開する

1. 本リポジトリを GitHub に配置（直下に `public/` があること）
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git
3. 上記「Cloudflare Pages 設定」どおりに入力 → Save and Deploy

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
KEIBA-Single-AI/                 # ← リポジトリ Root（= Pages Root）
├─ public/                       # 配信対象（Build output directory）
│  ├─ index.html
│  ├─ race.html
│  ├─ assets/{styles.css, app.js}
│  ├─ data/{sample_prediction_bundle.json, sample_data.js}
│  ├─ _headers
│  └─ _redirects
├─ functions/                    # 将来 API（現在は文書のみ）
├─ .gitignore
├─ README.md
├─ deployment_guide.md
├─ github_structure.md
└─ cloudflare_pages_setup.md
```

詳細は [`github_structure.md`](./github_structure.md)。

---

## データについて

- 入力契約は **PredictionBundle**（SINGLE-07）。
- `public/data/sample_prediction_bundle.json` がダミーデータ。
- `public/data/sample_data.js` は `file://` 用の同一内容フォールバック。
- 取得順:
  1. `fetch("data/sample_prediction_bundle.json")`（HTTP 環境）
  2. 失敗時 `window.SAMPLE_PREDICTION_BUNDLE`（`file://` 環境）

JSON を更新したら `sample_data.js` を再生成（[`deployment_guide.md`](./deployment_guide.md) §6）。

---

## 将来の API 追加

`functions/` に Cloudflare Pages Functions を置くと、同一プロジェクトで `/api/*` が使えます。  
フロントの取得先を静的 JSON から `/api/predictions/{race_id}` に差し替えるだけ（レスポンスは PredictionBundle 契約を維持）。  
詳細は `functions/README.md`。

---

## スコープ外

- ログイン / 認証
- DB / 実データ API
- AI 推論
- オッズ・購入・リアルタイム更新
