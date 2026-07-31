# Version83 — Integration Matrix

**Date:** 2026-07-28  
**Parent:** `v83-interaction-integration-design.md`  
**Locks:** Production / Trigger / Blueprint / World / Interaction Contract — 変更禁止  
**実装禁止**

---

## 比較軸の定義

| 軸 | 意味 |
|---|---|
| **ROI** | 将来の期待リターン方向（仮説）。実測なし。Hit / 購入効率 / 説明価値を含む広義。 |
| **Risk** | 悪化・誤適用・归因不能・カバレッジ欠損のリスク |
| **Rollback** | 方式 OFF 時に Legacy へ戻す容易さ |
| **影響範囲** | 触る PE 出力・レース割合・順位空間の広さ |

評価記号: **H** = High / **M** = Medium / **L** = Low（望ましい方向は軸による）

---

## 主比較表

| Mode | ROI（期待・仮説） | Risk | Rollback | 影響範囲 | V80教訓適合 | Shadow 適性 |
|---|---|---|---|---|---|---|
| ① Bonus | M〜H（効けば全体押し上げ）だが **悪化時も全域** | **H** | M（係数ゼロ化可） | **広い**（全頭 score） | **不適合**（加算族） | 低（非推奨） |
| ② Gate | M（ノイズ抑制で質↑の余地） | **H** | M〜H（Gate OFF→Legacy） | **中〜広**（不成立レースが脱落/Legacy） | 部分適合（「読むな」は良いが過剰） | 低〜中 |
| ③ Selector | M〜H（Contract 意味に最も忠実） | M | M（path=Legacy） | **中**（World×発火パス） | 適合（単位は Interaction） | 中（归因必須） |
| ④ Rank Swap | M（TopN の局所改善） | M | **H**（swap 層 OFF） | **狭い**（TopN のみ） | 部分適合（局所化） | **高** |
| ⑤ Confidence | L〜M（順位 Hit 非直接）/ 運用・閾値 ROI は別軸 | **L** | **H** | **狭い**（conf のみ） | **適合**（順位非侵襲） | **最高** |

---

## ROI 詳細（仮説・非実測）

| Mode | 上振れシナリオ | 下振れシナリオ |
|---|---|---|
| Bonus | Interaction が真の余力を captur | 全域スコア汚染 → V80 型 Hit 崩壊 |
| Gate | 偽シグナルレースを評価から排除 | 真の勝ち筋レースを落とす / カバレッジ減 |
| Selector | World 別 Must が正しいパスを選ぶ | 誤パス固定・Fallback 盗用 |
| Rank Swap | Top1–N の入れ替えが的中 | 無関係な微swap で購入効率↓ |
| Confidence | 閾値運用・説明・サイズ調整が改善 | 順位固定のまま機会損失（順位 ROI は動かない） |

---

## Risk 詳細

| Mode | 主リスク | 二次リスク |
|---|---|---|
| Bonus | 係数過学習・全域悪化 | Contract Forbidden の w 漏れ |
| Gate | 評価不能・Legacy 偏り | midhole pace 欠測で Gate 不発多発 |
| Selector | 归因困難（Mode×World） | Priority と実装パスのズレ |
| Rank Swap | TopN 定義依存 | N 过大で実質 Bonus 化 |
| Confidence | 「何も変わらない」と誤認され打ち切り | conf を隠れて順位に使う実装逸脱 |

---

## Rollback 詳細

| Mode | Rollback 操作（設計） | 残滓 |
|---|---|---|
| Bonus | w≡0 / Adapter OFF | 学習済み係数の誘惑（再ON危険） |
| Gate | Gate 無効 → 常時 Legacy 評価 | ログ上の「不成立」フラグのみ |
| Selector | path 固定 Legacy | 分岐コードが残ると誤ONリスク |
| Rank Swap | swap 層スキップ | BaseRank が正本のため残滓最小 |
| Confidence | conf' = BaseConf | 順位正本不変。残滓最小 |

---

## 影響範囲詳細

| Mode | Score | Rank | Confidence | 対象頭数 | Ready 限定時のレース割合目安 |
|---|---|---|---|---|---|
| Bonus | ○ 変更 | ○ 間接 | △ 任意 | 全頭 | rank7+unsat ≈ 85% で全域汚染可能 |
| Gate | ○/抑制 | ○/抑制 | △ | 発火レース全頭 | 不発火分は Legacy または欠損 |
| Selector | ○（パス依存） | ○ | △ | 選択パス上 | World 分割 |
| Rank Swap | △ 最小 or なし | ○ TopN | △ | TopN のみ | 同左だが頭数制限 |
| Confidence | × | × | ○ | 全頭可だが順位非変更 | 影響は閾値利用時のみ |

---

## Contract Role × Mode 適合マトリクス

|  | Must を正しく強制 | Aux を過剰適用しにくい | Forbidden を遮断しやすい |
|---|---|---|---|
| Bonus | △（w 次第） | ×（加算が積み上がる） | △（w=0 規律依存） |
| Gate | ○ | ○ | ○ |
| Selector | ○ | ○（優先度） | ○（候補除外） |
| Rank Swap | ○（主信号） | ○（微補正） | ○（swap 禁止） |
| Confidence | △（強制力は弱い） | ○ | ○ |

---

## World × Mode 推奨度（設計・非実装）

| World | Bonus | Gate | Selector | Rank Swap | Confidence |
|---|---|---|---|---|---|
| rank7 | 禁止推奨 | 条件付き | 可（Shadow） | **推奨** | **最推奨** |
| midhole | 禁止 | pace 欠測注意 | 可（慎重） | 可 | **推奨** |
| unsatisfied | 禁止 | 過剰Gate禁止 | Baseline のみ | 微swap可 | **推奨** |
| core | 禁止 | 禁止 | 禁止 | 禁止 | 観測のみ可 |

---

## 総合スコア（設計用・主観合成）

重み: Risk↓ 0.35 / Rollback↑ 0.20 / 影響範囲制御 0.20 / Contract整合 0.15 / ROI上振れ 0.10  
（実測最適化ではない）

| Mode | 合成 | 判定 |
|---|---|---|
| Confidence | 高 | Shadow 第一候補 |
| Rank Swap | 高 | Shadow 第二候補 |
| Selector | 中 | 归因付き第三 |
| Gate | 低〜中 | 原則見送り |
| Bonus | 低 | **見送り（V80）** |
