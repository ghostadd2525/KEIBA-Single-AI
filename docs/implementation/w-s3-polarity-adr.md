# ADR-W-S3 — Signal Polarity Contract

**Status:** Accepted（design ADR only — **not implemented**）  
**Date:** 2026-07-28  
**Version:** 60  
**Deciders:** Architecture / Research（V43 Semantic · V44 Trigger Spec · V59 Must Ledger）  
**Depends on:** W-S2 Must Readiness Ledger complete；W-S1 Shadow Dual-Eval PASS  
**Non-goals:** Threshold 数値、Exclusion 変更、Trigger 実装、Signal 生成、Cutover、Production / Prediction / PE / CE 変更

---

## Context

V44 は閾値なしで **極性（↑/↓）** を定義した。W-S1 Shadow は batch-median で観測したが、それは **運用仮極性**であり正式契約ではない。  
V46 S3 / V58 条件より、Exclusion 104件の再評価前に **極性を ADR で固定**する。

本 ADR は「高い／低い／フラグ真偽が、どの World の勝ち筋に対して正か」だけを固定する。

---

## Vocabulary

| Term | Definition |
|---|---|
| **Positive（+）** | 当該 World の契約上、その方向が **成立を支持**する（Must または Aux の契約 polarity） |
| **Negative（−）** | 当該 World の契約上、その方向が **成立に逆行**する（反対極性）。Must では不足側 |
| **Neutral（N）** | 当該 World 仕様で方向を定めない（V44 `N/A`）、または「中」のみで Must 極性を持たない |
| **Forbidden-as-positive（F+）** | その方向を **正条件に使ってはならない**（V44 Forbid+）。Exclusion 候補方向と一致しうるが、**本 ADR は Exclusion 規則を変更しない** |
| **Present / Absent** | フラグ系: Present=+、Absent=−（Must 欠落） |

**閾値:** 本 ADR では定めない（相対順位 / 分位 / 絶対値の選択は実装承認後。V46 S3）。

---

## ①–② Intrinsic axes（Signal 自体の読み）

物理・コードキーと「高い／低い」の意味（実装変更なし・既存キー名）:

| Signal（本フェーズ対象） | Code / contract key | High / Present の意味 | Low / Absent の意味 |
|---|---|---|---|
| `top_gap` | `top_gap` / `get_context_top_gap` | top1−top2 大＝能力差が開く | 小＝上位拮抗 |
| `race_leg_difficulty` | `race_leg_difficulty` | 脚難度・展開難が高い | 低い |
| `chaos_score` | `chaos_score` | 混戦・カオスが高い | 低い |
| `short_field_pressure` | `short_field_pressure` / `calc_short_field_pressure` | route/少頭圧が高い | 低い |
| `late_stop` | `late_stop_risk_score` | 差し遅れ圧が高い | 低い |
| `sustained` | `sustained_run_possible_score` | 持続脚可能性が高い | 低い |
| `high_pace` | `high_pace_score` | ハイペース圧が高い | 低い |
| `phase_transition` | `phase_transition` | 局面転換圧が高い | 低い |
| `aptitude_fit` | 意味契約上の適性（V43/V44；W-S2 Missing） | 適性が高い | 低い |
| `unexplained_single` | 意味契約フラグ（W-S2 Missing） | 単一説明不能が明示 | 非明示 |
| `exception_flag` | 意味契約フラグ（W-S2 Missing / bug Must） | 例外標識 ON | OFF |

---

## ③ World Mapping（正式極性）

記号: **+** Positive · **−** Negative · **N** Neutral · **F+** Forbidden-as-positive（高/Present を正条件にしない）

