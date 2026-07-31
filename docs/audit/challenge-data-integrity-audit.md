# Challenge データ整合性監査 — Prediction ↔ Result（Version9.0 前・最終）

**Date:** 2026-07-27  
**Mode:** 調査のみ（コード変更なし）  
**Scope:** Challenge AI 共有実績 51R（`month=2026-07`）における Prediction Bundle と `race_results` の対応  
**DB:** `/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db`  
**未変更:** PE / CE / AI推論 / Research / ResultAutomation

関連:  
- `docs/audit/challenge-ai-benchmark-audit.md`（データソース）  
- `docs/audit/challenge-data-source-audit.md`（先行）

---

## 総合判定

# **PASS**

| 観点 | 判定 | 要約 |
|------|------|------|
| ① 結合キー | **PASS** | `predictions.race_id` = `race_results.race_id` = Challenge `race_id`（TEXT） |
| ② 最新 Bundle 採用 | **PASS*** | 現行は「最新1件」採用。51R は各1行のみで衝突なし。\*承認ゲートは別問題（本監査の整合性 FAIL にはしない） |
| ③ `source` / Netkeiba ID 意味 | **PASS** | `netkeiba:{12桁}` は **開催コード**（年+競馬場+回次+日次+R）。カレンダー日付 YYYYMMDD **ではない** |
| ④ 51R 全件一致 | **PASS** | Bundle の race_id / date / venue、Result の race_date / venue、Netkeiba 場コード・R番号が **51/51 一致** |

※ 先行監査で「`20260402` 等が race_date と不一致」とした指摘は、Netkeiba ID を YYYYMMDD と誤読したことによる **誤警報**。本監査で訂正する。

---

## ① Prediction Bundle と race_results の紐付け

### 結合キー

**単一キー: `race_id`（TEXT）**

```
Prediction Bundle (predictions.bundle_json)
        │
        │  行キー: predictions.race_id
        │  （任意）bundle_json.race_id も同値を保持
        ▼
     race_id  ←── 結合キー（等価結合）
        │
        ▼
race_results.race_id
        │
        ▼
Challenge settle_ai_theory_for_race(race_id)
```

| 側 | キー | 実測 |
|----|------|------|
| `predictions` | `race_id` | Challenge の race_id と **51/51 一致** |
| `race_results` | `race_id` | **51/51 一致** |
| Bundle 内 | `bundle_json.race_id` | **51/51** が Challenge race_id と一致（または null 扱い不要） |
| 二次キー | なし | `source` / `numeric_race_id` は結合に使わない（結果取得 provenance） |

### コード上の参照

```text
latest_prediction_bundle(race_id)
  SELECT bundle_json FROM predictions
  WHERE race_id=?
  ORDER BY created_at DESC, id DESC LIMIT 1

_load_official_result(race_id)
  SELECT * FROM race_results WHERE race_id=?
```

Challenge は両結果を同一 `race_id` で読み、理論買い目 settle する。

---

## ② 最新 Bundle 採用条件

### なぜ「最新 predictions」か

| 項目 | 内容 |
|------|------|
| SQL | `ORDER BY created_at DESC, id DESC LIMIT 1` |
| 意図（コード） | 同一 `race_id` に複数行があり得るため、**最も新しい作成時刻**の Bundle を理論 settle に使う |
| 承認フィルタ | **無し**（`approved` / `published` / Production 承認フラグを見ない） |
| miss 時 | PI から Bundle 取得 → 任意で `predictions` に cache INSERT |

### Production 承認済み Bundle との違い

| | 現行 Challenge | 理想の「Production 承認済み」 |
|--|----------------|------------------------------|
| 選択規則 | 最新行（時刻順） | 承認済み / 公開済みのみ |
| ゲート列 | なし | （現状スキーマ・参照なし） |
| 複数版衝突 | 最新が勝つ | 承認版が勝つ |
| 実測 2026-07 | **各 race_id に predictions 1 行のみ**（`multi_prediction_races=0`） | 現行データでは最新＝唯一 |

**整理:** 「最新採用」は実装上のヒューリスティック。今回の 51R では唯一行のため、最新＝実データ上の Production `real_ai` Bundle と一致。ただし **承認プロセスとの契約保証はない**（ポリシー差分は WARNING 候補だが、レコード不整合ではない）。

