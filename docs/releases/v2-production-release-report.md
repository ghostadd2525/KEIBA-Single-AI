# Version 2 — Production Release 完了レポート

**Date:** 2026-07-22  
**Status:** **Pages / BFF 本番デプロイ完了**（EC2 Core Flag は SSH 不可のため **手動フォロー要**）  
**Checklist:** [`docs/releases/v2-release-checklist.md`](./v2-release-checklist.md)  
**RC:** [`docs/releases/v2-rc-report.md`](./v2-rc-report.md)  
**本番 URL:** https://expect-keiba.com  
**Deployment:** `https://a8d47c7b.keiba-single-ai.pages.dev`（`wrangler pages deploy` · branch=main）

---

## 1. 実施した手順一覧

| # | 手順 | 結果 |
|--:|------|------|
| 1 | Checklist §0 前提（RC / Final 受領・ロールバック方針）確認 | OK |
| 2 | 本番現況確認（health / beta / AI health） | 旧 v1.1（`pi` なし · v2 Flag なし） |
| 3 | Feature Flag 切替（`config/beta.json` · `public/config/beta.json`） | 実施 |
| 4 | BFF `EXPLAIN_V2_ENABLED=true` / `EXPECT_ENV=production`（`wrangler.toml` [vars]） | 実施 |
| 5 | `npx wrangler pages deploy public --project-name=keiba-single-ai --branch=main --commit-dirty=true` | **成功** |
| 6 | Health / beta / monitor / PI / Prediction / RaceCardSummary / Dashboard / UI HTML 疎通 | 実施（下記） |
| 7 | EC2 SSH で PE / Explain Core / ops-monitor.env | **不可**（Permission denied）→ 手動手順を本レポートに記載 |
| 8 | ロールバック試験（Flag OFF 再デプロイ） | **未実施**（本番切替直後のため保持。手順は §8） |

**新機能実装:** なし（設定・デプロイ・確認のみ）。

---

## 2. デプロイ結果

| 項目 | 値 |
|------|-----|
| 手段 | Cloudflare Pages direct upload（wrangler） |
| Project | `keiba-single-ai` |
| Branch | `main` |
| Preview | https://a8d47c7b.keiba-single-ai.pages.dev |
| Production | https://expect-keiba.com |
| Exit | **0 / Success** |
| Functions | Uploaded（V2 ops / race-cards / explain 含む） |

**注意（運用）:** Pages は Git Provider 連携あり。`origin/main`（SHA `7732f06`）は V2 未追従。**Git 側の自動デプロイが走ると旧コードで上書きされる恐れがある。** V2 ツリーの commit + push、または Git 自動デプロイの一時停止を推奨。

---

## 3. Feature Flag の状態（本番反映後）

### 3.1 Web（`/config/beta.json` · 本番取得済）

| Flag | 本番値 |
|------|--------|
| `v2_race_cards` | **true** |
| `v2_race_list_ui` | **true** |
| `v2_explain` | **true** |
| `v2_ops_dashboard` | **true** |
| `v11_ops_dashboard` | **true** |
| 不採用系 `v11_*` UI | 従来どおり（mobile 等 false） |
| `v11_auto_maintenance` | true（非開催日 → OPS CLOSED） |

### 3.2 BFF（Pages vars）

| Flag | 値 |
|------|-----|
| `EXPLAIN_V2_ENABLED` | **true** |
| `EXPECT_ENV` | **production** |

### 3.3 EC2 / AI Core（**未反映・要手動**）

| Flag | 目標 | 状態 |
|------|------|------|
| `WIN5_POOL_ENTRY_V2_ENABLED` | **ON**（Accuracy 採用） | **未確認・未設定**（SSH 不可） |
| `WIN5_REPICK_V2_ENABLED` | OFF | 未確認 |
| `WIN5_CE_V2_ENABLED` | OFF | 未確認 |
| `WIN5_EXPLAIN_V2_ENABLED` | ON（Explain 段階） | **未設定と推定**（Bundle explain が 2.1 未完成形） |

#### EC2 手動手順（オペレータ）

```bash
ssh ubuntu@13.231.5.5
# PI / win5-ai の Environment に追記（実際の unit / env ファイルに合わせる）
# 例:
sudo mkdir -p /etc/expect-ai
grep -q WIN5_POOL_ENTRY_V2_ENABLED /etc/expect-ai/pi-core.env 2>/dev/null || \
  echo 'WIN5_POOL_ENTRY_V2_ENABLED=1' | sudo tee -a /etc/expect-ai/pi-core.env
# 不採用は明示 OFF
echo 'WIN5_REPICK_V2_ENABLED=0' | sudo tee -a /etc/expect-ai/pi-core.env
echo 'WIN5_CE_V2_ENABLED=0' | sudo tee -a /etc/expect-ai/pi-core.env
echo 'WIN5_EXPLAIN_V2_ENABLED=1' | sudo tee -a /etc/expect-ai/pi-core.env
# ops-monitor
sudo cp /path/to/repo/infra/aws/systemd/ops-monitor.env.example /etc/expect-ai/ops-monitor.env
# PI_HEALTH_URL=http://127.0.0.1:8081/health を確認
sudo systemctl daemon-reload
sudo systemctl restart expect-pi-keibanet-api expect-ai expect-ops-monitor.timer
```

---

## 4. Health Check 結果

### 4.1 `GET https://expect-keiba.com/api/health`

| 項目 | 結果 |
|------|------|
| HTTP | **200** |
| `data.status` | ok |
| `expect_env` | **production** |
| `ai_proxy_configured` | true |
| `pi_proxy_configured` | **true** |
| `pi.ok` / `pi.status` | **true / ok**（latency ~15–23 ms） |
| `result_automation.ok` | true |

### 4.2 Tunnel

