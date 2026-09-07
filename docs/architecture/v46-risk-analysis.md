# Version46 — Migration Risk Analysis

**Date:** 2026-07-28  
**Parent:** `v46-migration-plan.md`  
**Type:** Design only

## Risk Scale

| Level | Meaning |
|---|---|
| L0 | 観測のみ。Production 決定不変 |
| L1 | 限定 Flag。Rollback 即時 |
| L2 | 決定経路変更。World 分布が変化しうる |
| L3 | 下流（Pool/Role/PE 等）へ伝播し Prediction 面に影響しうる |

---

## Per-Stage Breaking Risk

| Stage | Risk | Production Decision | 影響モジュール（設計上の波及） | 主リスク |
|---|---|---|---|---|
| S0 | L0 | No | docs / governance | なし |
| S1 | L0 | No | research Shadow / ログ容量 | Dual-Eval 負荷。決定非干渉の破綻 |
| S2 | L0 | No | research Readiness 台帳 | Missing を無視して先へ進む政治的リスク |
| S3 | L0* | No | architecture ADR | 悪い極性契約が後段を汚染 |
| S4 | L0 | No | Shadow レポート | World 別最適化の過適合（Shadow のみ） |
| S5 | L0 | No | Shadow ラベル | unsatisfied 比率の誤解釈 |
| S6 | **L1–L2** | Flag ON 時 Yes | `classify_world_line_type` 呼び出し側全般（World ラベル消費者） | ラベル急変、SubWorld/Role/Pool 不整合 |
| S7 | **L2** | Yes | World 決定層 + core 比率大幅変化 | DEFAULT 除去による core 崩壊 / unsatisfied 増 |
| S8 | **L2–L3** | 条件付き | SubWorld, Role, Required, Candidate Pool,（将来）PE/Prediction | 勝ち筋が PE に届くと Prediction が動く（V35/V36） |

\* S3 自体は L0。誤った ADR を S6 以降に適用すると実効 L2。

---

## Modules Potentially Affected（呼び出し面）

Production Trigger（`classify_world_line_type`）変更が触れうる設計上の消費者:

| Module / 領域 | S1–S5 | S6–S7 | S8 |
|---|---|---|---|
| World ラベル決定そのもの | 観測 | **直接** | 安定前提 |
| SubWorld 分類 | 間接（入力 World） | **高** | 再契約 |
| Role / Required | 低（未結合なら） | 中 | 再契約 |
| Candidate Pool | 低〜中 | **高** | 再契約 |
| CE / facade メタ | 低 | 中（表示・監査） | 中 |
| PE / Scorer / Ranker | **対象外（同時改修禁止）** | ラベル供給のみ変化しうる | V36 I3 は別 ADR |
| Prediction / AI モデル | **対象外** | 直接変更しない | 別計画 |
| Signal 生成 / CSV | S2 は Readiness のみ | Signal 変更は別承認 | — |

---

## Highest-Risk Transitions

### 1. S6 Soft Cutover
- **何が壊れるか:** World 分布が V45 で観測された core 偏重から Spec 分布へ急変しうる  
- **緩和（設計）:** Flag 既定 OFF、範囲限定、Rollback 訓練必須  
- **Rollback:** Flag → legacy

### 2. S7 DEFAULT Removal
- **何が壊れるか:** 旧来「どれにも非該当 ⇒ core」に依存した下流仮定が破綻  
- **緩和（設計）:** S4.6 + S5 PASS 必須、unsatisfied の明示契約、core Must Ready  
- **Rollback:** Flag legacy → 必要ならリリース戻し

### 3. S8 Downstream / PE
- **何が壊れるか:** V35 のとおり World→PE が繋がると Prediction が動く  
- **緩和（設計）:** Trigger 移行（S7）と PE 接続を **同一リリースに載せない**  
- **Rollback:** 下流 Flag のみ戻し、Trigger は維持可

---

## Risk by World（S4/S6/S7）

| World | Cutover Risk | Reason |
|---|---|---|
| rank7 | 低〜中 | Compliance 最高。Must 部分一致 |
| bug | 中 | exception_flag Missing なら Blocked |
| mixed | 中〜高 | multi_path と first-match の意味差 |
| midupper | 高 | 3 Must 欠落 + difficulty-only Forbidden |
| midhole | 高 | Aux 昇格の解消で分布激変しうる |
| core | **最高** | Compliance 0%。DEFAULT 依存が全域 |

---

## Non-Interference Guarantee（S0–S5）

設計上の保証条件:

- Production の World 決定関数の戻り値を変えない  
- Prediction / PE / CE / AI / Signal / CSV を変えない  
- Shadow 失敗は Production に伝播しない  

これが破られた場合、当該 Stage は自動 FAIL・即 Rollback（Shadow 停止）。

---

## Residual Risks（計画に残るもの）

1. Must 概念が Missing のまま政治的に Cutover されるリスク → S2 Blocked 規則で防止  
2. Threshold ADR（S3）の誤り → S4 Shadow で検出、S3 Reject 可能  
3. Flag 忘れ（S6 既定 ON）→ PASS に「Flag OFF 一致」を必須化  
4. S8 を急ぐことによる Prediction 回帰 → S7 と S8 の分離を硬制約
