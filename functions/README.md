# functions/ — 将来 API 用プレースホルダー（現在は空）

このディレクトリは **Cloudflare Pages Functions** の予約枠です。  
**現段階では API を実装しません**（AI / DB / API はスコープ外）。

## 将来ここに置くもの（設計メモのみ）

Cloudflare Pages では `functions/` 配下のファイルが自動で URL ルートにマッピングされます。

| 予定ファイル | ルート | 役割（将来） |
|---|---|---|
| `functions/api/health.js` | `/api/health` | 疎通確認 |
| `functions/api/predictions/[race_id].js` | `/api/predictions/:race_id` | PredictionBundle を返す |

## 移行方針（実装時）

- フロントの `loadPredictionBundle()` の取得先を  
  `data/sample_prediction_bundle.json` → `/api/predictions/{race_id}` に切り替えるだけで済むよう、  
  レスポンス形状は **PredictionBundle（SINGLE-07 契約）** を維持する。
- 静的フォールバック（`data/sample_data.js`）はローカル/オフライン用に残せる。

現時点ではコードを置かないこと。ディレクトリの存在意義を示すための文書のみ。
