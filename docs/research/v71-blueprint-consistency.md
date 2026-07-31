# Version71 — Blueprint Consistency（V69 ↔ Intent GT）

**Date:** 2026-07-28  
**Parent:** `v71-intent-gt-audit.md`  
**Question:** V69 Blueprint と Intent GT は一貫した成功定義か？

---

## Verdict

**不一致（Inconsistent Measurement）。**

V69 は V43/V44 の Positive Match を Shadow 実装する Blueprint である。  
Intent GT は V44 Logic Form を意図的に除外し、winner_rank 帯を主軸にした別メトリクスである。  
したがって **「V69 が Blueprint どおりか」を Intent Accuracy で判定することは妥当でない。**

---

## Consistency Matrix

| Blueprint 主張（V69） | Intent GT が測ること | 一貫？ |
|---|---|---|
| R7 = UPPER∧DEV∧APT（difficulty Aux） | midupper = wr∈[2,6] | **No** |
| R1 = multi_path（pressure Aux） | mixed = outcome 強スコア 2+ | **No** |
| R8 = Positive Match core（DEFAULT 廃止） | core = Gap∧Sep∧wr≤3（DEFAULT 非観測） | **No**（目的が違う） |
| \|M\|=0 → unsatisfied 正当 | unsatisfied を Acc の外れとして罰する | **No** |
| rank7 = V44 Chaos Form | rank7 = gap↓∧wr 7–10（n=7） | **No** |

---

## V70 数値との対応（一貫性チェック）

| V70 KPI | Blueprint 期待 | Intent GT 下の見え方 | 一貫な読み |
|---|---|---|---|
| DEFAULT core 104→0 | 構造成功 | Acc に寄与しない／悪化要因になりうる | Blueprint ✓ / GT 測定 ✗ |
| difficulty-only midupper = 0 | 構造成功 | GT は difficulty 非参照 | Blueprint ✓ / GT 非感度 |
| rank7 Recall 0→0.857 | Form 改善の兆し | support=7 の outcome 帯のみ | **限定的**・GT 定義依存 |
| Intent Acc 0.221→0.088 | （PASS 条件） | Outcome GT vs Positive Match | **測定失敗**（Blueprint 非難不可） |
| V65 Shadow↔Intent 8.8% = V70 | — | 同一 | Positive Match 系と GT の固定ギャップ |

### V70 不一致 Top（GT→V69）根拠

| GT → V69 | n | Consistency 注記 |
|---|---:|---|
| midupper → unsatisfied | 52 | GT は rank 帯; V69 は APT/DEV Must 欠落で unsatisfied になりうる |
| core → unsatisfied | 42 | GT は wr≤3; V69 は Exclude / Must 欠落で unsatisfied |
| midhole → unsatisfied | 30 | 同上 |
| midupper → rank7 | 26 | GT midupper(wr2–6) vs V69 chaos Form |

---

## 何が一貫しているか（肯定）

1. **V43 ↔ V44 ↔ V69:** midupper 3-AND / core Positive Match / mixed multi_path / DEFAULT 禁止 — 文書上一致。  
2. **V70 構造 KPI:** DEFAULT 除去・difficulty 単独除去は V69 自己整合。  
3. **V65 自己注記:** Logic Form を GT にしない — GT 側が Blueprint 非準拠であることを既に宣言。

---

## 何が一貫していないか（否定）

1. Intent Accuracy を V69 PASS 条件にしたこと（V70 Gate）。  
2. Intent GT が V43 Required Signals を World ごとに欠落させていること。  
3. bug / rank7 の Must 定義が Outcome に置換されていること。

---

## 監査上の含意（実装提案はしない）

- Soft/Cutover の Intent Acc ゲートは、**GT 再定義または別 KPI**なしでは Blueprint 成功を測れない。  
- 現状 GT のまま Trigger を「Intent Acc 改善」方向へ寄せると、V43/V44 Forbidden（difficulty のみ、DEFAULT 等）へ回帰するリスクがある（方向注意のみ。改修は本フェーズ外）。
