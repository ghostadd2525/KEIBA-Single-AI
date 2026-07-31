# Version 3 — Production Integration Migration Plan（A-03 → A-05）

**Date:** 2026-07-24  
**Status:** Plan Only · **実行なし**  
**Parent:** [`v3-production-integration-design.md`](./v3-production-integration-design.md)

---

## 1. 目的

公式スタックの Admission を **A-03（Offline FAIL）から A-05（Offline/Shadow PASS）へ移行**する計画を定義する。

---

## 2. As-Is / To-Be

### As-Is（Lab 公式 · 本番投入禁止）

| Stage | 構成 |
|-------|------|
| Admission | **A-03** `F_V3_A03_POOL_ADMIT_ENABLED` |
| Selection | A-04 |
| Evaluation | A-01 |
| Lab Hit | 279 |
| Offline | **FAIL**（59→42） |

### To-Be（本番候補 · 未配線）

| Stage | 構成 |
|-------|------|
| Admission | **A-05** `F_V3_A05_ADM_FAVSAFE_ENABLED` |
| Selection | A-04（継続方針 · 別確認可） |
| Evaluation | A-01（継続） |
| A-03 | **公式除外 · Flag 常時 OFF** |
| Offline / Shadow | A-05 solo で PASS 実証済み |

**注:** To-Be の「A-01+A-05+A-04」合成 Lab Hit は本 Migration の必須再現条件にしない（PRR/A-05 Success Criteria に準拠）。Offline / Shadow の本命非破壊を優先。

---

## 3. 移行フェーズ

```text
Mig-0  文書凍結: Baseline v3(A-03) = 本番禁止 / A-05 = 候補
Mig-1  Registry / Design 正本を To-Be に更新（実装なしでも可）
Mig-2  Staging 配線（A-05 経路 · 既定 OFF）
Mig-3  Prod Shadow（M1）— A-03 経路が残っていれば無効化確認
Mig-4  Canary（M2）— A-05 のみ Mesh ON
Mig-5  公式ラベル切替: lab_baseline を A-05 系に再発行（別承認）
Mig-6  A-03 コードは削除せず凍結（比較・監査用）
```

| フェーズ | 本 Round |
|----------|----------|
| Mig-0 | 本設計で宣言 |
| Mig-1–6 | **未実行** |

---

## 4. 切替手順（Admission）

1. 確認: `F_V3_A03_POOL_ADMIT_ENABLED` = OFF（全環境）  
2. 確認: `F_V3_A05_ADM_FAVSAFE_ENABLED` 既定 = OFF  
3. Staging で A-05 経路の identity/Canary スモーク  
4. mutex テスト: A-03∧A-05 → 拒否  
5. Mesh で Canary % のみ A-05 ON  
6. 監視窓 PASS 後に % 拡大  
7. 文書上の「公式 Admission」を A-05 に更新  

---

## 5. データ・互換

| 項目 | 方針 |
|------|------|
| 入力 runners | 変更なし |
| 出力 pick | top-1 契約維持 |
| journal | `AP-V3-A05-favorite-safe-coverage` |
| 旧 A-03 journal | 参照のみ |

---

## 6. 成功条件（移行）

| 条件 |
|------|
| 本番で A-03 promote 経路が発火しない |
| Canary で wr1=0 · churn=0 · ΔHit>0（合意窓） |
| Purchase が A-05 Canary pick のみ（Shadow 非購入） |
| 既定 Flag が OFF のまま |

---

## 7. 失敗時

Rollback Checklist に従い全 V3 Accuracy Flag OFF → Control 復帰。  
A-03 を「回避策として再 ON」しない（Offline FAIL 再燃）。

---

## 8. Stop

Migration Plan 文書化まで。Mig-1 以降は実行しない。
