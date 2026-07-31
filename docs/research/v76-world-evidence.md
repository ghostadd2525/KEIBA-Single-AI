# Version76 — World Evidence（不足証拠の棚卸し）

**Date:** 2026-07-28  
**Status:** Evidence Definition ONLY — **実装禁止 / PE・Trigger・Blueprint 変更禁止**  
**Parents:** V75 Strategy Design / Readiness（Ready=0） / V74 Validation（Verdict B） / V73 CEW  
**Corpus 現状:** 285R CEW 分布（V74）

| World | n | V75 Readiness |
|---|---:|---|
| unsatisfied | 176 | Partial |
| rank7_world | 65 | Partial |
| midhole_world | 24 | Partial |
| core_world | 8 | Blocked |
| midupper_world | 6 | Blocked |
| mixed_world | 6 | Blocked |
| bug_world | 0 | Blocked |

**本フェーズの目的:** Ready に必要な証拠の欠落を列挙する。PE 実装・Hit 改善は非目的。

---

## ① Evidence 不足（World 別）

### `rank7_world`（Partial）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=65（安定閾値≥20は充足） | 単一コーパス依存。**分割再現**（例: 時系列 half / 別開催）なし |
| Separation | midhole と符号逆転 2 件・脚質差あり | Top5 Jaccard **0.67** — 特徴集合の差が中程度。**ゲートの定量仕様**（減衰関数形）未固定 |
| 相互作用 | field_size r=−0.113（|r| 小さめ） | 効果量の信頼区間・感度分析なし |
| Contract→計測写像 | MUST は定性 | MUST 各条の **観測可能な合否テスト**が未整備 |
| 対比相手 | midhole のみ戦略安定 | core/midupper 安定化後の **多 World 分離**未確認 |

### `midhole_world`（Partial）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=**24**（下限ぎりぎり） | n 増または bootstrap で **優先順位（history≫win_prob）の安定性**証明 |
| Separation | rank7 と符号逆転・win_prob 弱 | 同左ゲート定量・再現 |
| FieldHit | win_prob FieldHit **0.083** | 小標本ノイズか構造かの切り分け |
| 対比 | rank7 のみ | unsatisfied / 将来 core との差分の定式化 |

### `unsatisfied`（Partial・Residual）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 役割定義 | 残余ベースライン（勝ち筋ではない） | PE における **default path 契約**（いつ Positive Strategy を使わないか）の正式化 |
| popularity | 首位だが部分集合 | 全レース coverage と欠損時フォールバック規則 |
| 誤用防止 | MUST NOT 文書あり | Positive World 誤適用率の **測定プロトコル** |

※ Residual の「Ready」は勝ち筋 Ready ではなく **Residual Policy Ready**（定義は Gate 文書）。

### `core_world`（Blocked）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=8 | まず **n≥20（推奨≥40）** の CEW core |
| Separation | 未証明 | win_prob 首位・高 top_gap が **安定再現**すること |
| 脚質 | 先行リフト大（不安定） | 再現確認 |
| Contract | PROVISIONAL | ACTIVE 化 |

### `midupper_world`（Blocked）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=6 | n≥20 |
| 適性軸 | V43 Must だが馬特徴未測 | **aptitude 系の観測可能な代理**と効果測定（Signal 新設は別 Decision — 本フェーズでは「不足」として記録のみ） |
| Separation | 未証明 | midhole/rank7/core との優先順位差 |

### `mixed_world`（Blocked）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=6 | n≥20 |
| 合成規則 | multi_path の合成重み未定 | 構成 Primary の Strategy **合成オペレータ**の定義と検証 |
| history | effect≈0（仮） | 再現性 |

### `bug_world`（Blocked）

| 不足カテゴリ | 現状 | Ready に足りないもの |
|---|---|---|
| 標本 | n=**0** | CEW bug ≥ 最小 n（Gate で定義） |
| exception | コーパスで欠落し MATCH 不能 | exception 標識の観測可能性（Signal 変更は別 Decision） |

---

## ② Sample Sufficiency（現 n の信用範囲）

| n 帯 | 信用できること | 信用できないこと |
|---|---|---|
| **n≥60**（rank7 65） | 優先特徴の大まかな順位、脚質リフトの符号、\|r|≳0.10 の文脈相関の方向 | 精密な減衰係数、単レース診断 |
| **20≤n\<40**（midhole 24） | 「history≫win_prob」のような **粗い順位構造**、符号逆転の存在示唆 | 効果量の大きさ、FieldHit の精密比較 |
| **n≥100**（unsatisfied 176） | 残余ベースラインの平均プロファイル | 「勝ち筋」としての固有 Strategy（定義上対象外） |
| **n\<20**（core/midupper/mixed） | V43 Goal の仮説メモのみ | いかなる PE 重み・順位・ゲート係数 |
| **n=0**（bug） | なし | すべて |

### 信用度ラベル（本文書）

| World | Sample Sufficiency Grade |
|---|---|
| rank7 | **S2** — 方向証拠は可、係数固定は不可 |
| midhole | **S1** — 構造仮説は可、単独で Ready 不可 |
| unsatisfied | **S2-R** — Residual プロファイルは可 |
| core / midupper / mixed | **S0** — 仮説のみ |
| bug | **S∅** — 証拠なし |

---

## 証拠ギャップの優先順位（蓄積順）

1. **midhole n 強化 + rank7/midhole ゲート再現**（Partial→Ready の最短路）  
2. **rank7 分割再現 + MUST 合否テスト**  
3. **unsatisfied Residual Policy の測定可能化**  
4. **Blocked Worlds の CEW n≥20**（core → midupper → mixed）  
5. **bug 標本または exception 観測可能性**（最長）

---

## 非範囲

- コーパス拡張の実装  
- Signal / Trigger / PE 変更  
- Hit を証拠にする行為  
