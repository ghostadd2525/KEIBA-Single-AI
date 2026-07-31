# Version88 — World Usage Matrix（Decision Layer）

**Date:** 2026-07-28  
**Parent:** `v88-decision-policy.md`  
**Rule:** Prediction 順位・Score 配列は全セルで **不使用（No mutate）**

凡例:

| 記号 | 意味 |
|---|---|
| **P** | Primary 利用（Decision の主スイッチ） |
| **S** | Secondary（補助） |
| **N** | 使わない / デフォルト |
| **X** | 禁止（誤用防止） |
| **H** | 仮説のみ（自動適用禁止） |

---

## 主マトリクス（World × Decision 軸）

| World | Ready | Ticket | Confidence Policy | Risk | Candidate Pool | Explanation | Pred Rank |
|---|---|---|---|---|---|---|---|
| `rank7_world` | Ready | **P** 分散 | **P** 過信抑制 | **S** 中予算 | **P** Top3–5 表示拡張 | **P** 混戦语义 | **X** 変更禁止 |
| `midhole_world` | Partial | **S** history 相手 | **S** win_prob 過信抑制 | **S** 控えめ | **S** 中位/history 追加表示 | **P** midhole 语义 | **X** |
| `unsatisfied` | Ready Residual | **N** 保守既定 | **N** 汎用 | **N** 標準 | **N** 拡張なし | **P** 残余明示 | **X** |
| `core_world` | Blocked | **H** | **X** 高確信禁止 | **P** 見送り寄り | **N** | **S** 仮説説明 | **X** |
| `midupper_world` | Blocked | **X** 自動禁止 | **X** | **X** | **N** | **S** | **X** |
| `mixed_world` | Blocked | **X** 自動禁止 | **X** | **X** | **N** | **S** 多筋注意 | **X** |
| `bug_world` | — | **X** | **X** | **P** 例外見送り | **X** | **P** 例外 | **X** |

---

## 用途別：World を「何に使うか / 使わないか」

| 用途 | World を使うか | 根拠 |
|---|---|---|
| Prediction 順位 | **使わない** | V80–V87 |
| Calibration p_base 主エンジン | **使わない（未証明）** | V87 INCONCLUSIVE |
| Ticket 券種・サイズ | **使う（設計）** | 语义→購入行動 |
| 表示 Confidence / 見送り閾値 | **使う（設計・順位非連動）** | 過信抑制 |
| Risk 予算 | **使う（設計）** | Ready/Partial/Blocked |
| Candidate Pool 表示 | **使う（設計・配列非変更）** | 混戦・midhole |
| Explanation | **使う** | V43 Semantic の本丸 |
| Interaction→Score | **使わない** | V84 主因否定 |

---

## rank7 vs unsatisfied（Ready 対比）

| Decision | rank7 | unsatisfied |
|---|---|---|
| Ticket | 分散・本命抑制 | 変更しない（既定） |
| Confidence | 混戦タグ・過信抑制 | 汎用のみ |
| Pool | 拡張表示 | 拡張しない |
| Explanation | 勝ち筋（混戦）あり | 勝ち筋なし（残余） |
| 価値の種類 | **積極的 Decision** | **抑制的 Decision** |

---

## midhole の位置づけ

| 項目 | 内容 |
|---|---|
| Prediction | 不使用 |
| Decision | Explanation + Pool は有望 |
| 自動 Ticket | Partial のため **条件付き / 原則手動または OFF** |
| rank7 との差 | 同格バンド禁止・win_prob 主軸禁止を Explanation/Ticket 禁則に写す |

---

## 誤用マトリクス（Forbidden）

| 誤用 | なぜ禁止 |
|---|---|
| World で Top1 を入れ替え | Prediction 層への侵食（V80 系） |
| World Prior を無検証で PE conf に直結 | V87 未証明 |
| unsatisfied を第7勝ち筋 Ticket 化 | Residual 契約違反 |
| Blocked World の自動購入 | 標本不足 |
| Pool 拡張を公式ランキング変更とみなす | 順位変更の裏口 |

---

## 将来 Shadow の対照アーム（設計メモ・非実装）

| Arm | Prediction | Decision |
|---|---|---|
| D0 | Legacy 固定 | 全 World 同一デフォルト |
| D1 | Legacy 固定 | rank7+unsatisfied Policy のみ |
| D2 | Legacy 固定 | + midhole Explanation/Pool |

評価は Decision 指標（Compliance / Pool Coverage / Overconfidence）。Hit を主 KPI にしない。
