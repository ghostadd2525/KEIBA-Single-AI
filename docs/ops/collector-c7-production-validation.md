# Collector C-7 — Production Validation Report

**Date:** 2026-07-20  
**Scope:** Production Validation only（Collector 仕様変更なし）  
**Evidence:** `services/win5-ai/tests/ops/test_collect_c7.py`  
**Result summary:** Controlled validation **PASS** / Real KeibaNet **BLOCKED（未接続）**

---

## 0. 結論

Collector 基盤は、モック KeibaNet 上では **取得成功・失敗・予算・Manifest・Prediction 非影響・性能** を設計どおり検証できた。

ただし **実 KeibaNet エンドポイントが環境に未設定**（`EXPECT_KEIBANET_BASE_URL` unset）のため、本番 Go-Live 判定は **保留**。実接続検証完了を Must とする。

| 観点 | 判定 |
|------|------|
| Artifact 成功（4種） | PASS（controlled） |
| Failure（429/500/Timeout/NULL/Partial） | PASS（controlled） |
| Budget（daily_limit / remaining / stop） | PASS |
| Manifest 整合（Planner→Scheduler→Gate→OPS） | PASS |
| Prediction 不変 | PASS（mock engine） |
| Performance（局所） | PASS（問題なし） |
| Real KeibaNet | **BLOCKED** |

---

## ① Real KeibaNet Validation

| 項目 | 結果 |
|------|------|
| `EXPECT_KEIBANET_BASE_URL` | **未設定** |
| race_meta / entries_core / odds / track 実取得 | **未実施** |
| Rate Limit / Retry / Timeout（実網） | **未実施** |

Controlled mock では同一パス契約で 4 artifact すべて `READY` を確認:

| artifact | status | elapsed_ms（目安） |
|----------|--------|-------------------|
| race_meta | READY | ~43 |
| entries_core | READY | ~47 |
| odds | READY | ~26 |
| track | READY | ~57 |

**運用リスク:** 実 API のスキーマ差・認証・会場名・日付フォーマット差は未検証。

---

## ② Budget Validation

想定: 週末 72R（race_meta のみ）・`daily_limit=150`。

| 観測 | 結果 |
|------|------|
| `daily_limit=20` で dequeue 停止 | PASS（20件で `remaining=0`、追加 0） |
| 翌日以降で残り消化 | PASS（52件消化→PENDING 0） |
| `used` / `remaining` 整合 | PASS |

**運用で問題になりそうな点**

1. **Planner は全ジョブを同一 `scheduled_for` に寄せる**ため、「月〜金へ自然分散」は Budget 停止に依存。分散スケジューリング自体は未実装。
2. **予算が二重**: `CollectBudget`（ジョブ dequeue）と `KeibaNetClient` 内部 `_DailyBudget`（HTTP）。既定値も別（150 vs 200）。ズレると「ジョブは取れたが HTTP 拒否」が起きうる。

---

## ③ Manifest Validation

フロー: Planner → Collect → Scheduler.finish → Friday Gate → OPS Monitor

| チェック | 結果 |
|----------|------|
| Planner 初期 `status.*=false` | PASS |
| Scheduler が `prediction_ready` を確定しない | PASS |
| Friday Gate が Prediction Ready 正本 | PASS |
| OPS `state` が Manifest と一致 | PASS（`PREDICTION_READY`） |
| `dynamic_*` と Prediction 軸の独立 | PASS |
| schema `assert_valid_manifest` | PASS |

---

## ④ Failure Validation

| シナリオ | 期待 | 実測 | 判定 |
|----------|------|------|------|
| HTTP 429 | Client retry → 最終 FAILED | retry≥3 → FAILED | PASS |
| HTTP 500 | Client retry → 最終 FAILED | retry≥3 → FAILED | PASS |
| Timeout | FAILED | FAILED（~346ms @ timeout 0.3s） | PASS |
| NULL Response (`null`) | PARTIAL | PARTIAL | PASS |
| Partial Response（必須 NULL） | PARTIAL | PARTIAL | PASS |
| Retry（CollectRetry） | FAILED/PARTIAL → PENDING | **retry_after 必須** | **GAP** |

### 重要ギャップ: Retry 自動再投入

