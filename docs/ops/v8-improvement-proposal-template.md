# Version 8.5 — Improvement Proposal Template

**Baseline Lock:** Version8.5  
**ルール:** 新 Research 機能は原則提案しない。以下の条件をすべて満たす場合のみ提出。

---

## 1. 提案条件チェック

| # | 条件 | 満たす？ | 根拠リンク |
|---|------|----------|------------|
| 1 | 実運用で不足が確認された | ☐ | |
| 2 | KPI 改善につながる Evidence がある | ☐ | |
| 3 | 285R Baseline で改善可能性が確認できた | ☐ | |

3 つすべて ☐ でなければ **提案しない**（Version8.5 維持）。

---

## 2. 必須添付

### 根拠 Evidence

- パス / week_id:
- Miss / Root Cause / Archive 参照:

### KPI 比較

| 指標 | 現状 | 提案後想定 | 差分 |
|------|------|------------|------|
| Hit | | | |
| Purchase | | | |
| rank710 | | | |
| other_miss | | | |
| rank46 | | | |

### 285R Baseline 比較

| 項目 | 値 |
|------|-----|
| baseline_id | formal-285r-offline-corpus |
| measured_delta_hit_at_1（現状） | |
| measured_delta_hit_at_1（提案 Canary） | |
| verdict | |

### 想定 ROI

| 項目 | 内容 |
|------|------|
| 期待改善（Hit pp 等） | |
| 実装コスト（人日） | |
| リスク（Validation / Canary） | |
| ROI 判定 | 採用 / 見送り |

---

## 3. 禁止事項（再確認）

- [ ] PE ロジック変更なし  
- [ ] CE ロジック変更なし  
- [ ] AI ロジック変更なし  
- [ ] Production DB 直接更新なし  
- [ ] Core Hot Patch なし  

---

## 4. Decision への接続

提案は Research サイクル（Validation → Canary → 285R → Decision）を通過した場合のみ検討。  
`decision = no_improvement` の週は提案を強制しない。
