# RePick v2 — Failure Analysis（発火過大）

**Date:** 2026-07-21  
**Status:** Analysis only（**コード変更なし** / 設計改訂なし）  
**Parent AB:** [`repick-v2-ab-report.md`](./repick-v2-ab-report.md)（採択）  
**実装:** 維持（Flag OFF）  

## 0. 結論（先に）

設計上の評価母集団は **G1=11** だが、実装トリガは **匿名 G1′（model_rank∈[7,10] ∧ ∉repick ∧ NEAR）** であり、
**レースが G1 であることは条件に含まれない**。そのため Treatment で **100 レース発火**し、うち **G1 外が 95**（AB の churn_g1≈95 と整合）。

過発火の主因は「G1 を対象に設計した」ことと「G1′ 匿名を全 285R に適用した」ことのギャップである。

---

## 1. 発火内訳（総発火 **100**）

| 母集団 | n | 定義 |
|--------|--:|------|
| **G1** | **5** | 設計 Primary 11 レースのうち発火したもの |
| **G2** | **1** | rank46 二次（小倉-11 rank6） |
| **G3** | **1** | Deep other_miss（re_pick 残） |
| **その他** | **93** | 上記外（多くは Control で既に Hit / 別バケツ） |

- AB 記載の「95件」は **G1 外の churn（symdiff）** 指標に対応。本解析の発火総数は **100**、G1 外発火 **95**。
- その他のうち Control が既に Hit の発火: **77**
- その他/関連で after_ctrl=rank46_miss の発火: **9**

### G1 発火詳細

| race_id | cand==winner | in_repick | Hit改善 |
|---------|--------------|----------:|--------|
| 2025-12-14-中京-11 | True | 1 | True |
| 2026-03-15-中山-11 | True | 1 | True |
| 2026-04-12-阪神-10 | False | 0 | False |
| 2026-04-19-中山-10 | True | 1 | True |
| 2026-04-25-京都-10 | True | 1 | False |

---

## 2. 発火条件別件数

実装条件（すべて AND）:

```text
WIN5_REPICK_V2_ENABLED
∧ model_rank(cand) ∈ [7,10]
∧ cand ∈ pool(rescored) ∧ cand ∉ selected
∧ N < surv_pos(cand) ≤ N+2   # RV2-A NEAR
∧ removable victim が存在
```

**レースが G1 / first_loss=re_pick / winner 一致 は条件に無い。**

| 切片（発火レースの属性） | n |
|--------------------------|--:|
| winner_rank 帯 = rank13 | 50 |
| winner_rank 帯 = rank45 | 20 |
| winner_rank 帯 = rank710 | 15 |
| winner_rank 帯 = rank6 | 9 |
| winner_rank 帯 = deep11p | 6 |

| Control after_miss_group | n |
|--------------------------|--:|
| Hit | 77 |
| rank46_miss | 9 |
| rank710_hidden_miss | 8 |
| other_miss_10_13 | 5 |
| other_miss_1_3 | 1 |

| Control first_loss_stage | n |
|--------------------------|--:|
| (empty/Hit) | 69 |
| re_pick | 15 |
| after_delete | 9 |
| candidate_pool | 5 |
| purchase | 2 |

| repick N | n |
|----------|--:|
| 5 | 6 |
| 7 | 94 |

---

## 3. NEAR 条件ごとの件数

初回 AB は **RV2-A（NEAR）のみ**。SLOT / rank6 Flag は OFF。

| NEAR facet | n |
|------------|--:|
| RV2-A | 100 |

全発火が facet=`RV2-A`（`N < surv_pos ≤ N+2`）。
（CSV に surv_pos 列が無いため N+1 / N+2 の内訳は本解析では未分割。必要なら別計測。）

---

## 4. 匿名トリガごとの件数

本番トリガ種別は **単一: 匿名 RV2-A**。Winner-Anchored / allowlist は未使用。

