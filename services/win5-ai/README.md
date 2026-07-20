# WIN5 AI — Domain Services

ブラウザ非公開の内部 HTTP API。Cloudflare Pages Functions（BFF）からのみ呼ぶ。

## Contract

**PredictionBundle** (`single-prediction-bundle/2.0`) が共通契約。  
PredictionService は Bundle を返す。他サービスは `race_id` で参照する。

## Services

| Service | Path | Notes |
|---|---|---|
| PredictionService | `GET /v1/predictions`, `GET /v1/predictions/{id}` | 返却 = PredictionBundle |
| AnalysisService | `GET /v1/analysis/{id}` | key = Bundle.race_id |
| ConfidenceService | `GET /v1/confidence/{id}` | Bundle.ai_confidence 投影 |
| TicketService | `GET /v1/tickets/{id}` | Bundle.betting_recommendations 投影 |
| KaobaService | `POST /v1/kaoba/chat` | body.race_id = Bundle.race_id |

## 起動

```bash
cd services/win5-ai
python -m app.main
# or from repo root:
python services/win5-ai/run.py
```

環境変数: `AI_HOST`, `AI_PORT`, `AI_API_KEY`（任意・`X-AI-Key`）

モック元: `../../public/data/mocks/`
