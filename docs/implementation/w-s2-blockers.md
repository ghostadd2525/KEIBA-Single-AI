# W-S2 Blockers

**Date:** 2026-07-28  
**Version:** 58  
**Parent:** `w-s2-readiness.md`  
**Scope:** W-S2 **開始**を妨げる条件の列挙（改善案なし）

---

## Legend

| Class | Meaning |
|---|---|
| **Hard Blocker** | W-S2 Decision Gate を開けない |
| **Soft Condition** | 開始可だが遵守必須（違反なら即停止） |
| **Not a Blocker** | 問題だが S2 開始条件ではない（後段 Stage） |
| **S2 Output** | S2 実施の結果として記録されるもの（開始前ブロッカーではない） |

---

## Hard Blockers（現時点）

| ID | Condition | Status |
|---|---|---|
| H1 | W-S1 未 PASS | **Clear**（PASS済） |
| H2 | Production Decision を S2 で変更する計画が混入 | **Clear if** 本 Gate 条件を守る |
| H3 | Signal 生成・Trigger 実装を S2 必須成果にする要求 | **Clear if** V46 定義どおり台帳のみ |

→ **現時点の Hard Blocker は無し**（条件遵守前提）。

---

## Soft Conditions（条件付き開始の中身）

| ID | Condition | Why |
|---|---|---|
| S1 | 成果を Readiness 台帳に限定 | V46 S2 範囲 |
| S2 | Exclusion 104 を「S2 で解消」しない | V57: 設計×極性 → S3 |
| S3 | `exception_flag` Missing を前提に bug を S4 Blocked 候補へ | V46 S2 PASS 条項 |
| S4 | aptitude 等 Proxy-only を S3 待ちリストへ | V46 S2 PASS |
| S5 | Unsatisfied 率を S2 失敗 KPI にしない | S2 は供給判定 Stage |
| S6 | Track P / PE / Prediction 変更を同時に入れない | V54 Downstream Isolation |

違反時: W-S2 を中断し、No-Go（C）相当へ格下げ。

---

## Not a Blocker（後段へ持ち越し）

| ID | Finding | Defer to |
|---|---|---|
| N1 | Exclusion after Must = 104 | S3 Polarity ADR |
| N2 | must∧¬exclude = 0 | S3 / Shadow 再評価 |
| N3 | Unsatisfied 61.8% | S4–S5 後の観測 KPI |
| N4 | Legacy vs V44 分布差 | Shadow 継続（S1維持） |
| N5 | 極性1軸 Near Miss 63 | S3 後の Shadow 再計測 |
| N6 | mixed multi_path 論理 | Spec 維持；S2 では Missing/定義可能性として記録 |

---

## S2 Outputs（開始後に出すべきもの — ブロッカーではない）

| Output | V46 PASS 対応 |
|---|---|
| 全 Must に Ready / Proxy-only / Missing | 必須 |
| Missing World → S4 Blocked 明示 | 必須（bug が典型） |
| Proxy-only → S3 待ちリスト | 必須 |

---

## 72件・104件と Blocker の関係

| Cohort | Blocks W-S2 start? | Role in S2 |
|---|---|---|
| 104 Exclusion | **No** | Must 到達証拠 → Ready/Proxy 判定材料；Exclude は S3 |
| 72 Must失敗 | **No** | gaps から Missing/Proxy 台帳化の主材料 |

---

## Go 判定との対応

- Hard Blocker 無し + Soft Conditions 受諾 → **B 条件付き開始**（`w-s2-governance.md`）  
- Soft Conditions 拒否（実装・Cutover 要求）→ **C 開始禁止**

*Blocker inventory only. No implementation.*
