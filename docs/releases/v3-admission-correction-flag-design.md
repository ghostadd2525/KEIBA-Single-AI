# Version 3 — Admission Correction Feature Flag Design

**Date:** 2026-07-24  
**Status:** Design Only · **Flag 未追加 · 既定値変更なし**  
**Parent:** [`v3-admission-correction-design.md`](./v3-admission-correction-design.md)

---

## 1. 予約 Flag

| Flag 名 | 既定値（設計） | Stage | Candidate |
|---------|----------------|-------|-----------|
| `F_V3_A05_ADM_FAVSAFE_ENABLED` | **False** | Admission | A-05 |

**本 Round では `flags.py` に追加しない。**

---

## 2. 既存 Flag との関係

| Flag | 既定 | A-05 設計上の扱い |
|------|------|-------------------|
| `F_V3_A03_POOL_ADMIT_ENABLED` | False | **凍結** · A-05 Primary 実験と同時 ON 禁止 |
| `F_V3_A01_*`（D1） | False | Stack-A05 で ON 可（Evaluation コード非変更） |
| `F_V3_A04_SEL_HISTORY_ENABLED` | False | Stack-A05 で ON 可（Selection コード非変更） |
| `F_V3_A02_*` | False | Secondary 維持 · A-05 と無関係に同時 ON 禁止ルール継承 |

---

## 3. 相互排他ルール

```text
assert not (A03_ON and A05_ON)  # Primary / Offline Hard Gate
```

| 組合せ | 許可 |
|--------|------|
| A-05 only | Yes |
| A-01 + A-05 | Yes |
| A-01 + A-05 + A-04 | Yes（置換スタック） |
| A-01 + A-03 + A-04 | Yes（現行 Baseline v3 参照） |
| A-03 + A-05 | **No** |
| いずれかの既定 True | **No**（本番・リポジトリ既定） |

---

## 4. 配線方針（実装 Round · 予約）

| 層 | 方針 |
|----|------|
| Lab `stages.py` | A-03 分岐の隣に A-05 分岐を追加（A-03 分岐は残す） |
| Production / API / UI | **配線しない**（本設計・次 Accuracy でも原則 HOLD） |
| Mesh / Shadow | PRR HOLD 解除後の別承認 |

---

## 5. Rollback 設計

| 状況 | 操作 |
|------|------|
| A-05 実験失敗 | Flag OFF · A-05 コードは残しても既定 OFF |
| 誤って同時 ON | Harness が Hard Fail |
| Baseline 戻し | A-03 Flag 経路を参照（A-03 非削除） |

---

## 6. Naming / Contract

| 項目 | 値 |
|------|-----|
| Policy ID | `AP-V3-A05-favorite-safe-coverage` |
| Contract | `v3-lab-admission/2.2`（予約） |
| Journal `policy_id` | 上記と一致 |

---

## 7. Stop

Flag 設計のみ。コード追加・既定値変更は行わない。
