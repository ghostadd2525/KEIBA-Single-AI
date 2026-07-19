# GitHub Structure — KEIBA-Single-AI

**方針:** リポジトリ直下 = Cloudflare Pages の Root。  
**廃止:** `single-10-cloudflare-deploy/` などのネストは使わない。

---

## 1. ルート構成

```text
KEIBA-Single-AI/                 # GitHub リポジトリ Root
├─ public/                       # 公開物（Pages Build output）
│  ├─ index.html
│  ├─ race.html
│  ├─ assets/
│  │  ├─ styles.css
│  │  └─ app.js
│  ├─ data/
│  │  ├─ sample_prediction_bundle.json
│  │  └─ sample_data.js
│  ├─ _headers
│  └─ _redirects
├─ functions/
│  └─ README.md                  # 将来 API 用（現在は文書のみ）
├─ .gitignore
├─ README.md
├─ deployment_guide.md
├─ github_structure.md
└─ cloudflare_pages_setup.md
```

---

## 2. 配信 vs 非配信

| パス | 公開される？ |
|---|---|
| `public/**` | **はい**（サイトの `/` に対応） |
| `functions/` | 実装後に `/api/*` |
| ルート `*.md` | GitHub 上のみ（サイトには出ない） |

---

## 3. Cloudflare Pages との対応

| Pages 設定 | 値 |
|---|---|
| Root directory | （空） |
| Build output directory | `public` |
| Build command | （空） |

```text
https://keiba-single-ai.pages.dev/          → public/index.html
https://keiba-single-ai.pages.dev/race.html → public/race.html
https://keiba-single-ai.pages.dev/data/...  → public/data/...
```

---

## 4. 誤った構成（避ける）

```text
KEIBA-Single-AI/
└── single-10-cloudflare-deploy/   ← ネスト禁止
    └── public/
```

この場合 Root directory を空にすると `public/` が見つからずデプロイ失敗する。  
必ず **リポジトリ直下に `public/`** を置く。
