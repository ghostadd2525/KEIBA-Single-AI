# Version 3 — Production Risk Assessment

**Date:** 2026-07-24  
**Review ID:** `v3-production-readiness-review/1.0`  
**Parent:** [`v3-production-readiness-report.md`](./v3-production-readiness-report.md)  
**Decision:** **HOLD**

---

## 1. スコープ

Lab Baseline v3（A-01 + A-03 + A-04）を本番候補とした場合のリスク。  
本文書は机上評価のみ。配線・Flag 変更は行わない。

---

## 2. リスク一覧

| ID | リスク | 等級 | 可能性 | 影響 | 現状緩和 | 残ギャップ |
|----|--------|------|--------|------|----------|------------|
| **R1** | 合成 Lab 形状が実レースに外挿できない | **高** | 中 | Hit/ROI 過大評価 | Taxonomy 固定 · Phase 2 設計で認識済 | 実 285R 未実施 |
| **R2** | A-04 Validation 欠如 | **解消** | — | — | Validation **PASS**（2026-07-24） | なし（Lab 再現性は充足） |
| **R3** | `history_score` 欠測・ノイズで誤 promote | **中** | 中 | Clear field での churn | crowding≥0.40 ∧ hist_gap≥0.15 | 本番特徴品質未検証 |
| **R4** | V2 PE-V2-A と V3 の二重適用 | **高** | 低※ | Control 破壊 | 現状未配線 · 別名前空間 | Mesh/経路分離の実装なし ※配線後は高 |
| **R5** | Explain / UI が旧 pick 根拠のまま | **中** | 高（配線後） | ユーザー信頼低下 | Explain 変更禁止中 | 同期計画未承認 |
| **R6** | A-03 promote と A-04 promote の相互作用 | **中** | 低 | Pool 回収の退行 | Lab 上 churn vs v2 = 0 | 実データでの再確認必要 |
| **R7** | D2（A-02）誤 ON | **中** | 低 | Eval 破壊（既知） | 同時 ON 禁止 · Secondary | Ops 手順・ガード未配線 |
| **R8** | Purchase / Delete 境界の意図せぬ変更 | **低** | 低 | 製品方針違反 | Purchase Baseline · Delete 対象外 | 配線時の不変テスト必須 |
| **R9** | レイテンシ悪化 | **低** | 中 | SLA | Lab のみ | p95 計測なし |
| **R10** | Flag 既定値の誤変更デプロイ | **高** | 低 | 全量即時影響 | 既定 OFF · Review で非変更 | CI で default-OFF 検査推奨 |

---

## 3. リスクヒートマップ（要約）

```text
        影響 →
       低      中      高
可 低  R8     R9     R4※ R7 R10
能 中  —      R3 R5R6  R1
性 高  —      —       —（R2 は Validation PASS で解消）
```

※ R4 は「未配線の今」は可能性低、「配線後」は可能性・影響とも高。  
R2（A-04 Validation 欠如）は 2026-07-24 に解消。HOLD 残は主に R1（実データ外挿）と経路分離。

---

## 4. HOLD に直結するブロッカー

| Blocker | 状態 |
|---------|------|
| B1 実データ外挿 | **FAIL**（[`v3-offline-gate-report.md`](./v3-offline-gate-report.md) · Hit 59→42 · churn 29） |
| B2 A-04 Validation | **解消**（PASS） |
| B3 経路分離設計 | **未実施** · Offline Gate FAIL により Shadow 着手不可 |

HOLD は B1 FAIL により継続・強化。B2 のみクローズ。

---

## 5. 受容可能な残リスク（配線後も）

| 項目 | 扱い |
|------|------|
| Delete 6 | 製品境界 · Accuracy 非対象のまま受容 |
| A-02 非採用 | Secondary 保持 · スタック外 |

---

## 6. 停止

本 Risk Assessment は Review の一部として完了。追加実装は行わない。