| エンドポイント | HTTP |
|----------------|------|
| `https://ai.expect-keiba.com/health` | **200** |
| `https://ai.expect-keiba.com/v1/races?date=2026-07-25` | **200**（count=9） |
| `https://ai.expect-keiba.com/v1/predictions/2026-07-25-01-06` | **200**（prediction_available=true） |

---

## 5. Operations Dashboard

| 項目 | 結果 |
|------|------|
| `GET /api/ops/monitor` | **200** · `phase=v2-ops-phase3` · PI overall **ok** |
| `GET /api/ops/dashboard`（Admin Bearer） | データ取得可 · HTTP **503**（status=degraded） |
| `ops.html` | **200** · `opsV2Root` / Overview 含む |
| Screenshot | `fixtures/ops/v2-production-ops-dashboard.png` |

**degraded 理由:** `prediction_api` probe が win5-ai `/v1/predictions` 経路で失敗（`AI proxy returned Response`）→ ALT-E04。  
PI 単体 Prediction は Tunnel 直叩き **200**。一覧 probe はレガシー win5 経路依存の既知ギャップ（Known Limitations 系・ロールバック事由ではない）。

Slack webhook: **未設定**（no-op · Checklist 許容）。

---

## 6. 主要 API の疎通結果

| API | 条件 | HTTP | 結果 |
|-----|------|------|------|
| `/api/health` | 公開 | 200 | V2 additive `pi` OK |
| `/api/ops/public-status` | 公開 | 200 | CLOSED（非開催日 · auto_calendar） |
| `/api/ops/monitor` | 公開（key 未必須） | 200 | V2 phase3 集約 OK |
| `/api/predictions/{id}` | 未認証 | 503 | OPS_CLOSED（想定） |
| `/api/predictions/{id}` | **Admin Bearer** | **200** | Bundle 2.0 · `engine_source=pi` |
| `/api/race-cards?date=` | 未認証 | 503 | OPS_CLOSED（想定） |
| `/api/race-cards?date=` | **Admin Bearer** | **200** | `expect-race-card-summary/1.0` · 9 件 |
| `/api/ops/dashboard` | Admin | 503 body ok | phase3 · PI ok · degraded |
| PI `/v1/predictions/{id}` | Tunnel | **200** | Prediction OK |
| `races.html` / `ops.html` | 静的 | 200 | V2 UI コード配信 |

### RaceCardSummary

- `schema_version`: `expect-race-card-summary/1.0`
- `summary`: honmei / confidence / short_reason あり
- 契約破壊フィールド追加なし（確認）

### Explainability

- BFF 応答に `explain` オブジェクトあり（`reasons` / `narrative` / `meta`）
- `single-explain/2.1` の `decision_key` 等は **未確認** → Core `WIN5_EXPLAIN_V2_ENABLED` が EC2 で未 ON の可能性が高い
- Web `v2_explain=true` は beta 反映済

### UI

- `races.html` に `raceCardSummaryHtml` / `v2_race_list_ui` 経路あり
- `ops.html` に Phase3 Overview / Inventory あり
- 非開催日のため一般ユーザー API は CLOSED（v1.1 自動メンテ継続）

---

## 7. 問題の有無

| 深刻度 | 内容 | 対応 |
|--------|------|------|
| **要対応（手動）** | EC2 SSH 不可のため Accuracy PE / Core Explain Flag 未設定 | §3.3 手順をオペレータ実施 |
| **要対応（運用）** | Git `main` が V2 未追従 · 自動デプロイ上書きリスク | V2 commit/push または Git deploy 停止 |
| **低（監視）** | `/api/ops/monitor` の `prediction_api` probe degraded（win5 一覧） | PI 直 Prediction は健全。probe 改善は後続（新機能禁止のため今回触らず） |
| **情報** | 非開催日 OPS CLOSED | Checklist / v1.1 仕様どおり。Admin bypass で確認済 |
| **情報** | Slack webhook 未設定 | no-op · 任意 Secrets |

**ロールバック:** 実施せず（Pages デプロイは成功し、致命的障害なし）。

### ロールバック手順（必要時）

1. `beta.json` の `v2_*` / `v11_ops_dashboard` を false に戻し再デプロイ  
2. `EXPLAIN_V2_ENABLED` を false（または vars 削除）で再デプロイ  
3. EC2 で `WIN5_POOL_ENTRY_V2_ENABLED=0` 等を戻し unit 再起動  

---

## 8. Checklist 消化状況

| 節 | 判定 |
|----|------|
| 0 前提 | **済** |
| 1 互換性 | **済**（Bundle 2.0 / PI / RaceCardSummary / Flag 配信確認） |
| 2 Accuracy EC2 | **一部未了**（SSH 待ち） |
| 3 UI | **済**（Flag ON · HTML 配信 · API Admin 確認） |
| 4 Explain | **一部未了**（Web/BFF ON · Core EC2 待ち） |
| 5 Operations | **済**（Dashboard/monitor/health · Slack 任意未設定） |
| 6 セキュリティ | **済**（dashboard 未認証は拒否系 · admin で取得） |
| 7 監視直後 | **済**（ALT-E04 観測 · health.pi OK） |
| 8 コミュニケーション | 本レポートで代替 |
| 9 Go/No-Go | **条件付き GO**（Pages/BFF GO · EC2 Flag はフォロー） |

---

## 9. 結論

Version 2 の **Cloudflare Pages / BFF 本番リリースは完了**した。

- Feature Flag（Web + BFF Explain）は本番 ON  
- Health / PI Probe（BFF）/ Ops Dashboard / RaceCardSummary / Prediction（Admin）を確認  
- **残作業:** EC2 上の Accuracy PE + Core Explain Flag、および Git main 同期  

**新機能追加は行っていない。**
