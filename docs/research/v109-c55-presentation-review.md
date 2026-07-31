# Version109 Phase C5.5 — Presentation Review

**Date:** 2026-07-29  
**Source:** Shadow `presentation-bundle/v1` · fixture `ux-r1`

---

## 表示順

| # | key | JA label | 評価 |
|---|---|---|---|
| 1 | world | ワールド | 先頭で状況が分かる |
| 2 | near_miss | ニアミス | World 直後で残余の性質が分かる |
| 3 | affinity | 親和度 | 数値は追える。注記あり |
| 4 | explanation_confidence | 説明確信度 | disclaimer 必須・実装済み |
| 5 | exclusion | 除外理由 | 構造は良い。id が生 |
| 6 | transition | 遷移 | 末尾で十分 |

**表示順 Verdict:** PASS（契約どおり固定）

---

## 説明量

| 項目 | 観察 | 判定 |
|---|---|---|
| セクション数 | 6 | 過多でない |
| ラベル長 | 2–6 文字級 | 適切 |
| 散文 | なし（null） | C2 遵守。利用者は「短文ストーリー」を期待する場合ギャップ |
| EC 軸 | 5 軸 + disclaimer | 上級者向け。一般 UI は総合値+disclaimer で足りる |
| Affinity ベクトル | 4 値 | 一覧表示は折りたたみ推奨 |

**説明量 Verdict:** ACCEPTABLE

---

## 誤解防止

| リスク | 対策（実装） | 判定 |
|---|---|---|
| EC=勝率 | disclaimer | PASS |
| Affinity=自動 Skip | 表示専用ノート | PASS |
| Near Miss=rank7 本採用券 | Ticket は conservative top1 | PASS |
| 除外 id を文章と誤認 | id のまま | NOTE |

---

## Localization

| locale | world label 例 |
|---|---|
| ja | 未充足（残余） |
| en | Unsatisfied residual |

短ラベル切替は機能している。

---

## 改善候補（Core 非変更・任意・本フェーズ非実装）

1. Exclusion reason id → Presentation 用短ラベル辞書（Consumer KEEP_DERIVED）  
2. UI で EC は総合値のみ、軸は詳細開閉  
3. warnings は開発者コンソール専用  

いずれも Semantic / Contract 変更ではない。
