# Version 3 — Phase 2 Miss Taxonomy

**Date:** 2026-07-24  
**Scope:** Research Design（ラベル体系 · 実装なし）  
**Control:** Hit 218 / Miss 67（285R）  
**根拠コーパス:** Unified Review `rev-285-*` + Phase 1 Taxonomy Lock  

> **更新:** Lab Baseline v2 採用後の残 miss 再凍結は  
> [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md)（Gap Analysis v2）を正とする。  
> 本ドキュメントは A-03 以前の Phase 2 設計時点のスナップショット。

---

## 1. 残 miss 全体図（Phase 1 後）

```text
Control miss 67
├── Recovered by A-01 only …… 28 (Eval)
├── Recovered by A-02 only …… 24 (Boundary 14 + Reorder 10)
├── Recovered by both ……… 0
└── Remaining ……………… 15
      ├── Pool …………… 9   ← Phase 2 主戦場
      └── Delete ……… 6   ← 不変
```

理論上の union 上限 Hit = 218 + 52 = **270**（stack なしの個別上限は A-01=246 / A-02=242）。  
残 15 のうち Accuracy が触れるのは **Pool 9** のみ。

---

## 2. 層定義（Phase 2 版）

| 層 ID | 名称 | 定義（操作的） | Phase 1 状態 | Phase 2 |
|-------|------|----------------|--------------|---------|
| L-Eval | Evaluation | 場内に勝者はいるが、校正不足で top pick が外れる | A-01 で回収済（本 Lab） | 実データ再検証 |
| L-Boundary | Boundary | トップ近傍混雑 · survivor≈容量境界 | A-02 で回収済 | 一般化 |
| L-Reorder | Reorder | 枠内にいるが順序/圧縮副作用で外れる | A-02 で回収済 | Selection 接続は別承認 |
| L-Pool | Pool | 勝者が候補場の外側（遠位 rank） | **未回収** | **A-03 主対象** |
| L-Delete | Delete | 購入/削除境界 | 不変 | **非対象** |
| L-Other | その他 | 上記に入らない・ラベル不明 | — | 実 285R 再分類 |

---

## 3. 残 Pool miss の観測特徴（Lab）

| 項目 | 典型値 |
|------|--------|
| n | 9 |
| winner_rank | 8–10 |
| field_size | 12 |
| winner win_prob | ≈0.03–0.05 |
| top win_prob | ≈0.24 |
| winner odds | ≈35–55 |
| history 優位 | なし（勝者 hist ≪ top） |

**解釈:** D1/D2 が使う「場内相対・校正」信号では勝者を持ち上げられない。  
原因仮説は (a) Admission 容量不足 (b) Representation が遠位を区別できない (c) 両方。

---

## 4. 残 Delete miss

| 項目 | 典型値 |
|------|--------|
| n | 6 |
| winner_rank | 5 |
| purchase_eligible | false |

製品方針により Accuracy 改善対象外。Purchase / Delete Boundary を変更しない。

---

## 5. Phase 2 での Taxonomy 作業

| 作業 | 目的 |
|------|------|
| 実 285R 再ラベル | Lab 合成形状の外挿リスク除去 |
| Pool 下位区分 |「未 admit」vs「admit 済だが評価不能」|
| Eval 残余の有無 | 実データで A-01 後に Eval が残るか |
| Other バケット | ノイズ・異常レースの隔離 |

---

## 6. 成功指標との接続

| 目標 | Taxonomy 含意 |
|------|----------------|
| Hit > 246 | Pool（または実データの未回収 Eval/Boundary）を動かす必要 |
| churn = 0 | Control/A-01 既存 Hit を壊さない |
| Delete 不変 | L-Delete を実験から除外 |
