# Challenge AI 共有実績（Benchmark）最終監査 — Version9.0 前

**Date:** 2026-07-27  
**Mode:** 調査のみ（コード変更なし）  
**Target:** `ChallengeCompareService.ai_monthly()` = Challenge「AI共有実績」  
**DB:** `/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db`  
**Sample:** `month=2026-07`（表示値 profit **-54,380** / **51R**）  
**Out of scope / 未変更:** PE / CE / AI推論 / Research / ResultAutomation / Production Logic

関連: `docs/audit/challenge-data-source-audit.md`（先行調査）

---

## 総合判定

# **WARNING**

| 観点 | 判定 | 理由 |
|------|------|------|
| Research / Canary / Validation / 285R **テーブル混入** | **PASS** | `ai_monthly` は `race_evaluations` 等を参照しない。寄与 51R はすべて `predictions.engine_source=real_ai` |
| 月次範囲 `2026-07-01`〜`2026-07-31` | **PASS** | `substr(race_date,1,7)='2026-07'`。カレンダー外リーク 0。実在データは 7/25–26 のみ |
| Production **公開済みのみ** | **FAIL** | 公開/承認ゲート列が存在せず未参照。「最新 predictions + 存在する race_results」を無条件採用 |
| 結果真正性（Netkeiba 紐づけ） | **WARNING** | 寄与 51/51 で `source=netkeiba:{YYYYMMDD…}` の日付部分が `race_date` と不一致 |

→ Version9.0 前の結論: **Research 混入による FAIL ではないが、「Production 公開実績のみ」とは認定できないため総合 WARNING。**

---

## ① `ai_monthly()` のデータソース

### データフロー図

```
Challenge API
  GET /v1/challenge/monthly?month=YYYY-MM
        │
        ▼
  app/main.py  (Handler — /v1/challenge/monthly)
        │
        ▼
  Service: ChallengeCompareService.compare()
        │
        ├─► ai_monthly(month)          ★本監査対象（共有）
        │         │
        │         ├─ list_race_ids_for_month(month)     # 同ファイル内ヘルパ（Repository クラスなし）
        │         │         │
        │         │         ▼
        │         │      SQL ──► TABLE race_results
        │         │
        │         └─ settle_ai_theory_for_race(race_id)  [各 race]
        │                   │
        │                   ├─ _load_official_result()   # app/user/service.py
        │                   │         │
        │                   │         ▼
        │                   │      SQL ──► TABLE race_results
        │                   │
        │                   ├─ latest_prediction_bundle()
        │                   │         │
        │                   │         ├─ SQL ──► TABLE predictions
        │                   │         │            (ORDER BY created_at DESC LIMIT 1)
        │                   │         └─ (miss) PI HTTP fetch_pi_prediction_bundle
        │                   │                    ※条件付き・cache INSERT あり
        │                   │
        │                   ├─ axis_rivals_from_bundle(bundle)   # 印抽出（PE 非実行）
        │                   ├─ build_purchase_snapshot(...)     # user/race_result_settle.py
        │                   └─ settle_strategy(...)             # 理論 P&L
        │
        └─► user_monthly(user_id, month)   # 個人台帳（本監査の対象外）
```

### 構成要素一覧

| 層 | 実体 | 備考 |
|----|------|------|
| **Service** | `ChallengeCompareService`（`app/challenge/service.py`） | `ai_monthly` / `compare` |
| **Repository** | **専用 Repository クラスなし** | SQL は service 内関数 + `_load_official_result` |
| **SQL（母集団）** | `SELECT race_id, race_date, venue, … FROM race_results WHERE race_date IS NOT NULL AND substr(race_date,1,7)=?` | |
| **SQL（結果）** | `SELECT * FROM race_results WHERE race_id=?` | |
| **SQL（予測）** | `SELECT bundle_json FROM predictions WHERE race_id=? ORDER BY created_at DESC, id DESC LIMIT 1` | |
| **TABLE** | `race_results`, `predictions` | |
| **VIEW** | **なし**（`sqlite_master` type=view は空） | |
| **未使用 TABLE** | `race_evaluations`, `self_evaluation_runs`, `user_race_results` | Challenge AI では不使用 |

