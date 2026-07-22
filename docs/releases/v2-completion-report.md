# Version 2 Completion Report

**Date:** 2026-07-22  
**Status:** **COMPLETE** — EC2 Core 残課題 + Git `main` ≡ Production  
**Git SHA (main / Production Pages):** `03e7a4f57bfe18a7d3fd7f6e6d7daff044230dd4`  
**Pages Deployment:** `https://66913935.keiba-single-ai.pages.dev`（Source=`03e7a4f` · branch=`main`）  
**本番:** https://expect-keiba.com  

本レポートは Version 2 残課題（EC2 Core 設定 / Git 運用整理）のみを対象とする。新機能追加なし。

---

## 1. EC2 設定反映結果

| 項目 | 結果 |
|------|------|
| SSH | **復旧・確認済**（`ubuntu@13.231.5.5` · PEM `expect-beta-tokyo.pem`） |
| Host | `ip-172-31-40-147` |
| `expect-pi-keibanet-api` | **active** |
| `expect-ai` | **active**（overlay 権限修正後） |
| Core env ファイル | `/etc/expect-ai/pi-core.env` 作成 |
| systemd | 両 unit に `EnvironmentFile=-/etc/expect-ai/pi-core.env` |
| PE-V2-A モジュール | `/opt/expect-ai/platform/v2_pool_entry_v2.py` 配置 |
| PE hook | `demo_ticket_optimizer_core.py` に Flag 読込 + `apply_win5_pool_entry_v2` 挿入 |
| Core Explain | `ai_platform/core/explain/` + `candidate_evaluation` explain 配線を platform / repo overlay へ反映 |
| PI pass-through | `pi_keibanet/service.py` に `explain_payload` 加算パススルー反映 |

### SSH 接続確認

```text
ssh -i expect-beta-tokyo.pem ubuntu@13.231.5.5
→ hostname=ip-172-31-40-147 / user=ubuntu / SSH_OK
```

---

## 2. 環境変数一覧（追加・変更分）

**ファイル:** `/etc/expect-ai/pi-core.env`（新規）  
**適用先:** `expect-pi-keibanet-api` · `expect-ai`（プロセス environ で確認済）

| 変数 | 値 | 備考 |
|------|----|------|
| `WIN5_POOL_ENTRY_V2_ENABLED` | **1** | Accuracy 採用構成 ON（新規） |
| `WIN5_REPICK_V2_ENABLED` | **0** | 不採用・明示 OFF（新規） |
| `WIN5_CE_V2_ENABLED` | **0** | 不採用・明示 OFF（新規） |
| `WIN5_EXPLAIN_V2_ENABLED` | **1** | Core Explain ON（新規） |
| `EXPLAIN_V2_ENABLED` | **1** | PI → BFF pass-through ON（新規） |

リポジトリ例: `infra/aws/systemd/pi-core.env.example`

**変更しないもの（維持）:** Prediction API 契約 · RaceCardSummary 契約 · Feature 追加なし · RP/CE ロジック採用なし

---

## 3. Health / Prediction / Explain 確認

### Health

| エンドポイント | HTTP | 結果 |
|----------------|------|------|
| `GET https://expect-keiba.com/api/health` | **200** | `expect_env=production` · `pi.ok=true` |
| `GET http://127.0.0.1:8081/health`（EC2） | **200** | `pi-keibanet-api` ok |
| `GET http://127.0.0.1:8000/health`（EC2） | **200** | expect-ai ok |

### Prediction API

| エンドポイント | HTTP | 結果 |
|----------------|------|------|
| `GET http://127.0.0.1:8081/v1/predictions/2026-07-25-01-06` | **200** | `prediction_available=true` · candidates>0 |
| `GET https://ai.expect-keiba.com/v1/predictions/2026-07-25-01-06` | **200** | 同上 |
| `GET /api/predictions/{id}`（未認証） | **503** | `OPS_CLOSED`（非開催日 · 想定） |
| `GET /api/predictions/{id}`（Admin Bearer） | **200** | Bundle 2.0 · explain 付き |

### Explain API（Bundle.explain / Core payload）

| 層 | 結果 |
|----|------|
| Core `explain_payload` | **あり** · `schema_version=core-explain-payload/1.0` |
| PI Prediction JSON | **`explain_payload` 同梱**（Tunnel でも確認） |
| BFF Bundle `explain` | **`single-explain/2.1`** · `meta.explain_source=core-explain-payload/1.0` · `explain_phase=1` |

---

## 4. Git main 同期結果

| 項目 | 値 |
|------|-----|
| 旧 `origin/main` | `7732f06`（V2 未追従 · 自動デプロイ上書きリスクあり） |
| 新 `origin/main` | **`03e7a4f`** `Release Version 2 to main for production parity.` |
| 差分規模 | 225 files · +39108 / −307 |
| ローカル | `main...origin/main`（ahead/behind なし） |

### Production と main が一致している証跡

1. **Git:** `git rev-parse HEAD` = `git rev-parse origin/main` = `03e7a4f57bfe18a7d3fd7f6e6d7daff044230dd4`
2. **Cloudflare Pages:** Production 最新 Deployment Source = **`03e7a4f`** · Branch = **`main`** · URL `https://66913935.keiba-single-ai.pages.dev`
3. **Live flags:** `/config/beta.json` の `v2_race_cards` / `v2_race_list_ui` / `v2_explain` / `v2_ops_dashboard` / `v11_ops_dashboard` がすべて **true**（main の本番設定と一致）
4. **自動デプロイ:** push 直後に Pages が `03e7a4f` を Production へ取り込み → **今後の Git 自動デプロイは V2 main を配信し、V1（7732f06）へ戻らない**

---

## 5. Version 2 最終構成（本番）

```text
Pages / BFF (main = 03e7a4f)
├─ Web Flags: v2_race_cards / v2_race_list_ui / v2_explain / v2_ops_dashboard ON
├─ BFF: EXPECT_ENV=production · EXPLAIN_V2_ENABLED=true
└─ EC2 Core
   ├─ WIN5_POOL_ENTRY_V2_ENABLED=1   【Accuracy 採用】
   ├─ WIN5_REPICK_V2_ENABLED=0       【不採用】
   ├─ WIN5_CE_V2_ENABLED=0           【不採用】
   └─ WIN5_EXPLAIN_V2_ENABLED=1 + EXPLAIN_V2_ENABLED=1
```

---

## 6. 残課題クローズ判定

| 残課題 | 判定 |
|--------|------|
| ① EC2 Core 設定（SSH / PE / Explain / 疎通） | **完了** |
| ② Git main ≡ Production · V1 自動戻し防止 | **完了** |

**Version 2 は Production と main が一致したため、本トラックはここで停止する。**