---

## ③ `race_results.source`（Netkeiba）の意味

### 書き込み経路

`NetkeibaResultProvider`（ResultAutomation の結果同期）:

1. PI catalog から `race_id` + `numeric_race_id` を取得  
2. `https://race.netkeiba.com/race/result.html?race_id={numeric}` を取得・パース  
3. `race_results` に保存し `source = "netkeiba:{numeric}"`

※ コメントの “published result table” は **Netkeiba 側に結果表が出ていること**を指し、Expect の「Production 承認」とは別概念。

### 12 桁 Netkeiba `race_id` の構造（訂正）

**日付の YYYYMMDD ではない。**

```
YYYY JJ KK NN RR
│    │  │  │  └─ レース番号 (01–12)
│    │  │  └──── 開催日次 (何日目)
│    │  └─────── 開催回次 (第N回)
│    └────────── 競馬場コード
└─────────────── 年
```

競馬場コード（JRA 慣例）:

| コード | 場 |
|--------|-----|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

### Challenge 51R に出現する値の意味

| source 接頭（例） | 解読 | Expect 側の対応（実測） |
|-------------------|------|-------------------------|
| `netkeiba:20260402…` | 2026年 / **新潟(04)** / 第02回 / 日次… / R… | venue=**新潟**, race_date=2026-07-25\|26 |
| `netkeiba:20260702…` | 2026年 / **中京(07)** / 第02回 / … | venue=**中京** |
| `netkeiba:20260101…` | 2026年 / **札幌(01)** / 第01回 / … | venue=**札幌** |

したがって:

- `20260101` / `20260402` / `20260702` の先頭 8 桁を「2026-01-01」「2026-04-02」「2026-07-02」と読むのは **誤り**。  
- 正しくは **年(4)+場(2)+回(2)** までが開催識別で、カレンダー日は Expect / Bundle の `race_date`（例: 2026-07-25）が正本。

### Bundle / Prediction / Result との関係

| フィールド | 役割 |
|------------|------|
| `race_id` | Expect 内部 ID。Prediction・Result・Challenge の結合キー |
| `race_date` | 開催カレンダー日（Challenge 月次フィルタの正本） |
| `predictions.bundle_json` | 印・レース情報（date/venue 含む） |
| `race_results.source` | 公式結果の取得 provenance（Netkeiba 12桁） |
| `result_json.numeric_race_id` | source と同じ numeric（実測一致） |

---

## ④ RaceID 全件監査（51R）

### チェック結果サマリ

| チェック | 結果 |
|----------|------|
| Result 行存在 | **51/51** |
| Prediction 行存在 | **51/51** |
| `predictions.race_id` == Challenge race_id | **51/51** |
| `race_results.race_id` == Challenge race_id | **51/51** |
| Bundle 内 `race_id` 一致 | **51/51** |
| Bundle `race_info.date` == `race_results.race_date` | **51/51** |
| Bundle venue == Result venue | **51/51** |
| Netkeiba 場コード → 場名 == Result venue | **51/51**（新潟/中京/札幌） |
| Netkeiba R番号 == Expect race_id 末尾 | **51/51** |
| `engine_source=real_ai` | **51/51** |
| finish_order あり | **51/51** |
| 同一 race_id の predictions 複数行 | **0**（最新=唯一） |
| `source` が netkeiba | **51/51** |

### 場別内訳

| venue | Netkeiba jyo | 件数 |
|-------|--------------|-----:|
| 新潟 | 04 | 17 |
| 中京 | 07 | 17 |
| 札幌 | 01 | 17 |
| **計** | | **51** |

### 全 RaceID 一覧（整合ステータス）

全件 `JOIN_OK` / `DATE_OK` / `VENUE_OK` / `NETKEIBA_JYO_OK` / `R_OK`。

