# Cloudflare Pages Setup — KEIBA-Single-AI

**前提:** リポジトリ直下が Pages Root。ビルド不要の静的サイト。

---

## 0. Worker として認識される場合（重要）

Cloudflare が本リポジトリを **Worker** として扱い、`npx wrangler deploy` が自動設定される場合があります。  
これは「Pages プロジェクトである」と明示する設定が無いのが原因です。

**対策（本リポジトリでは対応済み）:** ルートに `wrangler.toml` を置き、`pages_build_output_dir` を指定します。

```toml
name = "keiba-single-ai"
pages_build_output_dir = "public"
compatibility_date = "2026-07-19"
```

- `pages_build_output_dir` があると Cloudflare は **Pages** として認識します（この行が無い `main`/`[assets]` 指定は Worker 扱い）。
- 既に **Worker プロジェクトとして作成済み**の場合は、リポジトリ設定だけでは Pages に変換されません。  
  ダッシュボードで **その Worker プロジェクトを削除**し、**Pages として作り直す**必要があります（§2）。

---

## 1. 推奨設定（コピペ用）

| 項目 | 値 |
|---|---|
| Production branch | `main`（または既定ブランチ） |
| Framework preset | **None** |
| Build command | **（空欄のまま）** |
| Build output directory | **`public`** |
| Root directory | **（空欄のまま）** |

Project 名: `KEIBA-Single-AI` → 実体・URL は `keiba-single-ai` / `https://keiba-single-ai.pages.dev`

---

## 2. GitHub 連携手順（Pages として作成）

1. （Worker として作成済みなら）Cloudflare の当該 **Worker プロジェクトを削除**。
2. Workers & Pages → **Create** → **Pages** タブ → **Connect to Git**。  
   ※「Workers」タブの Import ではなく **Pages** タブから入ること。
3. リポジトリ `KEIBA-Single-AI` を選択。
4. `wrangler.toml` の `pages_build_output_dir` により Build output = `public` が自動認識される。  
   手動設定する場合は §1 のとおり（Framework=None / Build command 空 / Build output=`public` / Root 空）。
5. Save and Deploy。

### 既にネストしてしまった場合

GitHub 上で `single-10-cloudflare-deploy/` 配下になっているときは:

1. ローカルの `KEIBA-Single-AI/`（直下構成）を再アップロード、または
2. Pages の **Root directory** を一時的に `single-10-cloudflare-deploy` にする

恒久対応は **直下構成に直して Root を空に戻す**こと。

---

## 3. Wrangler（任意）

```bash
cd KEIBA-Single-AI
npx wrangler pages deploy public --project-name keiba-single-ai
```

ローカル Pages 相当:

```bash
npx wrangler pages dev public
```

---

## 4. チェックリスト

- [ ] リポジトリ直下に `public/` がある
- [ ] Root directory が空
- [ ] Build output directory = `public`
- [ ] Build command が空
- [ ] `/` と `/race.html?race_id=20260719_hanshin_11` が表示できる
- [ ] `/data/sample_prediction_bundle.json` が 200
