# Version36 — Recommendation

**Status:** Architecture only — **not implemented**  
**Date:** 2026-07-28  
**Parent:** `v36-world-pe-integration.md`

---

## ⑦ Recommendation — 単一推奨

### 推奨接続点

# **I3 — World → PE**

### 最終判定

# **C — World should integrate before PE**

---

## 理由

### 1. 設計思想との一致

World の定義は「最上流の **勝ち筋分類**」である（V32）。  
勝ち筋が Prediction の結果を決めるなら、順位を出す層 — **PE（Scorer/Ranker / top-pick policy）** — が World decision を消費しなければならない。

CE や facade に載せるだけでは「分類した記録」であり「決定」ではない（V35 で証明済み）。

### 2. V35 が示した唯一の実効ギャップ

```text
World 変化 ──✗──► PE top pick ──► Prediction
```

切断辺は PE 入力である。  
Pool / Required をいくら World 化しても、PE が全馬・World 非依存のままなら Single Prediction は動かない。

### 3. 「Pool 前接続」だけでは不足する理由（B を単独推奨しない）

調査対象チェーンは確かに:

```text
World → SubWorld → Required → Candidate Pool → PE → Prediction
```

これは **生成・選択の順序**として正しい。  
しかし V35 の問題設定（Hit / Prediction 不変）に対する **効く辺**は Pool ではなく PE である。

- **B（Pool 前のみ）** → Win5 券面は変わり得るが、現行 PE 定義では Prediction 不変が残る  
- **C（PE 前）** → Prediction が勝ち筋に従うための必須条件

したがって本フェーズの「最も責務が自然な **接続点**（単一）」は **PE** とする。  
Required / Pool は **同じ World decision の正式 Consumer**（副次脊柱）として境界文書に残すが、推奨の主語は I3。

### 4. CE を選ばない理由

現行失敗モードそのもの。CE は投影層であり決定層ではない（`v36-boundary-analysis.md`）。

### 5. Features 直結を選ばない理由

効果は出るが、WIC/World の責務を Feature に漏洩させ、V32「列数ではなく Signal 契約」と衝突する（I6）。

### 6. 難易度 High を許容する理由

正しい境界が重いのは、今日の順序が思想と逆だからである。  
Low 難易度案（I4/I5）は思想を満たさない。

---

## 推奨時の設計契約（未実装・意図文）

```text
World → PE Integration Contract (design intent)
-----------------------------------------------
1. World decision は PE より前に確定する（WIC 充足が前提）。
2. PE は World decision / policy を入力契約に含む
   （生 WIC 信号の再解釈は PE の責務にしない）。
3. CE は PE 出力を投影する。World で Rank を決めない。
4. Prediction は world / sub_world を破棄しない。
5. Required / Candidate Pool は同一 World decision の選択 Consumer。
6. 実装・Production 変更は別承認。本文書は接続点の設計固定のみ。
```

---

## 明示的に採用しないもの

| 案 | 扱い |
|----|------|
| A 現行維持 | Reject — 思想不適合 |
| B Pool 前を **唯一**の主接続とする | Reject as primary — 副次 Consumer としては維持 |
| I4 CE / I5 Facade | Reject — 偽接続 |
| I6 Features 直結 | Reject as primary — 責務漏洩 |
| D 複合を主推奨 | Reject for this phase — 文書上は副次脊柱を認めるが判定記号は **C** |

---

## 次フェーズへの含意（実装しない・ゲートのみ）

- V34: Signal Service は ROI 未証明で NO-GO のまま、という制約は維持し得る  
- ただし **接続点の設計問**は本フェーズで **C / I3** に固定する  
- 将来の AB は `frozen_pe_pick` では World→Prediction 因果を検証できない（V35 FP-AB）

---

## 関連成果物

| ファイル | 役割 |
|----------|------|
| `v36-world-pe-integration.md` | 概要・判定 C |
| `v36-integration-options.md` | 候補 I1–I6 |
| `v36-boundary-analysis.md` | 本来フロー・WIC Consumer |
| `v36-risk-analysis.md` | 難易度・影響 |
| `v36-recommendation.md` | 本ファイル |