| # | race_id | race_date | venue | source | pred | 整合 |
|---:|---|---|---|---|---|---|
| 1 | 2026-07-25-01-01 | 2026-07-25 | 新潟 | `netkeiba:202604020101` | real_ai | PASS |
| 2 | 2026-07-25-01-02 | 2026-07-25 | 新潟 | `netkeiba:202604020102` | real_ai | PASS |
| 3 | 2026-07-25-01-03 | 2026-07-25 | 新潟 | `netkeiba:202604020103` | real_ai | PASS |
| 4 | 2026-07-25-01-04 | 2026-07-25 | 新潟 | `netkeiba:202604020104` | real_ai | PASS |
| 5 | 2026-07-25-01-05 | 2026-07-25 | 新潟 | `netkeiba:202604020105` | real_ai | PASS |
| 6 | 2026-07-25-01-06 | 2026-07-25 | 新潟 | `netkeiba:202604020106` | real_ai | PASS |
| 7 | 2026-07-25-01-07 | 2026-07-25 | 新潟 | `netkeiba:202604020107` | real_ai | PASS |
| 8 | 2026-07-25-01-08 | 2026-07-25 | 新潟 | `netkeiba:202604020108` | real_ai | PASS |
| 9 | 2026-07-25-01-09 | 2026-07-25 | 新潟 | `netkeiba:202604020109` | real_ai | PASS |
| 10 | 2026-07-25-01-10 | 2026-07-25 | 新潟 | `netkeiba:202604020110` | real_ai | PASS |
| 11 | 2026-07-25-01-11 | 2026-07-25 | 新潟 | `netkeiba:202604020111` | real_ai | PASS |
| 12 | 2026-07-25-01-12 | 2026-07-25 | 新潟 | `netkeiba:202604020112` | real_ai | PASS |
| 13 | 2026-07-25-02-01 | 2026-07-25 | 中京 | `netkeiba:202607020101` | real_ai | PASS |
| 14 | 2026-07-25-02-02 | 2026-07-25 | 中京 | `netkeiba:202607020102` | real_ai | PASS |
| 15 | 2026-07-25-02-03 | 2026-07-25 | 中京 | `netkeiba:202607020103` | real_ai | PASS |
| 16 | 2026-07-25-02-04 | 2026-07-25 | 中京 | `netkeiba:202607020104` | real_ai | PASS |
| 17 | 2026-07-25-02-05 | 2026-07-25 | 中京 | `netkeiba:202607020105` | real_ai | PASS |
| 18 | 2026-07-25-02-06 | 2026-07-25 | 中京 | `netkeiba:202607020106` | real_ai | PASS |
| 19 | 2026-07-25-02-07 | 2026-07-25 | 中京 | `netkeiba:202607020107` | real_ai | PASS |
| 20 | 2026-07-25-02-08 | 2026-07-25 | 中京 | `netkeiba:202607020108` | real_ai | PASS |
| 21 | 2026-07-25-02-09 | 2026-07-25 | 中京 | `netkeiba:202607020109` | real_ai | PASS |
| 22 | 2026-07-25-02-10 | 2026-07-25 | 中京 | `netkeiba:202607020110` | real_ai | PASS |
| 23 | 2026-07-25-02-11 | 2026-07-25 | 中京 | `netkeiba:202607020111` | real_ai | PASS |
| 24 | 2026-07-25-02-12 | 2026-07-25 | 中京 | `netkeiba:202607020112` | real_ai | PASS |
| 25 | 2026-07-25-03-01 | 2026-07-25 | 札幌 | `netkeiba:202601010101` | real_ai | PASS |
| 26 | 2026-07-25-03-02 | 2026-07-25 | 札幌 | `netkeiba:202601010102` | real_ai | PASS |
| 27 | 2026-07-25-03-03 | 2026-07-25 | 札幌 | `netkeiba:202601010103` | real_ai | PASS |
| 28 | 2026-07-25-03-04 | 2026-07-25 | 札幌 | `netkeiba:202601010104` | real_ai | PASS |
| 29 | 2026-07-25-03-05 | 2026-07-25 | 札幌 | `netkeiba:202601010105` | real_ai | PASS |
| 30 | 2026-07-25-03-06 | 2026-07-25 | 札幌 | `netkeiba:202601010106` | real_ai | PASS |
| 31 | 2026-07-25-03-07 | 2026-07-25 | 札幌 | `netkeiba:202601010107` | real_ai | PASS |
| 32 | 2026-07-25-03-08 | 2026-07-25 | 札幌 | `netkeiba:202601010108` | real_ai | PASS |
| 33 | 2026-07-25-03-09 | 2026-07-25 | 札幌 | `netkeiba:202601010109` | real_ai | PASS |
| 34 | 2026-07-25-03-10 | 2026-07-25 | 札幌 | `netkeiba:202601010110` | real_ai | PASS |
| 35 | 2026-07-25-03-11 | 2026-07-25 | 札幌 | `netkeiba:202601010111` | real_ai | PASS |
| 36 | 2026-07-25-03-12 | 2026-07-25 | 札幌 | `netkeiba:202601010112` | real_ai | PASS |
| 37 | 2026-07-26-01-01 | 2026-07-26 | 新潟 | `netkeiba:202604020201` | real_ai | PASS |
| 38 | 2026-07-26-01-02 | 2026-07-26 | 新潟 | `netkeiba:202604020202` | real_ai | PASS |
| 39 | 2026-07-26-01-03 | 2026-07-26 | 新潟 | `netkeiba:202604020203` | real_ai | PASS |
| 40 | 2026-07-26-01-04 | 2026-07-26 | 新潟 | `netkeiba:202604020204` | real_ai | PASS |
| 41 | 2026-07-26-01-05 | 2026-07-26 | 新潟 | `netkeiba:202604020205` | real_ai | PASS |
| 42 | 2026-07-26-02-01 | 2026-07-26 | 中京 | `netkeiba:202607020201` | real_ai | PASS |
| 43 | 2026-07-26-02-02 | 2026-07-26 | 中京 | `netkeiba:202607020202` | real_ai | PASS |
| 44 | 2026-07-26-02-03 | 2026-07-26 | 中京 | `netkeiba:202607020203` | real_ai | PASS |
| 45 | 2026-07-26-02-04 | 2026-07-26 | 中京 | `netkeiba:202607020204` | real_ai | PASS |
| 46 | 2026-07-26-02-05 | 2026-07-26 | 中京 | `netkeiba:202607020205` | real_ai | PASS |
| 47 | 2026-07-26-03-01 | 2026-07-26 | 札幌 | `netkeiba:202601010201` | real_ai | PASS |
| 48 | 2026-07-26-03-02 | 2026-07-26 | 札幌 | `netkeiba:202601010202` | real_ai | PASS |
| 49 | 2026-07-26-03-03 | 2026-07-26 | 札幌 | `netkeiba:202601010203` | real_ai | PASS |
| 50 | 2026-07-26-03-04 | 2026-07-26 | 札幌 | `netkeiba:202601010204` | real_ai | PASS |
| 51 | 2026-07-26-03-05 | 2026-07-26 | 札幌 | `netkeiba:202601010205` | real_ai | PASS |