買い目定数（理論ブック）: 馬連 / ワイド / 三連複 / 三連単 × `unit_stake=100`。

---

## ② 集計対象の分類

Challenge AI 共有実績に **含まれる / 除外される** もの（コード＋ `2026-07` 実測）。

| 分類 | 含まれるか | 根拠 |
|------|:----------:|------|
| **Production 公開レース** | △（意図未保証） | `race_results` + `real_ai` 予測を読むが **公開フラグ無し** |
| **Research** | **除外（パス）** | Research 成果テーブルへ JOIN なし。寄与メタに research keyword 0 |
| **Validation** | **除外（パス）** | 同上 |
| **Canary** | **除外（パス）** | 同上 |
| **285R 評価** | **除外（パス）** | `race_evaluations` 未使用（DB 上 baseline-like 評価は 285 件あるが Challenge 非参照） |
| **ローカル検証** | **除外（実測）** | 寄与に local/fixture/test keyword 0 |
| **Replay** | **除外（実測）** | keyword 0 |
| **Demo** | **除外（実測）** | keyword 0 |
| **Archive** | **除外（パス）** | day-archive / archive ファイルは `ai_monthly` 非参照 |
| **Mock 予測** | **除外（実測）** | `engine_source=real_ai` のみ（51/51） |

### 集計対象一覧（実測・含まれるもの）

- `race_results` のうち `substr(race_date,1,7)='2026-07'` かつ  
  settle 可能なもの（finish_order あり + 印あり Bundle + 購入額 > 0）  
- 実測 **51 レース**（全件 settle 成功、skip 0）

### 除外対象一覧

| 除外 | 理由 |
|------|------|
| Research / Validation / Canary 成果物 | 参照経路なし |
| 285R / baseline `race_evaluations` | 明示的に未使用 |
| 他月の `race_results` | SQL 月フィルタ |
| 結果未確定・印なし・購入額 0 | `settle_ai_theory_for_race` が `None` |
| ユーザー購入台帳 | `user_race_results` は User セクション専用 |

---

## ③ 月次判定（`month=2026-07`）

| 項目 | 結果 |
|------|------|
| 期間条件 | `substr(race_date, 1, 7) = '2026-07'` |
| 等価レンジ | **`race_date` が `2026-07-01`〜`2026-07-31` に入る行**（日付文字列比較で月外リーク検査も 0） |
| `race_date < 2026-07-01` または `> 2026-07-31` かつ月プレフィックス一致 | **0 件** |
| 実測 min / max | **2026-07-25** / **2026-07-26** |
| 「月初から月末の全日を必ず含む」か | **否** — DB に行がある日だけ。開催ゼロ日は母集団に出ない |

**判定:** 指定月のみを集計している（**PASS**）。ただし「7 月全日の開催」ではなく「7 月に結果が載ったレース」。

---

## ④ 指標の計算元と RaceID 追跡

### フィールド対応

| UI / API 表現 | 実際のフィールド | 計算式 | レコード単位 |
|---------------|------------------|--------|--------------|
| profit | `summary.profit` | Σ `settle_strategy.profit` | 寄与各 race |
| race_count | `summary.race_count` | settle 成功レース数 | 同上 |
| purchase | `summary.purchase_amount` | Σ `purchase_amount` | 同上 |
| hit | `summary.hit_count` | Σ (`hit`==true) | 同上 |
| hit_rate | `summary.hit_rate` | `round(hit_count / race_count * 100)` | 集計後 |
| roi | **専用キーなし** | UI が roi を出す場合は実質 **`recovery_rate`** = `round(payout/purchase*100)` | 集計後 |

`2026-07` 実測:

| 指標 | 値 |
|------|---:|
| purchase_amount | 74,900 |
| payout_amount | 20,520 |
| profit | **-54,380** |
| race_count | **51** |
| hit_count | 6 |
| recovery_rate（≒roi%） | 27 |
| hit_rate | 12 |

