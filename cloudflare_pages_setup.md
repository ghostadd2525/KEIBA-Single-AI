# Cloudflare Pages Setup — KEIBA-Single-AI

**前提:** リポジトリ直下が Pages Root。ビルド不要の静的サイト。

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

## 2. GitHub 連携手順

1. リポジトリ `KEIBA-Single-AI` に、**直下へ** `public/` などを配置（ネストしない）。
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git。
3. リポジトリを選択し、§1 の設定を入力。
4. Save and Deploy。

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
