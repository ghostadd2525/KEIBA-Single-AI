# SINGLE-10 — Cloudflare Pages Setup

**対象:** SingleAI Web Prototype v2（静的）  
**前提:** ビルド不要の純静的サイト。AI / DB / API は無し。

---

## 1. 前提知識（最小）

Cloudflare Pages は Git 連携で静的サイトを自動デプロイするサービス。  
本プロジェクトは **ビルド工程なし**（フレームワーク非依存）で、`public/` をそのまま配信する。

| 設定項目 | 値 |
|---|---|
| Framework preset | None |
| Build command | （空欄） |
| Build output directory | `public` |
| Root directory | `single-10-cloudflare-deploy`（リポジトリ直下に置く場合は空欄） |

> リポジトリのルートを `single-10-cloudflare-deploy` にした場合、Root directory は空でよい。  
> 大きいモノレポの一部として置く場合は Root directory にこのフォルダのパスを指定する。

---

## 2. デプロイ方法A：GitHub 連携（推奨）

1. GitHub に本フォルダを push（`github_structure.md` 参照）。
2. Cloudflare ダッシュボード → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**。
3. リポジトリを選択。
4. ビルド設定:
   - Framework preset: **None**
   - Build command: 空
   - Build output directory: **`public`**
   - （必要時）Root directory: このフォルダのパス
5. **Save and Deploy**。
6. 数十秒で `https://<project-name>.pages.dev` が発行される。

以降、`main` への push で自動再デプロイ。PR ごとにプレビュー URL も発行される。

---

## 3. デプロイ方法B：Wrangler CLI（Git なしでも可）

```bash
# 事前: Node.js 環境が必要
npm install -g wrangler
wrangler login

# public を直接アップロード
cd single-10-cloudflare-deploy
wrangler pages deploy public --project-name singleai-demo
```

- Git 連携なしでも即公開できる。
- CI から実行することも可能。

---

## 4. ローカル確認：Wrangler で Pages 相当を再現

`file://` ではなく、本番に近い HTTP 環境で確認したい場合:

```bash
cd single-10-cloudflare-deploy
npx wrangler pages dev public
# 表示された http://localhost:8788 を開く
```

Node が無い場合の簡易代替（Functions は動かないが静的配信は確認可）:

```bash
cd single-10-cloudflare-deploy/public
python -m http.server 8080
# http://localhost:8080/
```

---

## 5. `_headers` / `_redirects`

`public/_headers` と `public/_redirects` は Cloudflare Pages が自動認識する特殊ファイル。

- `_headers`: セキュリティヘッダとキャッシュ制御。  
  - `assets/*` は `max-age=3600`、`data/*` は `no-cache`（デモ更新を反映しやすく）。
- `_redirects`: 現状は静的2ページのため実質無効（コメントのみ）。  
  将来 SPA 化する場合の受け皿。

これらはローカル `file://` では無視されるが、Pages 上でのみ有効。動作には必須ではない。

---

## 6. データ取得の動作切替（重要）

フロントの `loadPredictionBundle()` は次の順で読む:

1. `fetch("data/sample_prediction_bundle.json")` … HTTP（Pages / ローカルサーバ）で成功
2. 失敗時（典型的に `file://`）→ `window.SAMPLE_PREDICTION_BUNDLE`（`data/sample_data.js`）

| 環境 | 主に使われる経路 |
|---|---|
| Cloudflare Pages | ① fetch JSON |
| `wrangler pages dev` / `http.server` | ① fetch JSON |
| ローカル `file://` 直開き | ② sample_data.js フォールバック |

→ **どの環境でも表示できる**。

---

## 7. カスタムドメイン（任意）

1. Pages プロジェクト → **Custom domains** → **Set up a domain**。
2. 対象ドメイン/サブドメインを入力し、DNS（CNAME）を Cloudflare の指示どおり設定。
3. 反映後、HTTPS 自動発行。

---

## 8. 将来 API を有効化する場合

- `functions/` に Pages Functions を追加すると、同一プロジェクトで `/api/*` が有効になる（別サーバ不要）。
- ビルド設定は変更不要（Pages が `functions/` を自動検出）。
- レスポンスは PredictionBundle 契約を維持し、フロントは取得 URL を差し替えるだけ。

---

## 9. チェックリスト

- [ ] Build output directory = `public`
- [ ] Build command 空 / Framework None
- [ ] `https://<project>.pages.dev/` で開催一覧が出る
- [ ] `/race.html?race_id=20260719_hanshin_11` で詳細が出る
- [ ] `data/sample_prediction_bundle.json` が 200 で取得できる