（7/26 の `…0201` 等は Netkeiba の **日次=02**＋R。Expect `race_date=2026-07-26` と整合。）

---

## ⑤ Prediction → Result → Challenge 整合性

```
Prediction (bundle @ race_id, real_ai)
        │  race_id
        ▼
Result (race_results @ race_id, netkeiba provenance)
        │  finish_order / payouts + same race_id
        ▼
Challenge ai_monthly settle (理論 P&L)
```

| 層間 | 整合 |
|------|------|
| Prediction ↔ Result | **PASS**（race_id / date / venue） |
| Result.source ↔ venue/R | **PASS**（Netkeiba 開催コードとして解釈） |
| → Challenge 集計入力 | **PASS**（51R すべて settle 可能な一致セット） |

### 総合判定

# **PASS**

**補足（FAIL ではない）**

- 「最新 Bundle ≠ 承認済み Bundle」は **ガバナンス／仕様ギャップ**（前回 `challenge-ai-benchmark-audit.md` の WARNING 領域）。  
- 本監査対象の **レコード対応関係** においては不整合なし。  
- 先行の「source 日付不一致」は Netkeiba ID 誤読による誤警報 → **本ドキュメントで訂正**。

---

**署名:** 調査のみ。PE / CE / AI / Research / ResultAutomation への変更なし。
