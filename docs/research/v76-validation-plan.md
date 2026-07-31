# Version76 — Validation Plan（Ready 判定の評価項目）

**Date:** 2026-07-28  
**Purpose:** Ready Gate を満たすために実行すべき評価（計画のみ）。  
**本フェーズ:** 計画の定義。評価ランナー実装・PE 変更は **禁止**。

---

## ③ Validation Plan 概要

```text
Phase E0  現状スナップショット固定（V73 CEW + V74 metrics）— 済
Phase E1  契約テスト可能性（G-C1）— 計測定義
Phase E2  分割再現（G-S2 / G-R1 / Sep 再現）
Phase E3  標本増強後の再測（G-S1）— コーパス拡張は別 Decision
Phase E4  Residual 誤適用・カバレッジ
Phase E5  Blocked→Partial 再判定
→ Ready スコアカード更新（実装なし）
```

---

## E1 — Contract Testability（必須・全 Partial）

各 ACTIVE Contract MUST について:

| 出力 | 内容 |
|---|---|
| Test ID | 例: `rank7.MUST.2.field_size_attenuate` |
| 入力 | CEW=当該 World のレース集合 |
| 統計量 | 契約が指定する r / effect 差 |
| Pass 規則 | Gate 文書の閾値 |
| 記録 | n, 点推定, （可能なら）分割別 |

**禁止:** テスト合否に Hit を使う。

---

## E2 — Split Replication（必須・rank7 / midhole）

| 項目 | 定義 |
|---|---|
| 分割 | 285R を race_id 時系列（または開催日）で **半々**。各 World 各 split の n を記録 |
| 再計算 | importance 順位、style 首位、相互作用 r |
| Pass | `v76-readiness-gate.md` の G-S2 / G-R1 / Sep / 固有条件 |
| Fail 時 | Ready 不可。閾値緩和は別 Decision（本計画で勝手に緩めない） |

midhole が片側 n\<15 なら G-S2 FAIL — **標本増強が先**（E3）。

---

## E3 — Sample Enrichment（条件付き）

| 対象 | トリガ |
|---|---|
| midhole | 現状 n=24 \< G-S1(40) |
| core / midupper / mixed / bug | Blocked→Partial に n≥20 が必要 |

 enrichment 方法（選択肢・実施は別 Decision）:

1. 同一 CEW 規則でコーパス拡張（285R 外）  
2. 複数シーズンの CEW 再ラベル  

**本フェーズでは方法の列挙のみ。実行しない。**

---

## E4 — Residual Validation（unsatisfied）

| 評価項目 | 定義 |
|---|---|
| 誤適用率 | CEW=unsatisfied なのに Positive Strategy ラベルを当てた場合の件数定義（Shadow シミュレーション可 — PE 非変更） |
| フォールバック | popularity 欠損レース割合と、odds/win_prob への切替規則の適用率 |
| ベースライン安定 | 分割間で Top3 特徴の自己 Jaccard |

---

## E5 — Blocked Re-entry

| World | 最初の評価項目 |
|---|---|
| core | CEW n、top_gap 分布、win_prob effect 順位 |
| midupper | CEW n、aptitude 代理の有無フラグ、差しリフト再現 |
| mixed | CEW n、match_set 構成ヒストグラム、history effect |
| bug | exception 真の件数、n≥5 |

---

## 評価項目チェックリスト（Ready 直前）

### rank7

- [ ] n≥40（済: 65）  
- [ ] 2-split 各 n≥15  
- [ ] field_size 減衰 r≤−0.05 両 split  
- [ ] 脚質首位 ≠ midhole 両 split  
- [ ] Sep OR 条件 PASS  
- [ ] MUST テスト ID すべて記録  
- [ ] Top3 自己 Jaccard ≥0.60  

### midhole

- [ ] n≥40  
- [ ] 2-split 各 n≥15  
- [ ] history−win_prob effect 差 >0.15 両 split  
- [ ] upper_ability_band r≤−0.05 両 split  
- [ ] Sep OR 条件 PASS  
- [ ] MUST テスト記録  
- [ ] Top3 自己 Jaccard ≥0.60  

### unsatisfied（Residual Ready）

- [ ] 誤適用率ベースライン  
- [ ] フォールバック規則 + coverage  
- [ ] MUST テスト記録  

---

## 成果物（将来評価実行時）

評価を別 Decision で実行した場合の想定成果:

- `_v76-gate-scorecard.json`  
- split 別 metrics  
- MUST テスト結果表  

**本 Version76 では作成しない**（計画のみ）。  