| 匿名サブ分類（事後観測） | n | 意味 |
|--------------------------|--:|------|
| RV2-A かつ cand==winner | **4** | 偶然 winner を拾った |
| RV2-A かつ cand≠winner | **96** | 別の rank710 NEAR を支払った（過半） |

過発火の本体は後者: **「誰かの」rank710 NEAR 欠落を全レースで支払う**ため、G1 の winner 債務と一致しない。

---

## 5. 発火したが改善しなかった件数

| 定義 | n / 100 |
|------|---:|
| 改善あり（winner in_repick 0→1 または Hit 化） | **6** |
| **改善なし** | **94** |

改善なしの内訳:

| 理由（重複可） | n |
|----------------|--:|
| cand ≠ winner | 94 |
| Control 既に Hit（無意味 churn） | 77 |
| 発火後も winner ∉ repick | 30 |

母集団別（改善なし）:

| pop | n |
|-----|--:|
| other | 91 |
| G3 | 1 |
| G2 | 1 |
| G1 | 1 |

---

## 6. 発火しなかった改善候補（G1）

G1=11 のうち **未発火 6** 件:

| race_id | reason | winner_rank | after_tx |
|---------|--------|------------:|----------|
| 2024-01-21-京都-11 | no_near_candidate | 7 | rank710_hidden_miss |
| 2024-02-18-京都-11 | no_near_candidate | 10 | rank710_hidden_miss |
| 2024-07-14-函館-10 | no_near_candidate | 8 | rank710_hidden_miss |
| 2025-12-13-中山-10 | no_near_candidate | 9 | rank710_hidden_miss |
| 2026-01-18-中山-10 | no_near_candidate | 9 | rank710_hidden_miss |
| 2026-06-28-小倉-11 | no_near_candidate | 7 | rank710_hidden_miss |

未発火 reason 集計:

| reason | n |
|--------|--:|
| no_near_candidate | 6 |

解釈: G1 の多数は **winner が NEAR 帯（N+1〜N+2）にいない**（FAR / SLOT / 後段欠落）ため RV2-A では発火しない。
一方で同一レースに別馬の NEAR がいれば **その馬向けに発火しうる**（G1 外その他の源泉）。

---

## 7. 発火条件を 1 つ追加した場合の推定件数

基準発火: **100**。以下は「既存発火集合に対し事後フィルタを 1 枚足した」場合の残件数（再シミュレーションではない）。

| 追加条件（分析用） | 推定残発火 | 備考 |
|-------------------|----------:|------|
| Control after = rank710_hidden_miss | **8** | ミス帯に限定 |
| Control after ≠ Hit | **23** | Hit レースの無意味 churn を除去 |
| Control first_loss = re_pick | **15** | 設計の first_loss に寄せる |
| winner_rank ∈ [7,10] | **15** | ※結果依存・本番匿名と緊張 |
| cand == winner | **4** | Winner-Anchored（本番禁止） |
| race_id ∈ G1 | **5** | allowlist（本番禁止） |
| N == 7 | **94** | 弱い |
| wr∈[7,10] ∧ after≠Hit | **8** | |
| wr∈[7,10] ∧ fl=re_pick | **5** | |

### 設計示唆（改訂はしない・記録のみ）

1. **G1 は評価分母であり、トリガ集合ではない** — 現状実装は仕様どおり匿名のため全 285R で発火しうる。
2. churn 失敗の主因は **Hit 済レースや rank46 レースでの rank710 NEAR 置換**（cand≠winner）。
3. G1 未発火の主因は **winner が NEAR 外**（`no_near_candidate`）。SLOT 解禁や別 facet は別 Flag（設計どおり未実施）。
4. 発火を G1 規模に戻すには、本番禁止の allowlist/Winner-Anchored 以外の **構造ゲート**（例: 発火キャップ、Hit レース禁止は結果漏洩、など）が別途設計審査になる。

---

## 参照

- JSON: `compare/repick_v2_failure_analysis.json`
- AB: `compare/repick_v2_ab_result.json`
- Trace: `compare/repick_v2_ab_trace.csv`
