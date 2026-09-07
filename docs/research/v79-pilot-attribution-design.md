# Version79 — Pilot Attribution Design

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止 / PE 変更禁止 / Production 変更禁止 / 改善禁止**  
**Parent problem:** V78 は CEW を Pilot PE の入力にしたため、Prediction 差分が **Trigger（World ラベル）由来か Strategy（PE）由来か** を一意に切れない。  
**目的:** 差分を一意に帰属できる Pilot / Shadow 構成を定義する。

---

## 問題の定式化

| 要因 | 意味（本設計） |
|---|---|
| **Trigger 要因** | レースに付与する World ラベルが Legacy か CEW/V69 か |
| **Strategy 要因** | 所与の World 文脈に対する PE ポリシーが Legacy PE か Pilot PE（V75 Contract）か |

V78 単一アーム「CEW ∧ Pilot PE」は両要因を同時に動かすため:

```text
Δ_obs = Prediction(CEW, PilotPE) − Prediction(Legacy, LegacyPE)
      = Δ_Trigger + Δ_Strategy + Interaction
```

→ **一意归因不可**。

---

## 直交因子（必須）

| Factor | 水準 | 備考 |
|---|---|---|
| **A: WorldLabel** | `legacy` \| `cew` | ラベル源のみ。Production Trigger は本設計では常に観測用に両方計算（権限は変更しない） |
| **B: PEPolicy** | `legacy_pe` \| `pilot_pe` | Pilot PE は Ready（rank7 / unsatisfied）のみ。他は常に legacy_pe |

```text
PEPolicy = pilot_pe が発火する条件（設計）:
  B == pilot_pe
  AND WorldLabel_for_PE == cew          # Pilot 契約は CEW Ready で定義（V77/V78）
  AND cew_world ∈ {rank7_world, unsatisfied}
  AND 対応 World Flag ON
それ以外 → legacy_pe
```

**重要:** Strategy 単独アームでも PE 文脈ラベルは **CEW 固定**とする。  
Legacy ラベルでは Ready が 0 件（V73）のため `pilot_pe` が発火せず、Strategy 効果が測定不能になる。

---

## ① Trigger 変更の影響（Strategy 固定）

### 定義アーム

| Arm | WorldLabel (A) | PEPolicy (B) |
|---|---|---|
| **T0** | legacy | legacy_pe |
| **T1** | cew | legacy_pe |

```text
Δ_Trigger := Metric(T1) − Metric(T0)
```

### 何が分かるか

- World ラベルだけを CEW に替えたときの Prediction / Hit / rank710 / other_miss  
- PE 中身は Legacy のまま（Strategy 非変更）

### 解釈上の注意

- Legacy PE が World 非依存なら Δ_Trigger ≈ 0（その事実自体が归因結果）  
- World 依存なら「ラベル切替」の純効果

### 評価集合

全 285R。加えて **Legacy≠CEW のレース**（V73 では多数）をサブ解析すると感度が上がる。

---

## ② Strategy 変更の影響（Trigger/ラベル文脈固定）

### 定義アーム

| Arm | WorldLabel (A) | PEPolicy (B) |
|---|---|---|
| **S0** | **cew**（固定） | legacy_pe |
| **S1** | **cew**（固定） | pilot_pe |

```text
Δ_Strategy := Metric(S1) − Metric(S0)
```

### 評価集合（層別必須）

| 層 | 定義 | 目的 |
|---|---|---|
| Ready-rank7 | CEW=rank7 | rank7 Strategy 純効果 |
| Ready-unsat | CEW=unsatisfied | Residual Policy 純効果 |
| Non-Ready | CEW∉Ready | **Δ≈0 を確認**（発火しないこと＝境界監査） |

### 何が分かるか

- 同じ CEW 文脈で Pilot PE だけ変えた差分  
- Trigger/Production を動かしていない（A は観測 CEW、Production Decision は触らない）

---

## ③ 両方変更時の影響

### 定義アーム

| Arm | WorldLabel (A) | PEPolicy (B) |
|---|---|---|
| **B0** | legacy | legacy_pe |
| **B1** | cew | pilot_pe |

```text
Δ_Both := Metric(B1) − Metric(B0)
```

### 相互作用

```text
Interaction := Δ_Both − Δ_Trigger − Δ_Strategy
```

| Interaction | 意味 |
|---|---|
| ≈ 0 | 効果が近似的に加法的 |
| ≠ 0 | ラベルと PE の非線形（归因は 2×2 を全部見ないと不可） |

V78 単アームは **B1 vs B0 のみ**に相当し、Interaction を分離できない。

---

## 归因の一意性ルール

実験結果から改善源を一意に言うための **許可文**:

| 観測 | 許可される結論 |
|---|---|
| Δ_Trigger 有意・Δ_Strategy≈0・Interaction≈0 | **Trigger（ラベル）由来** |
| Δ_Strategy 有意・Δ_Trigger≈0・Interaction≈0 | **Strategy（PE）由来** |
| 両者有意・Interaction≈0 | **両方（加法）** — 内訳は Δ_T と Δ_S で報告 |
| Interaction 大 | **相互作用あり** — 「どちらか一方」と断言禁止。2×2 を併記 |
| B1 のみ見て改善 | **归因禁止**（V78 陥穽） |

Hit 改善自体は本フェーズの目的ではない。归因可能性の設計が成果。

---

## V78 設計への修正要件（設計・非実装）

| V78 | V79 要件 |
|---|---|
| 単一「CEW→Pilot PE」経路 | **2×2 Shadow** を必須化 |
| Pilot ON の A/B だけ | T0/T1/S0/S1/B0/B1 をログ |
| Flag が PE のみ | Label 源と PEPolicy を **独立 Flag** に分離（Shadow 文書参照） |

Production は引き続き Legacy Trigger +（将来）Flag OFF 時 Legacy PE。

---

## 関連成果物

| Doc | 内容 |
|---|---|
| `v79-attribution-matrix.md` | ④ Attribution Matrix |
| `v79-shadow-configuration.md` | ⑤ Shadow 構成 |
| `v79-governance.md` | 統治 |

---

## 非範囲

- PE / Trigger / Production の実装  
- 係数・閾値の新設  
- midhole 等 Non-Ready の Pilot  
- Hit 最適化  
