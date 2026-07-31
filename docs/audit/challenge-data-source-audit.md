# Challenge AI 実績 — データソース監査

**Date:** 2026-07-27  
**Scope:** `ChallengeCompareService.ai_monthly()` の集計元のみ（**コード修正なし**）  
**Environment:** Production AI SQLite ` /home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db `  
**Sample month:** `2026-07`（UI「今月」／実測 profit **-54,380** / **51R**）

---

## 結論（要約）

| 問い | 判定 |
|------|------|
| 参照テーブル | **`race_results` + `predictions`（＋不足時 PI bundle 取得）**。ビューなし。`race_evaluations` / 285 baseline **未使用** |
| 期間 | **指定月 `YYYY-MM` の `race_date` のみ**（`substr(race_date,1,7)=month`） |
| Research / Canary / Validation / 285R の混在 | **集計パス上は未参照**。寄与 51R はすべて `engine_source=real_ai` |
| UI「今月」との一致 | **API の `month` パラメータと一致**。ただし中身は「その月に `race_results` がある日」だけ（現状 7/25・7/26） |
| あるべきソースとの差分 | **Production 結果＋最新予測の理論 settle**。**「ユーザー公開済みのみ」ゲートは無い**。加えて `race_results.source` の Netkeiba 数値 ID 日付が `race_date` と不一致（データ整合リスク） |

---

## 1. `ai_monthly()` が参照しているテーブル・ビュー

### コード経路

```
ai_monthly(month)
  └─ list_race_ids_for_month(month)
       └─ SELECT … FROM race_results
            WHERE substr(race_date,1,7)=?
  └─ settle_ai_theory_for_race(race_id)  [各行]
       ├─ _load_official_result(race_id)
       │    └─ SELECT * FROM race_results WHERE race_id=?
       │         → result_json.finish_order / payouts
       ├─ latest_prediction_bundle(race_id)
       │    ├─ SELECT bundle_json FROM predictions
       │    │    WHERE race_id=? ORDER BY created_at DESC LIMIT 1
       │    └─ (miss 時) fetch_pi_prediction_bundle(race_id) → 任意で predictions へ cache INSERT
       ├─ axis_rivals_from_bundle(bundle)   # ◎○▲△ 抽出（PE 非実行）
       ├─ build_purchase_snapshot(…)        # 固定買い目: 馬連/ワイド/三連複/三連単 × 100円
       └─ settle_strategy(snapshot, finish_order, payouts)
```

### 使用 / 未使用

| オブジェクト | 役割 | Challenge AI 集計 |
|--------------|------|-------------------|
| **`race_results`** | 公式結果・払戻・母集合 | **使用（必須）** |
| **`predictions`** | PredictionBundle（印） | **使用（必須）** |
| PI（HTTP） | predictions miss 時の bundle 補完 | **条件付き使用** |
| `race_evaluations` | ヒートマップ / 総合実績 / 285 seed | **未使用**（コードコメント明示） |
| `self_evaluation_runs` | Stats run | **未使用** |
| `user_race_results` | ユーザー購入台帳 | **未使用**（User セクションのみ） |
| SQL VIEW | — | **なし** |

ソース: `services/win5-ai/app/challenge/service.py`

---

## 2. 集計対象期間（本当に指定月のみか）

| 項目 | 内容 |
|------|------|
| フィルタ | `race_results.race_date` の先頭 7 文字 = `month`（`YYYY-MM`） |
| 当日カット | **無し**（月初〜月末の該当行すべて。未来日も `race_date` が月内なら対象） |
| 他月リーク | **コード上なし**（月プレフィックス一致のみ） |
| 実測 `2026-07` | `race_date` **min=`2026-07-25` / max=`2026-07-26`** のみ。51 行すべてがこの 2 日 |

**判定:** 「指定カレンダー月の `race_date`」に限定されている。ただし「今月開催の全日」ではなく、**その月に結果行が存在する日だけ**が母集団。

---

## 3. Production のみか — Research / Canary / Validation / 285R の混在

### コード上の境界

- Challenge は **`race_evaluations` を読まない** → 285R baseline import / Research 評価行は **AI 利益に直接混入しない**。
- Research Scheduler / Canary / Validation の成果物テーブルへの JOIN も **無い**。

### 実測（寄与 51R）

| 指標 | 値 |
|------|-----|
| `predictions.engine_source` | **`real_ai` = 51 / 51** |
| `predictions.fallback_reason` | すべて null |
| race_id / source / engine / model への keyword（research, canary, validation, baseline, 285, mock, fixture, demo, test） | **0 ヒット** |
| `race_evaluations` 総数 | 302（うち month=2026-07 の distinct race_id = 15） |
| Challenge 51R ∩ evaluations(month) | 15（**参照はしていないが ID 重複はあり**） |
| Challenge only（eval 無し） | 36 |

