# Version78 — Feature Flag Design（Ready World Pilot）

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parent:** `v78-ready-world-pilot-design.md`  
**原則:** World 単位で切れること / デフォルト OFF / Production Trigger 非干渉

---

## ③ Rollback / Flag 階層

```text
W_PE_PILOT_MASTER          # 全体キルスイッチ（OFF=全 Legacy PE）
 ├── W_PE_PILOT_RANK7      # rank7 Strategy Pilot
 └── W_PE_PILOT_UNSAT      # unsatisfied Residual Pilot
```

| Flag | Default | ON の意味 | OFF の意味 |
|---|---|---|---|
| `W_PE_PILOT_MASTER` | **OFF** | 下位 Flag を評価 | 下位無視・常に Legacy PE |
| `W_PE_PILOT_RANK7` | **OFF** | CEW=rank7 のとき Pilot_rank7 | rank7 も Legacy PE |
| `W_PE_PILOT_UNSAT` | **OFF** | CEW=unsatisfied のとき Residual Pilot | unsatisfied も Legacy PE |

**禁止 Flag（本 Pilot 設計に含めない）:**

- midhole / core / midupper / mixed / bug 用 PE Pilot Flag  
- Production Trigger 切替 Flag の流用（`W_TRIGGER_*` と分離）

---

## 決定表

| MASTER | RANK7 | UNSAT | CEW=rank7 | CEW=unsatisfied | 他 CEW |
|---|---|---|---|---|---|
| 0 | * | * | Legacy | Legacy | Legacy |
| 1 | 0 | 0 | Legacy | Legacy | Legacy |
| 1 | 1 | 0 | **Pilot rank7** | Legacy | Legacy |
| 1 | 0 | 1 | Legacy | **Pilot residual** | Legacy |
| 1 | 1 | 1 | **Pilot rank7** | **Pilot residual** | Legacy |

---

## World 単位 Rollback

| 操作 | 効果 | 目標 RTO |
|---|---|---|
| `W_PE_PILOT_RANK7=0` | rank7 のみ即 Legacy | 設定反映サイクル内（実装時定義） |
| `W_PE_PILOT_UNSAT=0` | residual のみ即 Legacy | 同上 |
| `W_PE_PILOT_MASTER=0` | Pilot 全停止 | 同上 |

Rollback 判定トリガ（Validation 段階で監視・閾値は別 Decision）:

- Ready Scope の Hit 劣化  
- rank710 増加  
- other_miss 増加  
- 例外・スコア異常率  

本設計は **閾値数値を固定しない**（実装・Validation の別 Decision）。

---

## Trigger Flag との隔離

| 系統 | 例 | Pilot との関係 |
|---|---|---|
| Trigger 移行 | `W_TRIGGER_SHADOW` / `W_TRIGGER_PATH` | **独立**。Pilot は PE 層のみ |
| PE Pilot | `W_PE_PILOT_*` | 本設計 |

Trigger Soft/Cutover を Pilot の前提にしない。  
CEW は Shadow 評価として読み取り可能であればよい（Production World は Legacy）。

---

## ログ要件（設計）

Pilot 発火時に記録（実装時）:

- `cew_world`  
- `pe_path` ∈ {legacy, pilot_rank7, pilot_unsat}  
- flag スナップショット  
- race_id  

Production World（Legacy）も併記し、境界の監査を可能にする。

---

## デフォルト安全

全 Flag **OFF** = 現行 Production と同一 PE 経路（非干渉）。  
これが Pilot 導入前の必須状態。  
