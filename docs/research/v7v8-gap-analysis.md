# Gap Analysis — Version7/8 → ADR-009 / ADR-010 / V103

**Date:** 2026-07-28

---

## 分類サマリ

| 区分 | 内容 |
|---|---|
| **既に実現済み** | Prediction 非改変（ADR-003）; Product V8 の Miss Evidence パイプライン; Research V75 Contract 固定; Research V88 Decision Layer 設計 |
| **再設計された** | Evidence の対象（Miss→Completeness）; Decision の意味（採否→券種層）; Confidence の意味（Calibration→Explanation） |
| **失われた（Product V8 観点）** | なし（ADR-009 は Product Evidence を廃止していない。併存・非置換） |
| **追加された** | Near Miss / Affinity / Explanation Confidence / Completeness KPI / Contract Surface PROMOTE |

---

## 詳細

### 既に実現済み（根拠付き）

1. **Prediction を他層が書き換えない**  
   - ADR-003; `v8-self-improvement-cycle.md` Non-goals  
2. **本番中に Core を自動改善しない**  
   - `v8-self-improvement-cycle.md` 「本番中は AI を改善しない」  
3. **観測データの蓄積→研究**  
   - ResultAutomation Evidence Export（ただし Miss）  
4. **World 意味の文書固定（Research）**  
   - `v75-world-strategy-contract.md`  
5. **Prediction と購入 Decision の分離（Research）**  
   - `v88-decision-policy.md` → ADR-008  

### 再設計された

| From (V7/V8 帯) | To (現行) | 根拠 |
|---|---|---|
| Miss Evidence = 改善入力 | Completeness / EC = Core KPI | ADR-009; V100; 対照: RA `hit_at_1=0` |
| Decision = Accept/Reject | Decision = Ticket/Risk/Pool/Explain | `v8-operations-baseline.md` vs ADR-008 |
| Confidence ≈ Calibration/予測確度（V84） | Explanation Confidence | ADR-010; V84 は親に残すが定義転換 |

### 失われたか？

Product V8 Evidence / 週次サイクルを ADR-009 が **削除した根拠はない**。  
ギャップは「無いものを失った」ではなく **別レイヤが後から定義された**。

### 追加された（V7/V8 Product に根拠なし）

| 追加 | 初出根拠（本監査で確認） |
|---|---|
| Near Miss Taxonomy | V94–V95 |
| Affinity | V96 |
| Explanation Confidence | ADR-010 / V101 |
| Core Completeness Charter | ADR-009 / V99 |
| Contract Surface PROMOTE 集合 | V103 |
| Betting Policy 最適化 | V93（Decision 側） |

---

## ADR-009 思想は V7/V8 に「既にあった」か？

| 要素 | 判定 |
|---|---|
| 利益最大化しない / Completeness | Product V8 は Hit Miss 改善が Research 目的の一部 → **未一致** |
| レースを完全に記述 | Product V8 主文書に **根拠なし** |
| Evidence で成長 | **近似あり**（Miss Evidence）だが対象が異なる |
| Decision は Single/Win5 | Ticket 層としては **V88+**。Product V8 Decision は別物 |

**結論:** ADR-009 の中核（記述 Completeness）は Product Version7–8 に **既存在しない**。  
Research V72–V76 の Contract/Evidence 棚卸しが **部分的祖先**。完成形は V99–V100。

## ADR-010 思想は V7/V8 に「既にあった」か？

| 要素 | 判定 |
|---|---|
| Confidence = 説明の完全性 | Product V8 / Research V70–V89 に **根拠なし** |
| Prediction Confidence を Core が返さない | ADR-003 は Conversation 側の非改変。Core EC 定義は **ADR-010 が追加** |

**結論:** ADR-010 は **新規定義**。V84 Confidence は Calibration であり同一ではない（ADR-010 本文も Prediction/Calibration を排除）。
