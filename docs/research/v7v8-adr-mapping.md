# ADR Mapping — Version7/8 ↔ ADR-009 / ADR-010 / V103

**Date:** 2026-07-28

---

## 凡例

| 記号 | 意味 |
|---|---|
| ✅ 既に実現 | 文書/コードで同趣旨が確認できる |
| ≈ 近似 | 目的は近いが対象が違う |
| 🔄 再設計 | 後続で意味・境界が作り直された |
| ❌ 失われた / 不在 | 当該スコープに根拠なし |
| ➕ 追加 | V7/V8 に無く後続で導入 |

---

## Product Version7–8 → 現行

| 項目 | V7/V8 根拠 | 現行 | マッピング |
|---|---|---|---|
| Prediction 読取専用 | ADR-003 | ADR-009 維持 | ✅ |
| PE/CE 本番変更禁止 | Version8.5 Baseline / v8-ops | ADR-009 Core 非利益 | ≈（凍結運用） |
| Miss Evidence 蓄積 | RA `EVIDENCE_EXPORTING` | Completeness Evidence | 🔄 対象再設計 |
| Friday Decision | Accept/Reject proposal | ADR-008 Ticket Decision | 🔄 同名異義 |
| Betting / Skip / 資金 | 根拠なし | Decision 側（V93, ADR-009 外） | ➕ |
| World Completeness | 根拠なし | ADR-009 | ➕ |
| Near Miss Completeness | 根拠なし | ADR-009 / V95 | ➕ |
| Affinity | 根拠なし | V96 / V103 PROMOTE | ➕ |
| Explanation Confidence | 根拠なし | ADR-010 | ➕ |
| Contract Surface PROMOTE | 根拠なし | V103 | ➕ |

---

## Research Version70–89 → 現行

| 項目 | V70–V89 根拠 | 現行 | マッピング |
|---|---|---|---|
| CEW / World Label Rule | V72–V73 | ADR-009 World Completeness 入力 | ✅ → 再配置 |
| World Strategy Contract | V75 | Semantic 固定の祖先 | ✅ ≈ |
| World Evidence 棚卸し | V76 | Completeness 監査の祖先 | ≈ |
| Decision Layer 設計 | V88–V89 | ADR-008 | ✅ |
| Decision M1 Shadow | V91 | ADR-008 実装 Shadow | ✅（V89 直後） |
| Prediction Confidence Calibration | V84 | ADR-010 では **排除** | 🔄 定義転換 |
| Near Miss / Affinity | （V70–V89 に成果物なし） | V94–V96 | ➕ |
| Core Completeness Charter | なし | ADR-009 | ➕ |
| Explanation Confidence | なし（V84≠EC） | ADR-010 | ➕ |

---

## ADR 系列の位置

```text
ADR-003 Prediction Read-Only     … Product V4/会話、V8 でも有効
ADR-006 Memory Layer             … ユーザー Memory（World Evidence ではない）
ADR-007 AbilityScores Overlay    … Version8.5.1
ADR-008 Decision Layer           … Research V90（V88–V89 が親）
ADR-009 Core Completeness        … V99（親: ADR-003/008 + V94–V98）
ADR-010 Explanation Confidence   … V101（親: ADR-009 + V100）
```

---

## 重要な同名異義

| 語 | Product V8 | Research / ADR-008+ |
|---|---|---|
| Decision | 改善提案の採否 | Ticket / Pool / Risk / Explain |
| Evidence | Miss（予測外れ） | Completeness / World Ready 証拠 / Snapshot |
| Confidence | Analyzer の予測誤差文脈等 | ADR-010 = Explanation Confidence |
