# Version72 — Ground Truth Definition（Intent GT 再定義）

**Date:** 2026-07-28  
**Status:** Design Definition ONLY — **実装禁止**  
**Authority（唯一の正本）:** V43 World Semantic Contract → V44 World Trigger Specification  
**Supersedes:** V65 Intent GT（winner_rank ヒューリスティック）— **設計評価用途で廃止**  
**Locks:** Trigger / Blueprint コード / Signal / Threshold / PE / Prediction / Production — **変更禁止**

---

## 目的

評価基準を設計契約へ合わせる。  
Intent Ground Truth は **「そのレースが契約上どの勝ち筋 World を Expected とするか」** であり、結果帯・人気・スコア帯ではない。

---

## 構築順序（必須）

```text
① Semantic（V43）
     World Purpose / Winning Pattern / Required / Optional / Forbidden
        │
        ▼
② Trigger Contract（V44）
     Must + Polarity + Exclude + Logic Form（MATCH 定義）
        │
        ▼
③ Expected World（本 GT）
     MATCH 集合 → Conflict Resolution → 単一ラベル or unsatisfied
```

**禁止順序:** winner_rank / 人気 / model score / PE rank → World Label。

---

## 定義：Intent Ground Truth（V72）

### D0. 名称

**Contract Expected World（CEW）**  
通称: Intent GT（V72）。V65 Intent GT と混同しない。

### D1. 入力（許可）

契約が参照する **Signal / Concept の polarity 観測**のみ。

| 許可入力 | 根拠 |
|---|---|
| V43 Required / Optional に列挙された概念 | Semantic |
| V44 Must / Aux / Exclude に列挙された Signal・Concept | Trigger Spec |
| ↑/↓ の **契約 polarity**（高／低の方向） | V44 Spec Vocabulary |
| 複数 World の MATCH 真偽 | V44 Logic Form |

### D2. 入力（禁止 — Label 定義に使用不可）

| 禁止入力 | 理由 |
|---|---|
| `winner_model_rank` / 着順 / 勝馬 ID | 事後結果。勝ち筋（事前意味）ではない（V43 G1 / V71） |
| 人気順・単勝人気 | 契約 Must ではない |
| PE / Prediction score / model_rank 帯 | Prediction 層。World 意味の定義に使わない |
| V65 式 0.5/0.75/1.0 ソフトスコアによるラベル決定 | Outcome 帯ヒューリスティック（V71 IG-1） |
| Legacy / V69 Shadow の出力ラベルそのもの | 循環（実装を GT にしない） |
| 製品 Threshold 定数（0.72 等） | Threshold 変更禁止・GT は契約 polarity 層 |

### D3. 中間オブジェクト

各 Canonical World `w ∈ {core, midupper, midhole, rank7, bug}` について:

```text
MATCH(w) := MUST(w) AND NOT EXCLUDE(w)
```

`MUST` / `EXCLUDE` は **V44 `v44-trigger-logic.md` の Logic Form を正本写し**とする（本フェーズで改変しない）。

`mixed` は PRIMARY MATCH 集合から導出（下記 Label Rule）。

### D4. Expected World（出力）

V44 Cross-World Conflict Resolution に従う:

```text
M = { w | MATCH(w) } ∪ { mixed | MIXED_MATCH }

if |M| = 0:  Expected World = unsatisfied
if |M| = 1:  Expected World = that element
if |M| ≥ 2:  Expected World = mixed_world
```

（V44: count≥2 → prefer MIXED；count=0 → unsatisfied / NOT silent core DEFAULT）

### D5. Positive Match / Unsatisfied

| 用語 | GT 上の意味 |
|---|---|
| Positive Match | Expected World ≠ unsatisfied かつ DEFAULT 経路なし |
| unsatisfied | いずれの World も MUST 未充足（または Exclude により MATCH なし） |
| DEFAULT→core | **GT として存在しない**（V43 Forbidden / V44 T0 / FORBIDDEN_FORM） |

### D6. Expected Characteristics の扱い

V43 §⑥ / V44 T1: Expected Characteristics は **検証観点**であり、**Label の定義本体ではない**。  
成立後の観察（例: 結果が能力寄りに見えるか）は Evaluation Protocol の **副次チェック**に限り、CEW ラベル決定に使わない。

---

## 廃止（V65）

| V65 規則 | V72 |
|---|---|
| core := gap↑∧sep↑∧**wr≤3** | core := CORE_MATCH（wr 禁止） |
| midupper := **wr∈[2,6]** | midupper := MIDUPPER_MATCH |
| midhole := **wr∈[5,10]** ± mid_open | midhole := MIDHOLE_MATCH |
| rank7 := gap↓∧**wr∈[7,10]** | rank7 := RANK7_MATCH |
| bug := **wr≥11** | bug := BUG_MATCH |
| mixed := 強スコア 2+ | mixed := MIXED_MATCH / \|M\|≥2 |
| soft score pick + priority | boolean MATCH + V44 conflict resolution |

V65 文書・JSON は **歴史記録**として保持してよいが、新規設計評価の正本ではない。

---

## 権限階層

```text
V43 Semantic Contract     ← 意味の唯一正本
V44 Trigger Specification ← 意味→MATCH 論理の唯一正本
V72 Intent GT (CEW)       ← 上記からの導出ラベル定義（本ドキュメント群）
V69 Blueprint             ← 実装設計（GT 正本ではない；CEW で評価される側）
Legacy / Shadow 出力      ← 被評価者
```

衝突時: **V43/V44 > V72 文書の誤記修正 > 一切の実装・V65**。

---

## 非範囲

- MATCH 評価コードの実装  
- polarity の製品 Threshold 化  
- Signal 新設・配線  
- Trigger / V69 / Production 変更  
- 285R の再スコア実行（別フェーズ）

---

## Document Index

| # | Doc |
|---|---|
| ① | `v72-ground-truth-definition.md`（本ファイル） |
| ② | `v72-world-label-rule.md` |
| ③ | `v72-intent-label-guideline.md` |
| ④ | `v72-evaluation-protocol.md` |
| ⑤ | `v72-governance.md` |
