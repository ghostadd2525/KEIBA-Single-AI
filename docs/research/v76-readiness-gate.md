# Version76 — Readiness Gate（昇格条件）

**Date:** 2026-07-28  
**Purpose:** Partial / Blocked → **Ready** の客観条件  
**非目的:** PE 実装。Gate 通過 ≠ PE 変更許可（PE は別 Decision）。

---

## Ready の定義（再掲・厳密化）

**Ready** = 次をすべて満たす状態:

1. Sample Gate PASS  
2. Separation Gate PASS  
3. Contract Testability Gate PASS  
4. Stability / Replication Gate PASS  
5.（該当時）Residual 専用条項 PASS  

Hit / ROI / Purchase は **Ready 判定に使用禁止**。

---

## 共通数値ゲート（提案・固定）

| ID | 条件 | 根拠 |
|---|---|---|
| G-S1 | CEW ラベルで **n ≥ 40**（最低 20 は Stable だが Ready は 40） | midhole n=24 が下限不安（V75） |
| G-S2 | 評価コーパスが **2 分割以上**（例: 時系列前半/後半、または開催ブロック）で各分割 n≥15 | 単一 285R 依存の排除 |
| G-Sep1 | 対照 World との **文脈相互作用符号逆転 ≥1** が両分割で同符号 | V74 の midhole↔rank7 を再現要件化 |
| G-Sep2 | 優先特徴 Top3 の **Spearman ρ ≤ 0.70** 対 主要対照 World、または Top5 Jaccard ≤ 0.55 | 重複過大（現状 Jaccard 0.67）の低減または順位差の明確化 |
| G-Sep3 | 脚質リフトの **首位スタイルが対照と異なる**（両分割で一致） | V74 style Δ |
| G-C1 | Strategy Contract の各 MUST に **Pass/Fail 観測手順**が付き、対象レースの合否率が記録可能 | V75 MUST の計測写像 |
| G-R1 | 分割間で Top3 特徴集合の Jaccard ≥ 0.60（自己安定） | ノイズ戦略の排除 |

**注:** G-Sep2 は「差があること」の閾値。特徴セットが同じでも G-Sep1+G-Sep3 が強ければ、G-Sep2 は下記 OR 条件で緩和可能。

---

## ④ Promotion Gate

### A. Partial → Ready（Positive Worlds: rank7 / midhole）

```text
PASS :=
  G-S1 AND G-S2
  AND G-C1 AND G-R1
  AND (
        (G-Sep1 AND G-Sep3)
        OR (G-Sep1 AND G-Sep2)
        OR (G-Sep2 AND G-Sep3)
      )
```

| World | 追加固有条件 |
|---|---|
| **rank7** | MUST「field_size 減衰」の方向が両分割で r(field_size, winner_win_prob_pct) **≤ −0.05** |
| **midhole** | MUST「history 首位」が両分割で effect(history_z) > effect(win_prob_z) + **0.15** |
| **midhole** | MUST「upper_ability_band 減衰」方向が両分割で r ≤ **−0.05** |

現状（285R 単一）: **未 PASS**（G-S2 / G-C1 / 再現なし。midhole は G-S1 未達）。

### B. Partial → Ready（Residual: unsatisfied）

Residual Ready ≠ 勝ち筋 Ready。

```text
PASS :=
  n ≥ 100（現状 176 で充足）
  AND Residual Policy Contract が文書化（V75 済）
  AND G-C1（誤適用防止 MUST の測定）
  AND Positive World 誤適用率の定義とベースライン計測完了
  AND popularity 欠損時フォールバック規則の文書化 + 適用カバレッジ計測
```

現状: Policy 文書あり、**誤適用率計測・フォールバックカバレッジ未了** → 未 PASS。

### C. Blocked → Partial

```text
PASS :=
  CEW n ≥ 20
  AND Strategy Contract を PROVISIONAL→ACTIVE（草案）に更新可能
  AND 最低1つの対照 World との Separation 候補指標を記録
```

| World | 追加 |
|---|---|
| core | top_gap 平均が unsatisfied/midhole より高い、または win_prob が Top1 効果 |
| midupper | aptitude 代理の有無を明記（無なら Partial に上げても **適性欠落フラグ**付き） |
| mixed | multi_path 構成の記録（どの Primary が競合したか） |
| bug | n≥5 かつ exception 真のレースに限定 |

### D. Blocked → Ready

```text
PASS := (Blocked→Partial PASS) AND (Partial→Ready PASS)
```

一段飛ばし禁止。

---

## 現状スコアカード（285R のみ・推測なし）

| World | G-S1 | G-S2 | Sep | C1 | → Ready? |
|---|---|---|---|---|---|
| rank7 | PASS (65) | FAIL | PARTIAL（単一分割で符号あり） | FAIL | **No** |
| midhole | FAIL (24\<40) | FAIL | PARTIAL | FAIL | **No** |
| unsatisfied | n OK | N/A→要誤適用計測 | N/A | FAIL | **No** |
| core | FAIL | FAIL | FAIL | FAIL | **No** |
| midupper | FAIL | FAIL | FAIL | FAIL | **No** |
| mixed | FAIL | FAIL | FAIL | FAIL | **No** |
| bug | FAIL | FAIL | FAIL | FAIL | **No** |

---

## Gate と PE の関係

| Gate 結果 | 意味 |
|---|---|
| Ready | **PE Integration Design** を開始してよい（実装はさらに別 Decision） |
| Partial | Strategy 維持・証拠蓄積。PE 本番禁止 |
| Blocked | Strategy 仮説のみ。PE 禁止 |

Ready 達成後も **PE コードを自動変更しない**。  
