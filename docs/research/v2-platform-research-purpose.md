# Version2 Platform Research — Purpose Lock（未開始）

**Date:** 2026-07-29  
**Status:** **PURPOSE LOCK ONLY** · Version2 Platform Research = **未開始** · 実装 **禁止**  
**Separation:** Version1 Platform Contract と **完全分離**  
**Does not modify:** ADR-009 · ADR-010 · ADR-011 · PLATFORM-V1

---

## 1. 本票の位置づけ

Version2 の **正式開始 Gate ではない**。  
開始時に参照する **研究目的のロック**である。

- Version1 の運用・契約・コード経路に混入しない
- Version1 名義で Version2 仮説を実装しない
- 開始には別途「Version2 Platform Research 正式開始」承認が必要（PLATFORM-V1 条件 #4）

---

## 2. Version2 研究目的（確定）

> **「`unsatisfied` が現在の World 定義の限界なのか、  
> あるいは新しい World 構造によって自然に分類可能なのか」を検証する。**

| 問い | 意味 |
|---|---|
| Q1 | 現行 CEW / Trigger 定義の限界として `unsatisfied` が不可避か |
| Q2 | 新しい World Theory / 構造により、自然に分類し得るか |
| Q3 | その検証に必要な観測は何か |

成功は ROI でも Positive 昇格率でもない。**理論の妥当性検証**である。

---

## 3. 明示的に採用しない目的

| 非目的 | 理由 |
|---|---|
| Affinity による Positive World **昇格** | 昇格ルール研究ではない |
| Near Miss を新 CEW World として追加して件数削減 | V1 RT-X1 と混同しやすい。V2 でも「昇格ルール」としては定義しない |
| V1 本番 CEW の黙った置換 | V1/V2 分離違反 |
| Ticket / ROI / Decision 最適化 | Completeness / Theory 範囲外 |

---

## 4. Near Miss / Affinity の扱い（V2）

| 概念 | V2 での扱い |
|---|---|
| Near Miss | **新しい World Theory を検証するための観測** |
| Affinity | 同上 |
| Residual | 同上 |
| 昇格ルール | **しない**（観測 ≠ 割当アルゴリズムの採用決定） |

観測結果が「新構造で自然分類できる」仮説を支持しても、  
**V1 契約への自動反映は禁止**。反映は別の移行 Gate。

---

## 5. Version1 との完全分離

| 軸 | Version1 | Version2 |
|---|---|---|
| Contract | PLATFORM-V1 FROZEN | 未開始 · 別プログラム |
| `unsatisfied` | **許容**（所属） | 研究対象（限界 vs 新構造） |
| Prediction Returned | **100% 目標** | 本票の主目的ではない |
| NM / Affinity | 昇格禁止 · Completeness 観測 | 昇格ルールにしない · Theory 観測 |
| コードベース | 本番安定経路 | 研究ブランチ / 別成果物（開始後） |
| ADR-009/010/011 | **維持** | 改訂するなら V2 プログラム内の新 ADR |

```text
┌─────────────────────┐     ┌──────────────────────────┐
│ Version1 Platform   │     │ Version2 Research (future)│
│ FROZEN · 運用       │  ≠  │ Purpose locked · 未開始   │
│ Prediction Returned │     │ World Theory 検証         │
└─────────────────────┘     └──────────────────────────┘
         混線禁止（文書・Flag・経路・KPI）
```

---

## 6. 正式開始時に必要なもの（予告）

開始 Gate で最低限:

1. 本 Purpose の再確認
2. 研究ブランチ / 成果物名前空間の分離宣言
3. V1 非干渉の証明方法（Shadow only 等）
4. 終了条件（Q1/Q2 への回答形式）

**現時点では開始しない。**

---

## Related

- `v110-prediction-completeness-charter.md`（V1 解釈 A）
- `PLATFORM-V1-CONTRACT.md`
