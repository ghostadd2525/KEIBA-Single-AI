# Version75 — World Readiness（PE 組み込み成熟度）

**Date:** 2026-07-28  
**Question:** 各 World Strategy を将来 PE に渡せる成熟度は何か？  
**本フェーズ:** PE **変更しない**。判定のみ。  
**根拠:** V74 標本安定性 + Separation 証拠 + Contract 充足。

---

## 判定定義

| 判定 | 意味 |
|---|---|
| **Ready** | 285R で安定標本かつ Separation が十分。PE 統合設計（別 Decision）に進める。 |
| **Partial** | Strategy / Contract は書けるが、標本・重複・未測軸により PE 確定は条件付き。 |
| **Blocked** | 標本ゼロまたは PROVISIONAL 過大。PE 組み込み禁止。 |

**Hit 改善は判定に使わない。**

---

## ⑤ Readiness 表

| World | n | Stable | Separation 証拠 | Contract | **Readiness** | 理由（測定） |
|---|---:|:---:|---|---|---|---|
| `rank7_world` | 65 | Y | midhole と符号逆転 2 / 脚質差 | ACTIVE | **Partial** | 安定だが Top 特徴は midhole と重複（Jaccard 0.67）。PE 前にゲート仕様の固定が必要。 |
| `midhole_world` | 24 | Y | rank7 と符号逆転・win_prob 弱 | ACTIVE | **Partial** | 安定かつ差あり。n=24 は下限寄り。再測・拡張コーパス推奨。 |
| `unsatisfied` | 176 | Y | 残余ポリシー | ACTIVE-RESIDUAL | **Partial** | 大標本。ただし「勝ち筋」ではなくベースライン。PE では default path 設計が別途必要。 |
| `core_world` | 8 | N | 未十分 | PROVISIONAL | **Blocked** | n\<20。PE 重み確定禁止。 |
| `midupper_world` | 6 | N | 未十分 / 適性未測 | PROVISIONAL | **Blocked** | n\<20 + aptitude 馬特徴未測。 |
| `mixed_world` | 6 | N | 未十分 | PROVISIONAL | **Blocked** | n\<20。合成重み未定。 |
| `bug_world` | 0 | — | なし | BLOCKED | **Blocked** | 標本 0。 |

---

## 集計

| Readiness | Worlds |
|---|---|
| Ready | **なし** |
| Partial | rank7, midhole, unsatisfied（residual） |
| Blocked | core, midupper, mixed, bug |

**含意:** V74 Verdict B と整合。World を維持する理由（Selector）は Partial まで実証済みだが、**PE 即時統合（Ready）には未達**。

---

## PE 統合前チェックリスト（将来・本フェーズ外）

Partial → Ready に上げる条件（設計ゲート案）:

1. 対象 World の CEW n≥20 を維持、できれば拡張コーパスで再現。  
2. midhole↔rank7 の文脈ゲート（field_size / upper_ability_band）が符号ごと再現。  
3. Strategy Contract の MUST が PE 入力契約に写せる（重み数値は別 Decision）。  
4. Hit を目的関数にしない検証（非劣化ゲート）は PE フェーズで別定義。  
5. Trigger/CEW/World Meaning を変更しない。

---

## 明示的禁止

- 本判定を理由に本フェーズで PE を実装・変更すること  
- Blocked World の仮 Strategy を本番 PE に載せること  
- Ready が 0 件であることを無視して Cutover すること  
