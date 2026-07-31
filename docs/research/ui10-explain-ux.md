# UI10 — Explain UX Improvement

実装リポジトリ: `C:\win5-ai\KEIBA-Single-AI`  
ミラー詳細: 本ファイルと同趣旨。検証は `docs/research/artifacts/ui10/`。

## 変更点

- 旧 explain 長文テンプレを UI から除去
- 4ブロック（状況 / ◎理由 / 買いポイント / 見立て）を構造化データから組立
- Client: `explain-ux.js` / BFF: `explainUxComposer.js`

## 検証

3レース fingerprint 一意・旧「を◎にしたのは、AI予測では1番手で…」非含有 → PASS
