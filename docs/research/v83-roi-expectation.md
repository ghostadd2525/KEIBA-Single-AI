# Version83 — ROI Expectation

**Date:** 2026-07-28  
**Type:** Expectation / Hypothesis ONLY — **実測なし・実装なし**  
**Parent:** `v83-interaction-integration-design.md` / `v83-integration-matrix.md`  
**Locks:** Production / Trigger / Blueprint / World / Interaction Contract  
**注意:** ここに書く ROI は **期待シナリオ**であり、約束・目標 KPI ではない。

---

## 期待の置き方

| 層 | 本ドキュメント |
|---|---|
| 実測 ROI / Hit / Purchase | **しない**（V80 以外の新規実行なし） |
| 方向性期待 | する（方式比較用） |
| 本番コミット | 禁止 |

参照アンカー（既知実測）:

| 事実 | 含意 |
|---|---|
| V80 ΔStrategy Hit = **−133**（単体 Weight 寄り Shadow） | 加算・再スコア系は下振れが現実に大きい |
| V81 Interaction Lift（例: 3-way ≈1.8–2.0 帯が一部） | 「情報はある」が PE 写像を保証しない |
| V82 Contract | 写像の意味制約。ROI 保証ではない |

---

## 方式別 ROI Expectation

### ① Bonus

| 項目 | Expectation |
|---|---|
| 方向（楽観） | Interaction 余力を連続値で回収 → 中〜高 |
| 方向（悲観） | V80 再来（全域悪化）→ **大きく負** |
| 期待値（設計判断） | **負にバイアス**（非推奨） |
| 時間軸 | 短期に Hit が動きやすい＝観測は容易、危険も早い |
| Rollback 価値 | 高い（悪化時の損失回避）が、採用期待値自体が低い |

### ② Gate

| 項目 | Expectation |
|---|---|
| 方向（楽観） | 偽Interaction レースを落とす → 質的 ROI↑ |
| 方向（悲観） | カバレッジ減・真陽性ゲート落ち → 機会損失 |
| 期待値（設計判断） | **不安定**（欠測・pace 依存で中立〜負） |
| 特記 | midhole は pace 240/285 欠測があり Gate 不発が増えやすい |

### ③ Selector

| 項目 | Expectation |
|---|---|
| 方向（楽観） | Contract 通りの読み分け → 中（World 分離利益） |
| 方向（悲観） | 誤パス固定・Fallback 盗用 → 中負 |
| 期待値（設計判断） | **中立〜弱正**（归因成功が前提） |
| 条件 | V79 型 2×2 なしでは ROI 解釈不能 → 見かけ正を信じない |

### ④ Rank Swap

| 項目 | Expectation |
|---|---|
| 方向（楽観） | TopN の局所的的中改善 → 弱〜中正 |
| 方向（悲観） | 無意味 swap → 弱負（全域崩壊はしにくい） |
| 期待値（設計判断） | **弱正（条件付き）** |
| 条件 | N 小・Must 信号のみ・Ready World 限定 |

### ⑤ Confidence

| 項目 | Expectation |
|---|---|
| 方向（順位 Hit） | **≈0**（定義上順位非変更） |
| 方向（運用 ROI） | 閾値・サイズ・見送り判断が改善すれば弱正 |
| 方向（悲観） | conf を無視する運用なら ROI≈0 のまま |
| 期待値（設計判断） | **順位 ROI は狙わず、学習コスト最小の検証 ROI を取る** |

---

## 段階期待（将来 Shadow・非コミット）

| Stage | Mode | 主に見る期待指標 | 成功の見え方 | 失敗の見え方 |
|---|---|---|---|---|
| S0 | Confidence | Interaction 発火と conf 単調性 / 説明一貫性 | Must 発火で conf が契約通り動く | 発火と conf が無相関・逆行 |
| S1 | Rank Swap | TopN Hit / 局所 Δ（Legacy 比） | 局所非劣化＋弱改善 | TopN 劣化（全域 Hit は副次） |
| S2 | Selector | 归因分離後の ΔStrategy | Contract パスが正の寄与 | パス切替がノイズ |

**Bonus / 全面 Gate は Expectation 上「採用期待値 < 検証コスト」のため Stage 外。**

---

## World 別 ROI 注意

| World | Expectation 上の注意 |
|---|---|
| rank7 | 標本安定。S0/S1 の主戦場。 |
| midhole | n=24・Partial。正の ROI を主張しない。 |
| unsatisfied | Residual。勝ち筋 ROI を謳わない。Baseline conf のみ。 |
| core | PROVISIONAL。ROI Expectation **対象外**。 |

---

## 非主張（明示）

- Interaction Lift > 1 を PE ROI に換算しない  
- V82 Must 採用 = ROI 改善、とは書かない  
- Production 投入の期待 ROI は定義しない  

---

## 要約一文

> V83 の ROI Expectation は「Bonus で稼ぐ」ではなく、**Confidence → Rank Swap の順で下振れを抑えながら Contract 作用を検証する**ことに置く。
