# Version78 — Ready World Pilot Design

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parents:** V77 Readiness（rank7 / unsatisfied = Ready） / V75 Strategy Contract / V76 Gate  
**Locks:** Trigger / Blueprint / Signal / Threshold / **Production Decision** — 変更禁止  
**禁止:** 全 World PE 統合 / midhole・Blocked World の Pilot 対象化

---

## 目的

Ready World **のみ**に Strategy を試す **Pilot Integration** を設計する。  
PE 全体統合・本番 Cutover・実装は本フェーズ外。

---

## Pilot 対象 / 非対象

| 区分 | World | 扱い |
|---|---|---|
| **Pilot ON 可** | `rank7_world` | V75 rank7 Strategy Contract |
| **Pilot ON 可** | `unsatisfied` | V75 Residual Policy（勝ち筋ではない） |
| **Fallback 必須** | midhole / core / midupper / mixed / bug | **Legacy PE**（変更なし） |

285R CEW 規模（V73/V77）:

| Scope | n | share |
|---|---:|---:|
| rank7 | 65 | 22.8% |
| unsatisfied | 176 | 61.8% |
| **Ready 合計** | **241** | **84.6%** |
| Non-Ready | 44 | 15.4% |

---

## ① Strategy 適用境界

### 境界の入力ラベル（必須）

Pilot の適用判定は **CEW（V72 Contract Expected World）** とする。

| 理由 | 根拠 |
|---|---|
| Legacy は rank7 / unsatisfied を **0 件**しか出さない（V65/V73） | Legacy 境界では Ready Pilot が発火しない |
| V77 で Ready 判定した正本が CEW | V76/V77 Gate |
| V69 Shadow は CEW と 285/285 一致（V73） | 観測ラベルとして CEW と同等 |

```text
IF CEW == rank7_world AND flag.rank7:
    PE_path := Pilot_rank7_strategy
ELIF CEW == unsatisfied AND flag.unsatisfied:
    PE_path := Pilot_unsatisfied_residual_policy
ELSE:
    PE_path := Legacy_PE   # Fallback
```

### Production World Decision との分離

| 層 | 権限 | Pilot での扱い |
|---|---|---|
| Trigger / Production World | **Legacy 固定** | 変更しない |
| CEW（Shadow / 評価オラクル） | V44/V72 | Pilot 境界の **入力のみ** |
| PE Strategy path | Legacy or Pilot | Flag で切替（実装は別 Decision） |

**MUST NOT:** Production `classify_world_line_type` を Pilot のために書き換える。  
**MUST NOT:** midhole 等 Non-Ready に Pilot 戦略を適用する。

### rank7 Pilot 境界（Strategy 要約・新設計なし）

V75 Contract の写し（係数は未実装・未固定）:

1. history と win_prob を同格バンド  
2. field_size↑ で win_prob 依存を減衰  
3. 差し・追込を主勝ち脚質にしない  

### unsatisfied Pilot 境界（Residual）

1. Positive World Strategy（rank7/midhole 等）を **強制しない**  
2. 汎用ベースライン（popularity 可なら市場、否則 odds/win_prob）  
3. 「第7の勝ち筋」として特殊 PE を発明しない（V75 MUST NOT）

---

## ② Fallback

| 条件 | PE |
|---|---|
| CEW ∉ {rank7, unsatisfied} | **Legacy PE 100%** |
| Flag OFF（全体 or World 単位） | **Legacy PE 100%** |
| CEW 計算不能 / Must 欠落で CEW 不定 | **Legacy PE**（Pilot 不発火） |
| rank7 Flag ON かつ unsatisfied Flag OFF | rank7 のみ Pilot、unsatisfied は Legacy |
| 逆 | unsatisfied のみ Pilot |

Fallback 時の出力は現行 Production と **ビット一致を目標**（Validation 段階の非干渉確認）。

---

## ④ Risk（285R・現行 Prediction 併記）

**注:** 本フェーズは PE 未実装のため、以下は **影響範囲の実測ベースライン**であり、Pilot後の Hit Δ 予測ではない。

### 全体ベースライン（V73 Prediction アーム）

| Metric | 285R |
|---|---:|
| Hit | 218 |
| Purchase | 218 |
| rank710 | 14 |
| other_miss | 18 |

### Ready Scope 内訳（CEW・fixture hit_at_1）

| Scope | n | Hit | rank710 | other_miss* |
|---|---:|---:|---:|---:|
| rank7 | 65 | 52 (80.0%) | **1** | 3 |
| unsatisfied | 176 | 128 (72.7%) | **13** | 11 |
| Ready 合計 | 241 | 180 | **14** | 14 |
| Non-Ready | 44 | 38 | **0** | 4 |

\*other_miss ≈ other_1_3 + other_10_13 + other（V70 定義に近い合算）

### リスク含意（測定から言えることのみ）

1. **rank710 の 14/14 が Ready Scope 内**（Non-Ready に 0）。Pilot は rank710 面に必ず触れる。  
2. unsatisfied が Ready の **73%**（176/241）を占め、Residual Pilot の影響が主。  
3. rank7 単独は n=65・rank710=1 で相対的に小さいが、field_size 減衰は本命寄りを動かす。  
4. Hit 改善は Pilot 成功条件に **しない**（V75 C4）。Validation は非劣化ゲートを別定義。

### リスク軽減（設計）

| 策 | 内容 |
|---|---|
| World 単位 Flag | unsatisfied を後回し、rank7 のみ先行 Pilot 可 |
| Soft 比率 | Pilot 混合比 0→ε→…（Migration 参照） |
| Rollback | Flag OFF で Legacy 即時復帰 |
| 監視 | Ready Scope 限定の Hit / rank710 / other_miss |

---

## 非範囲

- PE 重みの数値決定・コード実装  
- Trigger / CEW 規則変更  
- midhole Ready 化（E3）の先行 Pilot  
- Production Cutover  

---

## 関連

- `v78-feature-flag-design.md`  
- `v78-migration.md`  
- `v78-governance.md`  
