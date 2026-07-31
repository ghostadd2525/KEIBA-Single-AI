# Version9.0 Release — Benchmark Layer Promotion

**Date:** 2026-07-27 (JST)  
**Status:** Production Standard 昇格 完了  
**Scope:** Feature Flag / Challenge API 形状 / Dashboard 表示ラベルのみ  
**非変更:** PE / CE / AI推論 / Prediction Logic / Research Runtime / ResultAutomation

---

## 1. 目的

Version9 Benchmark Layer（◎単勝1点）を Experimental から **Production Standard** へ昇格する。

先行監査（`docs/audit/v90-benchmark-runtime-audit.md`）の結論:

- Benchmark Layer 実装済み・検証 PASS
- 本番が旧値 **-54,380** を出していた原因は **Feature Flag OFF のみ**

---

## 2. 実施内容

| # | 項目 | 実施 |
|---|------|------|
| 1 | EC2 `V9_BENCHMARK_LAYER=true` | `/etc/expect-ai/v9-benchmark.env` + systemd drop-in `expect-ai.service.d/v9-benchmark.conf` → `daemon-reload` / `restart expect-ai` |
| 2 | Pages `V9_BENCHMARK_LAYER=true` | `wrangler.toml` `[vars]` を `"true"` |
| 3 | Cloudflare Environment 同期 | Pages 再デプロイ（vars）。secret との二重定義は解消済み |
| 4 | Challenge API 標準 = benchmark | AI `v9_benchmark_layer_enabled()` default **ON**; `compare()` → schema `2.0` / `benchmark` / `comparison.source=benchmark` |
| 5 | Challenge Dashboard | Flag ON 時 Benchmark Card 正式表示（既存 `challenge-dashboard.js`） |
| 6 | Home Dashboard | `#homeChallengeSlot` が Flag ON で「AI Benchmark（◎単勝）」表示 |
| 7 | Benchmark Strategy | Experimental → **Production Standard**（Ops JSON + AI `BENCHMARK_STRATEGY.status`） |

### 変更ファイル（要点）

- `services/win5-ai/app/challenge/service.py` — default ON / `status=production_standard`
- `wrangler.toml` — `V9_BENCHMARK_LAYER = "true"`
- `functions/api/v1/challenge/monthly.js` — BFF flag ミラー default ON
- `public/ops-data/benchmark-strategy.json` — `enabled: true`, `status: "Production Standard"`
- `public/assets/ops-console-v89.js` / `public/ops.html` — Ops カード表示
- `infra/cloudflare/env/production.env.example` — `V9_BENCHMARK_LAYER=true`
- `docs/design/v9-benchmark-layer.md` — Status 更新

### EC2

```
EnvironmentFile=-/etc/expect-ai/v9-benchmark.env   # V9_BENCHMARK_LAYER=true
```

プロセス environ に `V9_BENCHMARK_LAYER=true` を確認済み。

---

## 3. 確認結果（本番 AI / EC2 localhost）

Research Week により `https://expect-keiba.com/api/v1/challenge/monthly` は `OPS_CLOSED`（503）。  
検証は本番同一プロセス `http://127.0.0.1:8000` および `ChallengeCompareService.compare()` で実施。

| 指標 | 期待 | 実測 |
|------|------|------|
| AI利益（Benchmark） | **-2,560** | **-2560** |
| 回収率 | 約50% | **50** |
| `comparison.source` | `"benchmark"` | **`benchmark`** |
| `feature_flags.v9_benchmark_layer` | true | true |
| `schema_version` | `expect-challenge-compare/2.0` | OK |
| Ops `benchmark-strategy.json` | Production Standard | 本番 CDN で確認済み |

Rollback: AI / Pages 双方で `V9_BENCHMARK_LAYER=false`（明示 OFF）。

---

## 4. 関連ドキュメント

- 本番監査: `docs/audit/v90-benchmark-production.md`
- 昇格前 Runtime Audit: `docs/audit/v90-benchmark-runtime-audit.md`
- 設計: `docs/design/v9-benchmark-layer.md`
