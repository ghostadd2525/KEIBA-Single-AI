# Version10 Audit — Evidence Harvest Validation

**Date:** 2026-07-27 (JST)  
**Type:** Read-only harvest proof（コード変更なし）  
**Question:** Evidence Collection Platform は Prediction Snapshot を **実際に収集・保存** できているか

---

## 0. 最終判定（Production / EC2）

| 項目 | 実測 | 判定 |
|------|------|------|
| Prediction 件数 | **58** | — |
| Snapshot 件数 | **0** | **FAIL** |
| Evidence JSON ファイル | **0** | **FAIL** |
| Migration `011_research_evidence` | **未適用** | **FAIL** |
| Research コード EC2 配置 | **なし** | **FAIL** |
| Collector プロセス | **未起動** | **FAIL** |
| Anti-Leak 違反 | **0**（Snapshot 無しのため N/A） | — |

**総合 Verdict: Harvest 未成立（Platform 実装済み・本番未デプロイ / 未稼働）**

Feature 別判定（本番実測）:

| Feature | 取得件数 | Coverage | Missing | Verdict |
|---------|----------|----------|---------|---------|
| 人気 | 0 | 0% | 100% | **FAILED** |
| 単勝オッズ | 0 | 0% | 100% | **FAILED** |
| 想定人気 | 0 | 0% | 100% | **FAILED** |
| 厩舎 | 0 | 0% | 100% | **FAILED** |

---

## 1. 検証方法

| 環境 | 手段 |
|------|------|
| EC2 本番 AI DB | `expect_ai.db` 読取専用 SQL + ファイルシステム走査 |
| ローカル Dev DB | migration 011 適用後の状態確認 + Collector `--once` 試行 |
| コード | 変更なし |

Hard Lock 確認: PE / CE / AI / Prediction Logic / RA / Challenge / Research Runtime — **監査中に未変更**。

---

## 2. EC2 Production 実測

### 2.1 DB / Store

| 指標 | 値 |
|------|-----|
| DB | `/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db` |
| `predictions` | **58** |
| `research_prediction_snapshots` | **テーブル不存在**（011 未適用） |
| `research_collect_jobs` | **テーブル不存在** |
| JSON store | `evidence/research/prediction-snapshots/` — **0 files** |

### 2.2 Migration

適用済み: `001`〜`010`  
**未適用:** `011_research_evidence`

### 2.3 コード / 運用

| 項目 | EC2 |
|------|-----|
| `app/research/collector_runner.py` | **不存在** |
| `011_research_evidence.sql` | **不存在** |
| `RESEARCH_EVIDENCE_COLLECTOR` | unset |
| `PI_BASE_URL` / `EXPECT_KEIBANET_BASE_URL` | unset（プロセス environ） |
| `GET /v1/admin/research/evidence/monitoring` | **404** |
| Collector プロセス | **なし** |

### 2.4 直近 Prediction サンプル

| prediction_id | race_id | created_at |
|---------------|---------|------------|
| 58 | 2026-07-26-03-05 | 2026-07-26T03:30:59Z |
| 57 | 2026-07-26-03-04 | 2026-07-26T03:01:07Z |
| 56 | 2026-07-26-02-05 | 2026-07-26T03:01:05Z |

→ **58 件すべて Snapshot 未収集**

---

## 3. Feature 別詳細（本番）

Harvest 未成立のため、以下は **実測 0**（理論値ではなく DB/JSON 走査結果）。

| # | Feature | ①取得件数 | ②Coverage | ③Missing | ④Source | ⑤ObservedAt | ⑥pred.created_at | ⑦Anti-Leak | ⑧Missing理由 |
|---|---------|-----------|-----------|----------|---------|-------------|------------------|------------|--------------|
| 1 | 人気 | 0 | 0% | 100% | — | — | — | 0 | — |
| 2 | 単勝オッズ | 0 | 0% | 100% | — | — | — | 0 | — |
| 3 | 想定人気 | 0 | 0% | 100% | — | — | — | 0 | — |
| 4 | 厩舎 | 0 | 0% | 100% | — | — | — | 0 | — |

### Source マッピング（設計上・収集成功時）

| Feature | 取得元 |
|---------|--------|
| 人気 / 単勝 | **JRA** odds API `type=1` → **PI** `/v1/races/{race_id}/board` |
| 想定人気 | **PI** 派生（単勝ソート） |
| 厩舎 | **Netkeiba** shutuba → **PI** `entries_full.trainer` |

既存DB（`predictions` / `entries`）からの Snapshot コピーは Phase1 では **未使用**（外部ソース取得のみ）。

---

## 4. ローカル Dev 参考（Harvest 試行）

| 項目 | 値 |
|------|-----|
| Migration 011 | **適用済**（検証用 `migrate()` のみ） |
| predictions | 1 |
| snapshots | **0** |
| Collector `--once` | job **failed** — `PI_BASE_URL unset` |
| JSON files | 0 |

→ ローカルでも **Feature 実データ Harvest 未達**（PI 未設定）。  
Collector **enqueue 自体は動作**（`research_collect_jobs` に failed 1 件）。

---

## 5. 二次証拠（オフライン・実 Harvest ではない）

| 証拠 | 内容 |
|------|------|
| 単体テスト | `tests/research/test_v10_evidence_platform.py` — mock board で 4 Feature 取得成功 |
| 設計 | `docs/design/v10-evidence-collection-platform.md` |

**注意:** 単体テストは Collector **ロジック** の証明であり、本番 Harvest の証明にはならない。

---

## 6. 根因

1. V10 Research 実装が **EC2 に未デプロイ**（`app/research/` 不存在）  
2. Migration **011 未適用** → Research Store 未作成  
3. Collector サイドカー **未起動** / PI URL 未設定  
4. よって **Prediction 58 件に対し Snapshot 0 件**

---

## 7. Harvest 成立のための必要条件（参考・実装以外）

1. EC2 へ `app/research/` + `011_research_evidence.sql` デプロイ  
2. `expect-ai` 再起動（migrate 自動適用）  
3. `PI_BASE_URL` 設定 + Collector `--loop` 常駐  
4. 再監査: `snapshots_total > 0` かつ Feature coverage > 0%

---

## 8. 成果物

| ファイル | 内容 |
|----------|------|
| 本ファイル | Harvest 実測監査 |
| `docs/audit/v10-evidence-coverage.csv` | Feature × Production カバレッジ（全 FAILED） |

---

## 9. 変更境界

| 領域 | 本監査 |
|------|--------|
| プロダクトコード | **未変更** |
| EC2 DB | **読取のみ** |
| ローカル | migration 適用 + collector 試行（Harvest 証明用・本番非影響） |

---

## 10. 参照

- `docs/design/v10-evidence-collection-platform.md`
- `docs/audit/v10-evidence-validation.md`
- EC2 probe: `/tmp/v10-harvest-probe.py`（2026-07-27 実行）
