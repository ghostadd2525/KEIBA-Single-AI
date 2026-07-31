# Version 4 Handover（from Version 3）

**Date:** 2026-07-24  
**Status:** Handover Only · **Version 4 未着手**  
**Source Close:** [`v3-close-report.md`](./v3-close-report.md) · [`v3-final-report.md`](./v3-final-report.md)

---

## 1. 引継ぎ宣言

Version 3 は CLOSED。本文書は Version 4 企画のための引継ぎ事項のみを記す。  
**本 Round では Version 4 を開始しない。**

---

## 2. 必ず引き継ぐ決定

| 項目 | 内容 |
|------|------|
| Official Admission Candidate | **A-05** |
| A-03 | **Deprecated · 再挑戦して本番投入しない** |
| PRR at V3 Close | **HOLD** |
| Immediate prod | **NO-GO** |
| Integration | Design Complete（実装は V4/別プログラム） |
| Flag defaults | すべて **OFF** |

---

## 3. 推奨スタート地点（V4）

1. Integration Design の **実装**（API · Purchase · Ops · Mesh）  
2. Staging Rollback ドリル  
3. PRR 条件付き GO  
4. Canary（A-05 + A-01 ± A-04）  
5. 公式 Baseline 再発行（A-03 なし）  

---

## 4. 技術的必須ルール（V4 でも維持）

| ルール |
|--------|
| Dual-Gate: Lab 合成だけでは GO しない（Offline/Shadow 必須） |
| worsened_winner_rank1 = 0 を Admission Hard Gate に含める |
| A-03 ∧ A-05 禁止 |
| Shadow 非購入 · fail-open |
| 結果列をモデル入力に使わない |

---

## 5. 資産パス

| 資産 | Path |
|------|------|
| A-05 policy | `research/v3_lab/admission_policy_a05.py` |
| Shadow | `research/v3_lab/shadow/` |
| Integration Design | `docs/releases/v3-production-integration-*.md` |
| PRR Final | `docs/releases/v3-prr-final-decision.md` |
| Registry/Flags snapshot | `research/v3_lab/baselines/v3_close/` |

---

## 6. やらないこと（V3 からの禁止の継続）

- A-03 を「簡単に直して」本番へ戻す  
- Lab Hit 279 を本番 KPI の正とする  
- Flag 既定を True にして出荷する  
- Explain/UI を無視した Canary  

---

## 7. Open Questions for V4 Charter

1. A-04 を Canary 初日に含めるか  
2. Canary % と観察窓の正式数値  
3. V2 PE-V2-A との長期共存期間  
4. Explainability の A-05 journal 露出範囲  

---

## 8. Stop

Handover 文書化まで。Version 4 プログラムには着手しない。
