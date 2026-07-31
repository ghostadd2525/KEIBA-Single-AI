# Version9.0 Audit — Benchmark Layer Production

**Date:** 2026-07-27 (JST)  
**Type:** Promotion verification（Production Standard）  
**前段:** `docs/audit/v90-benchmark-runtime-audit.md`（Flag OFF が旧 -54,380 の一次原因）

---

## 0. Verdict

| 項目 | 結果 |
|------|------|
| EC2 Flag | **PASS** — process `V9_BENCHMARK_LAYER=true` |
| Pages Flag | **PASS** — `wrangler.toml` `"true"` + 再デプロイ |
| Challenge API（本番 AI） | **PASS** — profit **-2560** / recovery **50** / `source=benchmark` |
| Ops Strategy 表示 | **PASS** — `status: "Production Standard"`, `enabled: true` |
| PE / CE / RA / Research Runtime | **未変更** |

公開 Origin の Challenge BFF は Research Week `OPS_CLOSED` のため未経由。AI 層は本番プロセスで確認。

---

## 1. Feature Flag（昇格後）

| 層 | `V9_BENCHMARK_LAYER` | 根拠 |
|----|----------------------|------|
| AI（EC2 process） | **`true`** | `/proc/<MainPID>/environ` |
| AI systemd | **設定済** | `/etc/expect-ai/v9-benchmark.env` + `expect-ai.service.d/v9-benchmark.conf` |
| Pages `wrangler.toml` [vars] | **`"true"`** | リポジトリ |
| Cloudflare Pages Secrets | **未登録（意図的）** | vars と secret の二重定義を回避。`AI_BASE_URL` / `PI_BASE_URL` のみ |
| AI default（unset） | **ON** | `v9_benchmark_layer_enabled()` |
| BFF default（unset） | **ON** | `functions/api/v1/challenge/monthly.js` `flagOn()` |

---

## 2. API 実測（2026-07 / EC2）

### 2.1 HTTP `GET /v1/challenge/monthly?month=2026-07`

```json
{
  "ok": true,
  "schema": "expect-challenge-compare/2.0",
  "flags": { "v9_benchmark_layer": true },
  "source": "benchmark",
  "profit": -2560,
  "recovery": 50
}
```

### 2.2 `ChallengeCompareService.compare()`

| フィールド | 値 |
|------------|-----|
| `schema_version` | `expect-challenge-compare/2.0` |
| `feature_flags.v9_benchmark_layer` | true |
| `comparison.source` | **`benchmark`** |
| `benchmark.summary.profit` | **-2560** |
| `benchmark.summary.recovery_rate` | **50** |
| `benchmark.summary.purchase_amount` | 5100 |
| `benchmark.summary.payout_amount` | 2540 |
| `benchmark` / `purchase_lab` | キーあり |

判定スクリプト: EC2 `/tmp/v90-verify.py` → **PASS**

---

## 3. UI / Ops

| 面 | 状態 |
|----|------|
| Challenge Dashboard | Flag ON で「AI Benchmark（◎単勝1点）」主カード + Purchase Lab 折りたたみ |
| Home `#homeChallengeSlot` | Flag ON で Benchmark キッカー |
| Ops Benchmark Strategy カード | `Production Standard` / flag=ON |
| 本番 CDN `ops-data/benchmark-strategy.json` | `enabled: true`, `status: "Production Standard"` |

---

## 4. 公開 Origin 注記

| 経路 | 結果 |
|------|------|
| `https://expect-keiba.com/api/v1/challenge/monthly` | **503 `OPS_CLOSED`**（Research Week） |
| `https://expect-keiba.com/ops-data/benchmark-strategy.json` | **200** Production Standard |

OPS 再開後は BFF 経由でも同一 AI ペイロードが返る想定（AI Flag ON 済み）。

---

## 5. 差分サマリ（昇格前後）

| | 昇格前 | 昇格後 |
|--|--------|--------|
| AI利益表示根拠 | 4券種 legacy `-54380` | ◎単勝 Benchmark `-2560` |
| `comparison.source` | `ai_legacy_book` | `benchmark` |
| Strategy status | Experimental / Flag OFF | **Production Standard** / Flag ON |

---

## 6. Rollback

1. EC2: `/etc/expect-ai/v9-benchmark.env` を `V9_BENCHMARK_LAYER=false` → `systemctl restart expect-ai`
2. Pages: `wrangler.toml` を `"false"` → `npm run deploy:pages`
3. 期待: schema `1.1` / profit `-54380` / `source=ai_legacy_book`
