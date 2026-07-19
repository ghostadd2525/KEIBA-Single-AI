# SINGLE-10 — Deployment Guide

**対象:** SingleAI Web Prototype v2（静的サイト）  
**目的:** ローカル（`file://`）と Cloudflare Pages の両方で動く公開手順をまとめる。  
**スコープ外:** AI / DB / API 実装。

---

## 1. このガイドの読み方

- とにかく手元で見たい → **§2 ローカル**
- Web に公開したい → **§3 Cloudflare Pages**（詳細は `cloudflare_pages_setup.md`）
- リポジトリ構成を知りたい → `github_structure.md`

---

## 2. ローカルで動かす

### 2-A. いちばん簡単（file://）

`public/index.html` をダブルクリックしてブラウザで開く。

- `file://` では `fetch` が使えないため、自動的に `data/sample_data.js`（同一内容）にフォールバックして表示する。
- 追加ソフト不要。

### 2-B. 本番に近い形（HTTP）

```bash
cd single-10-cloudflare-deploy/public
python -m http.server 8080
# ブラウザで http://localhost:8080/
```

または Node があれば:

```bash
cd single-10-cloudflare-deploy
npx wrangler pages dev public   # http://localhost:8788
```

HTTP 経由では `fetch("data/sample_prediction_bundle.json")` が使われる。

---

## 3. Cloudflare Pages へ公開（要約）

詳細は `cloudflare_pages_setup.md`。要点のみ:

1. 本フォルダを GitHub に push。
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git。
3. 設定:
   - Framework preset: **None**
   - Build command: 空
   - **Build output directory: `public`**
4. Save and Deploy → `https://<project>.pages.dev` が発行。

CLI 派は:

```bash
npx wrangler pages deploy public --project-name singleai-demo
```

---

## 4. 動作確認手順（両環境共通）

以下を目視で確認:

| # | 操作 | 期待 |
|---|---|---|
| 1 | トップを開く | 「開催一覧」に阪神/福島/中山が出る |
| 2 | 阪神をタップ | レース一覧（10R〜12R）。11R が「予想あり」 |
| 3 | 11R をタップ | レース詳細へ遷移 |
| 4 | 詳細の並び | 印 → AI本命カード → 残り買い目(タブ) → AI信頼度 → 解説 |
| 5 | タブ切替 | 「三連単 #2-5」「三連複 TOP5」が切り替わる |
| 6 | 折りたたみ | 「詳しい根拠を見る」「詳細を見る」が開閉する |
| 7 | 予想なしレース | 12R はタップ不可（空状態運用） |

Cloudflare Pages では加えて:

- `/data/sample_prediction_bundle.json` に直接アクセスして 200 が返る。

---

## 5. 環境別のデータ取得経路

| 環境 | 取得経路 |
|---|---|
| Cloudflare Pages | `fetch` で JSON |
| ローカル HTTP（http.server / wrangler） | `fetch` で JSON |
| ローカル `file://` | `sample_data.js` フォールバック |

`sample_prediction_bundle.json` を更新したら、`sample_data.js` を再生成（§6）。

---

## 6. サンプルデータ更新（任意）

JSON を編集した場合、`file://` 用の JS も同期する:

```bash
cd single-10-cloudflare-deploy/public/data
python -c "import json,pathlib; p=pathlib.Path('sample_prediction_bundle.json'); pathlib.Path('sample_data.js').write_text('window.SAMPLE_PREDICTION_BUNDLE = '+json.dumps(json.loads(p.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+';\n', encoding='utf-8')"
```

---

## 7. トラブルシュート

| 症状 | 原因 | 対処 |
|---|---|---|
| 画面が「読み込み中…」のまま | JSON も JS も読めていない | `file://` なら `data/sample_data.js` の存在確認 / HTTP で開く |
| Pages で 404 | 出力ディレクトリ設定ミス | Build output directory を `public` に |
| データが古い | `sample_data.js` 未同期 | §6 で再生成 |
| 詳細が「予想なし」 | `race_id` 不一致 | `?race_id=20260719_hanshin_11` を使用 |

---

## 8. ロールバック / 再デプロイ

- Cloudflare Pages はデプロイ履歴を保持。ダッシュボードから過去デプロイへ即ロールバック可能。
- Git 連携時は revert コミットを push すれば自動で戻る。

---

## 9. 次段階（このガイドの対象外）

- `functions/api/*` による PredictionBundle 配信（`functions/README.md`）
- 実データ連携・認証・購入導線

現段階は「静的に公開して画面を共有する」ことがゴール。
