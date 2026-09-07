# Version72 — Intent Label Guideline

**Date:** 2026-07-28  
**Parent:** `v72-ground-truth-definition.md` / `v72-world-label-rule.md`  
**Audience:** 設計評価・監査・Dual-Eval 設計者  
**実装禁止**

---

## ガイドライン原則

| ID | 原則 |
|---|---|
| G1 | World Label = **契約上の Expected 勝ち筋**（V43 G1） |
| G2 | 判定経路は常に Semantic → Trigger Contract → Expected World |
| G3 | **事前 Signal/Concept** のみ。事後結果でラベルを書き換えない |
| G4 | Must 欠落は unsatisfied 方向へ。Aux / 人気 / score で埋めない |
| G5 | 「どれにも非該当」を core にも bug にもしない → **unsatisfied** |
| G6 | 複数 MATCH → **mixed**（単一へ無理に落とさない） |

---

## 付与手順（人・設計レビュー用）

1. **Semantic 確認:** 当該レースについて、V43 Purpose がどの勝ち筋を述べているかを一文で書く（まだラベル確定しない）。  
2. **Contract 展開:** V44 Must / Exclude を World ごとにチェックリスト化する（`v72-world-label-rule.md`）。  
3. **Polarity:** 各 Must Signal について契約方向（↑/↓）のみ判定。製品閾値表を新設しない。  
4. **MATCH 表:** Primary 5 World の MATCH 真偽を記録。  
5. **Mixed:** multi_path / unexplained を評価。  
6. **Decision Tree:** `|M|` 規則で Expected World を確定。  
7. **禁止チェック:** ラベル決定過程に winner_rank / 人気 / Prediction score が混入していないことを確認。  
8. **副次のみ:** Expected Characteristics（V43 §⑥）は「MATCH 後の観察メモ」に限り記録。ラベル変更に使わない。

---

## World 別ガイド（要約）

| World | 付与してよいとき | 付与してはいけないとき |
|---|---|---|
| core | Gap↑∧Sep↑ かつ Exclude なし | 残余 DEFAULT、高 chaos、高 sfp、multi_path |
| midupper | UPPER∧DEV∧APT | difficulty のみ、chaos∧high_pace、中位帯開きを本体に |
| midhole | MidOpen∧WeakMono | late∧sust を本体、強い top_gap |
| rank7 | Chaos∧Pace∧Subordinate | chaos なし difficulty のみ、強い top_gap |
| mixed | 2+ Primary MATCH または unexplained | phase 単独、単一明確パス |
| bug | 例外標識が正に立つ | wr 深穴だけ、単なる高 chaos、残余ラベル |
| unsatisfied | MATCH 集合が空 | 「とりあえず core」 |

---

## V65 からの移行ガイド

| 旧（禁止） | 新（必須） |
|---|---|
| wr≤3 → core | CORE_MATCH |
| wr 2–6 → midupper | MIDUPPER_MATCH |
| wr 5–10 → midhole | MIDHOLE_MATCH |
| wr 7–10 → rank7 | RANK7_MATCH |
| wr≥11 → bug | BUG_MATCH（exception） |
| soft score priority | boolean MATCH + \|M\| 規則 |

旧ラベルが新規則と不一致でも、**旧に合わせない**。契約が正本。

---

## 欠損・観測不能時

| 状況 | 扱い |
|---|---|
| Must Signal 欠測 | 当該 MUST=false |
| aptitude / exception 欠測 | midupper / bug は MATCH 不可（埋めない） |
| 全 Primary MATCH false かつ mixed false | **unsatisfied** |
| 実装 Shadow が別ラベル | GT は変えない。差分は評価対象 |

---

## 用語の使い分け

| 用語 | 意味 |
|---|---|
| Intent GT / CEW | 本 V72 Expected World |
| Legacy World | Production `classify_world_line_type` 出力（被評価） |
| Shadow World | V44/V69 Logic Form 観測出力（被評価） |
| Winner Alignment | 結果帯との整合チェック（**GT ではない**） |