**判定:**  
集計ロジックは Research/Canary/Validation/285 **テーブルを混ぜていない**。  
寄与レースの予測メタも `real_ai` のみ。  
一方で「公開承認済みのみ」などの **Production ゲート列は参照していない**（下記 §6）。

---

## 4. -54,380 円 / 51R の構成

### 集計値（`ai_monthly("2026-07")` 再計算一致）

| 項目 | 値 |
|------|-----|
| race_count | **51** |
| purchase_amount | **74,900** |
| payout_amount | **20,520** |
| profit | **-54,380**（= 20,520 − 74,900） |
| hit_count | 6 |
| recovery_rate | 27% |
| hit_rate | 12% |
| 買い目設定 | 馬連 / ワイド / 三連複 / 三連単 × 単注 100 円（理論） |

日別: `2026-07-25` = 36R、`2026-07-26` = 15R。

### 寄与レース一覧（全 51）

| # | race_id | race_date | profit | purchase | payout | hit | engine | result_source |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | 2026-07-25-01-01 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020101` |
| 2 | 2026-07-25-01-02 | 2026-07-25 | 4530 | 1500 | 6030 | True | real_ai | `netkeiba:202604020102` |
| 3 | 2026-07-25-01-03 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020103` |
| 4 | 2026-07-25-01-04 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020104` |
| 5 | 2026-07-25-01-05 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020105` |
| 6 | 2026-07-25-01-06 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020106` |
| 7 | 2026-07-25-01-07 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020107` |
| 8 | 2026-07-25-01-08 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020108` |
| 9 | 2026-07-25-01-09 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020109` |
| 10 | 2026-07-25-01-10 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020110` |
| 11 | 2026-07-25-01-11 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020111` |
| 12 | 2026-07-25-01-12 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020112` |
| 13 | 2026-07-25-02-01 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020101` |
| 14 | 2026-07-25-02-02 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020102` |
| 15 | 2026-07-25-02-03 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020103` |
| 16 | 2026-07-25-02-04 | 2026-07-25 | -120 | 1500 | 1380 | True | real_ai | `netkeiba:202607020104` |
| 17 | 2026-07-25-02-05 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020105` |
| 18 | 2026-07-25-02-06 | 2026-07-25 | 7790 | 1500 | 9290 | True | real_ai | `netkeiba:202607020106` |
| 19 | 2026-07-25-02-07 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020107` |
| 20 | 2026-07-25-02-08 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020108` |
| 21 | 2026-07-25-02-09 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020109` |
| 22 | 2026-07-25-02-10 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020110` |
| 23 | 2026-07-25-02-11 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020111` |
| 24 | 2026-07-25-02-12 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020112` |
| 25 | 2026-07-25-03-01 | 2026-07-25 | -940 | 1500 | 560 | True | real_ai | `netkeiba:202601010101` |
| 26 | 2026-07-25-03-02 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010102` |
| 27 | 2026-07-25-03-03 | 2026-07-25 | -920 | 1500 | 580 | True | real_ai | `netkeiba:202601010103` |
| 28 | 2026-07-25-03-04 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010104` |
| 29 | 2026-07-25-03-05 | 2026-07-25 | -700 | 700 | 0 | False | real_ai | `netkeiba:202601010105` |
| 30 | 2026-07-25-03-06 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010106` |
| 31 | 2026-07-25-03-07 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010107` |
| 32 | 2026-07-25-03-08 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010108` |
| 33 | 2026-07-25-03-09 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010109` |
| 34 | 2026-07-25-03-10 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010110` |
| 35 | 2026-07-25-03-11 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010111` |
| 36 | 2026-07-25-03-12 | 2026-07-25 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010112` |
| 37 | 2026-07-26-01-01 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020201` |
| 38 | 2026-07-26-01-02 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020202` |
| 39 | 2026-07-26-01-03 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020203` |
| 40 | 2026-07-26-01-04 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020204` |
| 41 | 2026-07-26-01-05 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202604020205` |
| 42 | 2026-07-26-02-01 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020201` |
| 43 | 2026-07-26-02-02 | 2026-07-26 | -700 | 700 | 0 | False | real_ai | `netkeiba:202607020202` |
| 44 | 2026-07-26-02-03 | 2026-07-26 | 1180 | 1500 | 2680 | True | real_ai | `netkeiba:202607020203` |
| 45 | 2026-07-26-02-04 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020204` |
| 46 | 2026-07-26-02-05 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202607020205` |
| 47 | 2026-07-26-03-01 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010201` |
| 48 | 2026-07-26-03-02 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010202` |
| 49 | 2026-07-26-03-03 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010203` |
| 50 | 2026-07-26-03-04 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010204` |
| 51 | 2026-07-26-03-05 | 2026-07-26 | -1500 | 1500 | 0 | False | real_ai | `netkeiba:202601010205` |

### データ整合の注意（Research 混在ではないが重要）

`race_results.source = netkeiba:{numeric}` の numeric 先頭 8 桁（開催日っぽい部分）の内訳:

| source 内日付 | 件数 | 対比 |
|---------------|-----:|------|
| `20260101` | 17 | `race_date` は 7/25–26 |
| `20260402` | 17 | 同上 |
| `20260702` | 17 | 同上 |

会場コード `01/02/03` と source 日付が揃って見える一方、**`race_id` / `race_date`（7/25–26）と Netkeiba numeric の日付が一致しない**。  
Challenge は `result_json` の着順・払戻をそのまま settle するため、**誤った Netkeiba ページが紐づいている場合、理論損益は「7月レース」名義でも中身が別日結果になり得る**。本監査では RA の numeric 解決ロジックまでは断定しないが、**Production 結果の真正性リスク**として差分に含める。

---

## 5. UI「今月」と実際の集計範囲

| 層 | 挙動 |
|----|------|
| FE | `currentMonth()` = ブラウザローカルの `YYYY-MM`。ラベル「YYYY年M月」「今月のAIチャレンジ」「AI利益（今月の目標）」 |
| API | `GET /v1/challenge/monthly?month=YYYY-MM`（FE が同じ文字列を渡す） |
| 集計 | その `month` の `race_results.race_date` プレフィックス一致行のみ |

**一致している点**

- UI の選択月 ↔ API `month` ↔ SQL 月フィルタは **同一キー**。
- 月送り UI でも同じ契約。

**ずれやすい点**

1. 「今月」＝**カレンダー月全体の開催予定**ではなく、**結果が DB にあるレースのみ**（現状 2 日分）。
2. TZ: FE はローカル日付、DB の `race_date` は日付文字列。通常 JST 運用なら一致しやすいが、コード上 TZ 正規化は無い。
3. 文言「今月の目標」は **共有ベンチマーク**であり、ユーザー登録日以降には切らない（AI 側は意図どおり共有）。

---

## 6. あるべきデータソースとの差分

### 想定（監査上の期待）

Challenge AI 実績は次のみを見るべき:

1. **Production** 経路の公式結果  
2. **ユーザー公開済み（または Production 承認済み）** の予測のみ  
3. Research / Canary / Validation / 285 baseline / mock を混ぜない  
4. 表示月と `race_date` 月が一致

### 現状

| 期待 | 現状 | 差分 |
|------|------|------|
| Production 結果のみ | `race_results`（RA Netkeiba 由来 `source=netkeiba:…`） | **テーブルは Production 系**。ただし **公開/承認フラグでの絞り込み無し** |
| 公開済み予測のみ | `predictions` 最新 1 件（`ORDER BY created_at DESC`）。engine/publish 条件なし。miss 時は **PI 直取得** | **「公開済み」ゲート無し**。最新行が何であれ採用 |
| Research/Canary/285 排除 | `race_evaluations` 未使用 → 285 は直接混ざらない | **パス上は OK**。メタ keyword も寄与 51R で 0 |
| 月一致 | `substr(race_date,1,7)` | **OK**（UI month と一致） |
| 結果の真正性 | Netkeiba から同期した `result_json` | **`source` 内日付 ≠ `race_date`** の疑い → **真正性未保証** |

### 差分サマリ

1. **ゲート不足:** Production / 公開済みを区別する列・フラグを Challenge は見ていない（「最新 predictions + ある race_results」）。  
2. **Research 系テーブル混入:** なし（285 / evaluations は別系統）。  
3. **結果ソースの日付不整合:** `netkeiba:` numeric と `race_date` の不一致は、Challenge 数値の信頼度を下げる（別チケット候補）。  
4. **UI:** 「今月」ラベルと月フィルタは一致。母集団は「結果確定済みの月内レース」に限定される点は仕様理解が必要。

---

## 7. 生データ参照

- EC2 監査ダンプ: `/tmp/challenge-data-source-audit.json`（調査時生成）  
- ローカルコピー: `tmp-challenge-data-source-audit.json`（リポジトリ作業ツリー、コミット対象外想定）

---

## 判定

**Challenge `ai_monthly` は `race_results` × `predictions`（必要時 PI）の理論 settle であり、Research / Canary / Validation / 285R 評価テーブルは集計に入れていない。**  
期間は指定月の `race_date` のみで、UI「今月」と月キーは一致する。  

一方で **「Production かつユーザー公開済みのみ」という製品期待に対しては、公開ゲートが無く、かつ Netkeiba `source` 日付と `race_date` の不一致リスクがある** — ここが本来ソースとの主な差分である。

（本ドキュメントは調査のみ。修正は行っていない。）
