# SingleAI — Web Prototype (Static)

競馬予想パッケージ **PredictionBundle** を「開催 → レース → 詳細」で閲覧する静的 Web プロトタイプです。  
AI・API・DB は含みません。表示のみ。

- レース詳細は **1レース分の PredictionBundle**（ダミー JSON）を読み込んで描画します。
- ローカル（`file://`）でも Cloudflare Pages でも動作します。

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

Cloudflare Pages にデプロイ:

- Build command: なし
- **Build output directory: `public`**

詳細は [`deployment_guide.md`](./deployment_guide.md) / [`cloudflare_pages_setup.md`](./cloudflare_pages_setup.md)。

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
single-10-cloudflare-deploy/
├─ public/                      # 配信対象（Pages 出力ディレクトリ）
│  ├─ index.html
│  ├─ race.html
│  ├─ assets/{styles.css, app.js}
│  ├─ data/{sample_prediction_bundle.json, sample_data.js}
│  ├─ _headers                  # Pages 用ヘッダ
│  └─ _redirects                # Pages 用（予約）
├─ functions/                   # 将来 API（現在は文書のみ）
├─ .gitignore
├─ README.md                    # 本ファイル
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