| Signal | core | midupper | midhole | rank7 | mixed | bug |
|---|---|---|---|---|---|---|
| `top_gap` | **+**（高=Must） | N（中=Aux；高単独で定義しない） | **−**寄り Aux；高は F+ as 独占 | **−**（低=Must） | N / Aux | N |
| `race_leg_difficulty` | F+（単独定義禁止） | N〜+ Aux（非・能力帯） | N | N〜+ Aux | + Aux（複合時） | + Aux（極端のみ・Mustではない） |
| `chaos_score` | F+（高を正にしない） | N〜+ Aux | N〜+ Aux | **+**（高=Must） | + Aux | + Aux（極端；Mustではない） |
| `short_field_pressure` | F+（高）/ Aux は **低=+**（V44 core Aux sfp↓） | + Aux（展開 Dev） | N | + Aux | + Aux | N |
| `late_stop` | F+（∧sustained を core 正にしない） | N | + Aux | N | N | N |
| `sustained` | F+（∧late_stop を core 正にしない） | N | + Aux | N | N | N |
| `high_pace` | F+（単独正禁止） | + Aux（Dev） | + Aux | **+**（Must系 pace_conflict） | + Aux | N |
| `phase_transition` | N | + Aux（Dev） | N | + Aux | + Aux；**単独定義は F+** | N |
| `aptitude_fit` | N | **+**（高=Must） | + Aux | N | N | N |
| `unexplained_single` | N | N | N | N | **+**（Present=Must OR枝） | N |
| `exception_flag` | F+（≠DEFAULT） | N | N | N | N | **+**（Present=Must） |

詳細: `w-s3-world-polarity.md`

---

## ④ Conflict Matrix

同一 Signal が World 間で **逆極性**または **F+ vs +** になる組:

| Signal | Conflict | Worlds | Contract basis |
|---|---|---|---|
| `top_gap` | 高=+ vs 低=+ | core vs rank7 | V44 T3；V43 Required |
| `top_gap` | 高=Must vs 高=F+ | core vs midhole（独占） | V44 Forbid+ midhole |
| `chaos_score` | 高=F+ vs 高=Must | core vs rank7 | V44 T3 |
| `short_field_pressure` | 高=F+ vs 高=Aux+ | core vs midupper/rank7/mixed | V44 roles |
| `high_pace` | 高=F+(単独) vs 高=Must | core vs rank7 | V44 |
| `late_stop`∧`sustained` | 同時高=F+ for core；各+ Aux midhole | core vs midhole | V44 Logic Form |
| `phase_transition` | 複合 Aux+ vs 単独 F+ | mixed 内部 | V44 mixed Forbid |
| `exception_flag` | Present=Must bug；core では F+ as DEFAULT混同禁止 | bug vs core | V43/V44 |

Full matrix: `w-s3-conflict-matrix.md`

---

## ⑤ Exclusion Interaction（参照のみ・変更禁止）

V44: Exclusion は Forbidden 方向が支配的なとき候補を落とす。  
本 ADR の **F+ / 逆極性**は Exclusion の **入力意味**を固定するが、**Exclusion 条項・順序・実装は変更しない**。

| ADR polarity | Relation to Exclusion（設計参照） |
|---|---|
| F+（高） on World W | W の Exclude 候補方向と整合しうる |
| core で chaos/sfp/late∧sust = F+ | V44 CORE_EXCLUDE と対応（変更しない） |
| rank7 で top_gap 高 = −（Must は低） | RANK7_EXCLUDE の top_gap↑ と対応（変更しない） |

**104件 Exclusion after Must** の再評価は、本 ADR Accepted 後の **別 Shadow 観測**（実装・Trigger 変更なしの再計測）で行う。本フェーズでは再集計しない。

---

## Decision

1. 上表の World Mapping を **正式極性契約**とする。  
2. 閾値・分位・中央値の採用は **本 ADR の外**（別実装承認）。  
3. W-S2 Missing（`aptitude_fit` / `unexplained_single` / `exception_flag`）でも **極性定義は有効**（供給可否は Ledger 側）。  
4. Exclusion / Trigger / Signal コードは **変更しない**。

---

## Consequences

### Positive

- Shadow / 将来 Soft Cutover 前に「高い＝誰の勝ち筋か」が単一契約になる  
- core↔rank7 の `top_gap` / `chaos` 逆極性を文書で固定  

### Negative / Follow-on

- 閾値未決のままでは数値判定はできない（意図どおり）  
- Missing Must は極性があっても MATCH 不能（W-S2）  

### Out of scope

- Exclusion 改修、Trigger 改修、104件の再判定実行、Proxy 復活、Cutover  

---

## References

- `docs/architecture/v43-required-signals.md`  
- `docs/architecture/v44-world-trigger-specification.md` T3  
- `docs/architecture/v44-signal-roles.md`  
- `docs/architecture/v44-trigger-logic.md`  
- `docs/implementation/w-s2-must-readiness.md`  
- Code keys: `demo_ticket_optimizer_core.get_context_top_gap` / `chaos_score` / `race_leg_difficulty` / `calc_short_field_pressure` 等（観測・命名根拠のみ）

---

*ADR-W-S3 — polarity only. No implementation.*