### RaceID 一覧（全 51・profit 内訳）

| # | race_id | race_date | profit | purchase | payout | hit | engine | result_source |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | 2026-07-25-01-01 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020101` |
| 2 | 2026-07-25-01-02 | 2026-07-25 | 4530 | 1500 | 6030 | T | real_ai | `netkeiba:202604020102` |
| 3 | 2026-07-25-01-03 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020103` |
| 4 | 2026-07-25-01-04 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020104` |
| 5 | 2026-07-25-01-05 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020105` |
| 6 | 2026-07-25-01-06 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020106` |
| 7 | 2026-07-25-01-07 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020107` |
| 8 | 2026-07-25-01-08 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020108` |
| 9 | 2026-07-25-01-09 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020109` |
| 10 | 2026-07-25-01-10 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020110` |
| 11 | 2026-07-25-01-11 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020111` |
| 12 | 2026-07-25-01-12 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020112` |
| 13 | 2026-07-25-02-01 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020101` |
| 14 | 2026-07-25-02-02 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020102` |
| 15 | 2026-07-25-02-03 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020103` |
| 16 | 2026-07-25-02-04 | 2026-07-25 | -120 | 1500 | 1380 | T | real_ai | `netkeiba:202607020104` |
| 17 | 2026-07-25-02-05 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020105` |
| 18 | 2026-07-25-02-06 | 2026-07-25 | 7790 | 1500 | 9290 | T | real_ai | `netkeiba:202607020106` |
| 19 | 2026-07-25-02-07 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020107` |
| 20 | 2026-07-25-02-08 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020108` |
| 21 | 2026-07-25-02-09 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020109` |
| 22 | 2026-07-25-02-10 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020110` |
| 23 | 2026-07-25-02-11 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020111` |
| 24 | 2026-07-25-02-12 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020112` |
| 25 | 2026-07-25-03-01 | 2026-07-25 | -940 | 1500 | 560 | T | real_ai | `netkeiba:202601010101` |
| 26 | 2026-07-25-03-02 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010102` |
| 27 | 2026-07-25-03-03 | 2026-07-25 | -920 | 1500 | 580 | T | real_ai | `netkeiba:202601010103` |
| 28 | 2026-07-25-03-04 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010104` |
| 29 | 2026-07-25-03-05 | 2026-07-25 | -700 | 700 | 0 | F | real_ai | `netkeiba:202601010105` |
| 30 | 2026-07-25-03-06 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010106` |
| 31 | 2026-07-25-03-07 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010107` |
| 32 | 2026-07-25-03-08 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010108` |
| 33 | 2026-07-25-03-09 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010109` |
| 34 | 2026-07-25-03-10 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010110` |
| 35 | 2026-07-25-03-11 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010111` |
| 36 | 2026-07-25-03-12 | 2026-07-25 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010112` |
| 37 | 2026-07-26-01-01 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020201` |
| 38 | 2026-07-26-01-02 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020202` |
| 39 | 2026-07-26-01-03 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020203` |
| 40 | 2026-07-26-01-04 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020204` |
| 41 | 2026-07-26-01-05 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202604020205` |
| 42 | 2026-07-26-02-01 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020201` |
| 43 | 2026-07-26-02-02 | 2026-07-26 | -700 | 700 | 0 | F | real_ai | `netkeiba:202607020202` |
| 44 | 2026-07-26-02-03 | 2026-07-26 | 1180 | 1500 | 2680 | T | real_ai | `netkeiba:202607020203` |
| 45 | 2026-07-26-02-04 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020204` |
| 46 | 2026-07-26-02-05 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202607020205` |
| 47 | 2026-07-26-03-01 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010201` |
| 48 | 2026-07-26-03-02 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010202` |
| 49 | 2026-07-26-03-03 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010203` |
| 50 | 2026-07-26-03-04 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010204` |
| 51 | 2026-07-26-03-05 | 2026-07-26 | -1500 | 1500 | 0 | F | real_ai | `netkeiba:202601010205` |

Σ profit = **-54,380**（表示値と一致）。

---

## ⑤ Production 公開データのみか

### 質問への回答

| 質問 | 回答 |
|------|------|
| Production 公開済みレースだけか？ | **認定できない（FAIL）** |
| Research データが混入しているか？ | **集計パス上は混入していない（PASS）** |

### 詳細

**Research 非混入（PASS）**

- `ai_monthly` → `race_evaluations` / baseline fixture / Research Scheduler 成果を読まない。
- 寄与 51R の engine/fallback/model/race_id/source に research|canary|validation|285|demo|replay 等の keyword **0**。
- DB に baseline-like `race_evaluations` が **285 件**あるが、Challenge AI 集計とは接続されていない。

**Production 公開のみ（FAIL）**

- Challenge / predictions / race_results に **published / visibility / production_only** 相当の参照が無い。
- 採用規則は「その race_id の **最新** prediction + race_results 行が settle 可能なら採用」。
- よって「ユーザー向けに公開承認された Production 実績のみ」という仕様は **コード上未実装**。

**追加 WARNING:** `result_source` の Netkeiba 数値日付が `race_date` と **51/51 不一致**（例: `race_date=2026-07-25` vs `netkeiba:20260402…`）。結果ページの取り違えがあれば理論利益も汚染される。これは Research 混入とは別系統の真正性問題。

---

## ⑥ 理想仕様との差分

| # | 理想仕様 | 現状 | 差分 |
|---|----------|------|------|
| 1 | Production **公開済み**予測のみ | 最新 `predictions` 無条件 | 公開ゲート欠如 |
| 2 | Production **確定結果**のみ | `race_results`（RA/Netkeiba） | テーブルは Production 系だが紐づけ検証不足 |
| 3 | Research/Canary/Validation/285 除外 | パス上除外 | **一致** |
| 4 | 指定カレンダー月のみ | `substr(race_date,1,7)` | **一致** |
| 5 | 共有ベンチマーク（全ユーザー同一） | `shared: true` / `ai_shared_benchmark_monthly` | **一致** |
| 6 | 結果ソースと race_date の一致 | Netkeiba numeric 日付 ≠ race_date（51/51） | **不一致（真正性）** |
| 7 | roi 明示フィールド | `recovery_rate` のみ | 命名差分 |

---

## 必須サマリ（チェックリスト）

### データフロー図

```
Challenge → Service(ChallengeCompareService.ai_monthly)
         →（Repository クラスなし / 直 SQL ヘルパ）
         → SQL
         → Table(race_results, predictions)
         →[+ optional PI on prediction miss]
