# SINGLE-10 — GitHub Structure

**対象:** SingleAI Web Prototype v2 の公開用リポジトリ構成  
**方針:** 静的サイト（HTML/CSS/JS のみ）· 将来 API を足しやすい配置  
**スコープ外:** AI / DB / API 実装

---

## 1. ルート構成

このフォルダ（`single-10-cloudflare-deploy/`）を **リポジトリのルート**として公開する想定。

```text
single-10-cloudflare-deploy/        # = リポジトリルート
├─ public/                          # 公開物（Cloudflare Pages の出力ディレクトリ）
│  ├─ index.html                    # 開催一覧 / レース一覧（hash 遷移）
│  ├─ race.html                     # レース詳細（?race_id=...）
│  ├─ assets/
│  │  ├─ styles.css
│  │  └─ app.js
│  ├─ data/
│  │  ├─ sample_prediction_bundle.json   # PredictionBundle（SINGLE-07 契約）
│  │  └─ sample_data.js                   # file:// 用フォールバック（同一内容）
│  ├─ _headers                      # Cloudflare Pages: セキュリティ/キャッシュ
│  └─ _redirects                    # Cloudflare Pages: 予約（現状ほぼ無効）
├─ functions/                       # 将来 API（Pages Functions）· 現在は文書のみ
│  └─ README.md
├─ .gitignore
├─ README.md                        # = updated_README.md（デプロイ手順込み）
├─ deployment_guide.md
├─ github_structure.md              # 本ファイル
├─ cloudflare_pages_setup.md
└─ updated_README.md                # 成果物としての README 版
```

---

## 2. 役割分担

| パス | 役割 | 公開される？ |
|---|---|---|
| `public/` | ブラウザに配信する静的成果物 | **はい**（Pages 出力先） |
| `public/assets/` | CSS/JS | はい |
| `public/data/` | ダミー PredictionBundle | はい（将来 API に置換可能） |
| `functions/` | 将来の Pages Functions | 実装後 `/api/*` として |
| ルートの `*.md` | ドキュメント | GitHub 上のみ（配信されない） |

**ポイント:** ドキュメント（`*.md`）は `public/` の外に置くため、サイトには公開されない。

---

## 3. 配信 vs 非配信の境界

```text
配信（Web からアクセス可）:  public/** のみ
非配信（リポジトリのみ）:    functions/（未実装）, *.md, .gitignore
```

Cloudflare Pages の「Build output directory = `public`」により、`public/` の中身だけがサイトルート `/` に対応する。

- `https://<project>.pages.dev/`            → `public/index.html`
- `https://<project>.pages.dev/race.html`   → `public/race.html`
- `https://<project>.pages.dev/data/sample_prediction_bundle.json` → 同 JSON

---

## 4. 初回コミットに含めるもの

含める:

- `public/**`
- `functions/README.md`
- ルート `*.md`
- `.gitignore`

含めない（`.gitignore` 済み）:

- `node_modules/`, `.wrangler/`, `dist/`, エディタ設定, OS 生成物

秘密情報は無し（AI/API/DB キーを持たない構成）。

---

## 5. 推奨 Git 手順（例）

> 実際のコミットはユーザー判断で行う。以下は手順例。

```bash
cd single-10-cloudflare-deploy
git init
git add .
git commit -m "SingleAI web prototype v2 (static, Cloudflare Pages ready)"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

---

## 6. 将来 API を足すときの構成変化

```text
functions/
└─ api/
   ├─ health.js                     # /api/health
   └─ predictions/
      └─ [race_id].js               # /api/predictions/:race_id → PredictionBundle
```

- フロント側は取得先 URL を差し替えるだけ（レスポンスは PredictionBundle 契約を維持）。
- `public/data/` の静的 JSON はローカル/フォールバック用に残せる。

---

## 7. 命名・配置ルール（今後の追加時）

1. ブラウザに出すものは必ず `public/` 配下に置く。
2. サーバ処理は `functions/` 配下（`/api/*` に集約）。
3. ドキュメントはルートに置き、`public/` に混ぜない。
4. データ契約は SINGLE-07 の PredictionBundle を単一の真実とする。
