# Version46 Governance — World Trigger Migration Design

## Verdict

**Migration Design: DEFINED**  
**Implementation: NOT AUTHORIZED（本フェーズ禁止）**  
**Cutover: NOT STARTED**

V44 Specification → Production への安全移行は **S0–S8 の段階計画**として固定する。  
本文書は実装許可ではない。

---

## Authority

| 層 | 正本 | 役割 |
|---|---|---|
| Semantic | V43 | 勝ち筋の意味 |
| Trigger Spec | V44 | 移行先仕様 |
| Gap | V45 | 適合率ベースライン（平均 37% / core 0%） |
| Migration | **V46** | Stage・依存・リスク・Rollback・PASS |
| Implementation | （未発行） | 各 Stage の別承認が必要 |

---

## Stage Governance Summary

| Stage | PASS の要点 | Rollback |
|---|---|---|
| S0 | Legacy/Target/Gap 固定 | 計画中止 |
| S1 | Dual-Eval 完走 & 決定非干渉 | Shadow 停止 |
| S2 | Must Readiness 台帳完備 / Missing=Blocked | 台帳差戻し |
| S3 | Polarity/Threshold ADR Accepted | ADR Reject |
| S4 | World 別 Shadow Compliance ゲート | 前 Sub-stage へ |
| S5 | unsatisfied 一貫・silent core なし | ラベル OFF |
| S6 | Flag 切替の安全証明 + Rollback 訓練 | **Flag → legacy** |
| S7 | DEFAULT 除去・core Positive Match・再計測ゲート | Flag / リリース戻し |
| S8 | 下流は別 ADR | 下流 Flag のみ |

---

## Hard Rules

1. **S0–S5 で Production Decision を変えない**  
2. **Missing Must の World を S6/S7 に載せない**（Blocked）  
3. **S7 と S8（特に PE/Prediction）を同一切替にしない**  
4. **S6/S7 は Flag による即時 Rollback を必須装備とする（設計要件）**  
5. V46 文書の受理 ≠ 実装開始。実装は Stage ごとの実装承認後

---

## What V46 did NOT do

- コード実装
- Production / Trigger / Signal / Prediction / PE / CE / AI 変更
- Threshold 数値の確定
- Cutover の実行

---

## Artifacts

- `docs/architecture/v46-migration-plan.md`
- `docs/architecture/v46-stage-design.md`
- `docs/architecture/v46-risk-analysis.md`
- `docs/architecture/v46-governance.md`

## Expected Next Action

移行計画（V46）を前提に、**S0 受理**または **S1 実装承認**の指示待ち。  
指示なき実装開始は禁止。