```

### 集計対象一覧

- 指定月の `race_results` 行のうち、公式着順 + 予測 Bundle 印から理論買い目 settle できたレース  
- 実測 `2026-07`: 51 race_id（上表）

### 除外対象一覧

- Research / Validation / Canary / 285R evaluations / Archive ファイル / Demo / Replay / Mock（パスまたは実測）  
- 他月 race_results  
- settle 不能レース

### RaceID 一覧

- 上表 51 件（§④）

### 集計期間

- 条件: `2026-07-01`〜`2026-07-31`（`race_date` 月プレフィックス）  
- 実データ: `2026-07-25`〜`2026-07-26`

### Production のみかどうか

- Research 混入: **なし**  
- Production **公開済みのみ**: **未達（ゲートなし）**

### 総合判定

# **WARNING**

Version9.0 に進む前の推奨フォロー（調査のみ・本ドキュメントでは未実施）:

1. 公開/承認ゲートの定義と Challenge 参照の設計  
2. `race_results.source`（Netkeiba numeric）と `race_date` / `race_id` の対応検証  
3. Challenge 指標の `roi` 命名を `recovery_rate` と契約で揃える  

---

**署名:** 調査のみ。PE / CE / AI推論 / Research / ResultAutomation / Production Logic への変更は行っていない。
