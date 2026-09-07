# Version78 — Migration（Pilot → Validation → Expansion）

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parent:** `v78-ready-world-pilot-design.md`  
**禁止:** Expansion で Non-Ready World を Ready 扱いすること / 全 World 一括統合

---

## ⑤ Migration 概要

```text
Pilot
  │  Ready のみ・Flag OFF 既定・境界=CEW
  ▼
Validation
  │  285R（および拡張）で非干渉・Scope 監視
  ▼
Expansion
     Ready 増（例: midhole が V76 Gate PASS）のみ追加
```

---

## Stage 1 — Pilot（設計対象・本 Version）

### 目的
rank7 / unsatisfied に限定した PE Strategy 経路の設計固定。

### 入口条件
- V77: 対象 World が Ready  
- Feature Flag 設計完了（本ドキュメント群）  
- Trigger / Production 非変更の明示

### 出口条件（次へ）
- 実装 Decision が別途承認された場合のみ Validation 実装へ  
- **本 Stage だけではコード変更しない**

### 推奨順序（将来実装時）
1. MASTER=1, RANK7=1, UNSAT=0（rank7 単独）  
2. 安定後 UNSAT=1  

一括両 ON は Validation 負荷が大きい（unsatisfied 176/285）。

---

## Stage 2 — Validation

### 目的
Pilot 経路が Legacy Fallback と安全に共存することを測る。

### 必須評価（設計）

| 項目 | 定義 |
|---|---|
| Flag OFF 非干渉 | MASTER=0 で Prediction Fingerprint / Hit / rank710 / other_miss が現行と一致 |
| Scope 監視 | CEW∈Ready の部分集合で Hit / rank710 / other_miss |
| 境界監査 | pe_path が Non-Ready で常に legacy |
| Rollback 訓練 | World Flag OFF で pe_path が legacy に戻る |

### 非目的
Hit 最大化。Ready 判定の再定義。

### FAIL 時
即 MASTER=0。Expansion 禁止。設計見直しは別 Version。

---

## Stage 3 — Expansion

### 目的
**新たに Ready になった World のみ** Flag を追加。

### 入口条件
- 当該 World が V76 Gate で Ready（例: midhole が E3 後）  
- Pilot Design 追補（対象表の更新）  
- 専用 Flag（例: `W_PE_PILOT_MIDHOLE`）の設計

### 禁止
- Blocked / Partial の Expansion  
- 「全部 ON」による全 World 統合  
- Trigger Cutover との同時 Expansion（分離）

### 出口
World ごとの Flag が独立に ON/OFF 可能な状態を維持。

---

## Stage Map（権限）

| Stage | PE コード | Production Trigger | CEW |
|---|---|---|---|
| Pilot（V78 設計） | 未変更 | 未変更 | 境界定義のみ |
| Validation | Flag 付き経路（別 Decision） | 未変更 | 読取 |
| Expansion | Ready 増分のみ | 未変更（別軌道） | 読取 |

---

## Rollback と Migration の関係

```text
いずれの Stage でも
  World Flag OFF  → 当該 World Legacy
  MASTER OFF      → 全 Pilot 停止
```

Expansion 後も MASTER OFF で **初期状態（全 Legacy PE）に戻れる**こと。  