- `KeibaNetClient` は 429/5xx の **トランスポート再試行**を行う。
- `CollectRetry` は `retry_after` がセットされた PARTIAL/FAILED のみ PENDING に戻す。
- **Collector は FAILED/PARTIAL 時に `retry_after` を自動設定しない。**

→ 現状のままでは「失敗後のジョブ再投入」は **人手 or 外部オーケストレーション必須**。

---

## ⑤ Prediction Validation

Collector → Raw → `ingest_ready_race_meta` 前後で mock Prediction シグネチャ比較:

```
before: engine=mock, top=[7, 3, 12]
after:  engine=mock, top=[7, 3, 12]
```

**一致（PASS）**。Prediction / FeatureLoader / LightGBM は未変更。

※ real AI engine は本 C-7 ではスキップ（C-3 と同様、環境依存）。

---

## ⑥ Performance Validation（controlled・局所）

| 工程 | ms（実測） |
|------|-----------|
| Planner | ~39 |
| dequeue | ~1 |
| fetch avg / max | ~38 / ~53 |
| Raw list | ~0.4 |
| SQLite ETL | ~27 |
| Manifest update | ~12 |
| Retry process | ~8 |

局所モックではボトルネックなし。実 KeibaNet + 72〜200 req/日 + `min_interval` 下では **ネットワークと間隔**が支配的になる想定。

---

## ⑦ 運用で問題になりそうな点

1. **実 KeibaNet 未検証** — Go-Live ブロッカー  
2. **`retry_after` 未自動設定** — 失敗ジョブが PENDING に戻らない  
3. **二重 Budget** — Collect と Client の limit 不整合リスク  
4. **平日分散は Budget 頼み** — `scheduled_for` 分散ロジックなし  
5. **HTTPError ResourceWarning**（テスト上）— 本番でも接続クローズ漏れに注意  
6. **Timeout 後のサーバ側処理** — クライアント切断後もサーバが書き込み続ける可能性（ログノイズ）  
7. **Complete Ready** — odds/track 未取得のまま Prediction Ready 運用は設計どおりだが、監視で取り違えやすい  

---

## Must / Should / Nice to Have

### Must（本番投入前）

1. `EXPECT_KEIBANET_BASE_URL` を設定し、**実 KeibaNet で 4 artifact（成功/失敗/429/Timeout）を再検証**  
2. ~~FAILED/PARTIAL 時に `retry_after` を自動設定~~ → **C-8 で解消**  
3. ~~Collect Budget と KeibaNet Client Budget の単一の正本~~ → **C-8 で解消**  
4. 週末規模（〜72R×必須 artifact）での **実測レート制限**確認（Real KeibaNet 前提）  

### Should

1. ~~Planner の `scheduled_for` 平日分散~~ → **C-8 で解消**  
2. OPS Monitor に `retry_after` 未設定 FAILED 件数アラート（防御的）  
3. Manifest / OPS に「Prediction軸」と「DYNAMIC軸」の表示を運用ダッシュボードで分離  
4. 実エンジンでの Prediction 不変確認（mock 以外）  

### Nice to Have

1. 取得レイテンシの週次ベースライン保存  
2. Raw Store 容量・世代管理ポリシー  
3. HTTP 429 の `Retry-After` ヘッダ尊重  
4. C-7 検証結果の自動レポート出力（JSON → OPS）  

---

## 設計との差分（C-7）

| 設計（dispersion C-7） | 本フェーズ |
|------------------------|------------|
| OPS-Monitor Manifest 連携（本番拡張） | Manifest↔OPS 整合は検証済み。本番ダッシュボード連携は未着手 |
| 土日 DYNAMIC 本番運用 | Contract/Scheduler は C-6 済。実網 DYNAMIC は未検証 |

**本フェーズでコード改善は最小**（検証テスト `test_collect_c7.py` と本レポートのみ）。Collector 本体仕様は変更していない。

---

## 再現手順

```bash
cd services/win5-ai
python -m unittest tests.ops.test_collect_c7 -v

# Real KeibaNet（接続可能時）
set EXPECT_KEIBANET_BASE_URL=https://<keibanet-host>
python -m unittest tests.ops.test_collect_c7.RealKeibaNetProbeTest -v
```

---

## Go-Live 判定

| 判定 | 条件 |
|------|------|
| **条件付き PASS（基盤）** | Controlled validation すべて PASS |
| **本番 Go-Live** | Must ①〜④ 完了後に再判定 |
