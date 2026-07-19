# Deployment Guide — KEIBA-Single-AI

**対象:** リポジトリ直下構成の静的サイト  
**スコープ外:** AI / DB / API 実装

---

## 1. ローカル

### file://

`public/index.html` を開く（`data/sample_data.js` フォールバック）。

### HTTP

```bash
cd public
python -m http.server 8080
```

---

## 2. Cloudflare Pages

| 項目 | 値 |
|---|---|
| Root directory | （空） |
| Build command | （空） |
| Build output directory | `public` |

詳細: [`cloudflare_pages_setup.md`](./cloudflare_pages_setup.md)

---

## 3. 動作確認

| # | 操作 | 期待 |
|---|---|---|
| 1 | `/` | 開催一覧 |
| 2 | 阪神 → 11R | 詳細（印→本命→買い目→信頼度→解説） |
| 3 | `/data/sample_prediction_bundle.json` | 200 |

---

## 4. データ更新

```bash
cd public/data
python -c "import json,pathlib; p=pathlib.Path('sample_prediction_bundle.json'); pathlib.Path('sample_data.js').write_text('window.SAMPLE_PREDICTION_BUNDLE = '+json.dumps(json.loads(p.read_text(encoding='utf-8')),ensure_ascii=False,indent=2)+';\n', encoding='utf-8')"
```

---

## 5. よくある失敗

| 症状 | 原因 | 対処 |
|---|---|---|
| Output directory not found | `public/` がネストされている | 直下に `public/` を置く / Root を空に |
| 404 on pages.dev | Build output が間違っている | `public` に設定 |
| 詳細が読み込み中のまま | JSON パス不一致 | `public/data/` を確認 |
