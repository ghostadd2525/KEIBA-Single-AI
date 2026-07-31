# W-S1 Unsatisfied Root Cause Audit

**Date:** 2026-07-28  
**Version:** 57  
**Scope:** Research / classification only — **改善・実装・コード変更禁止**  
**Source:** `w-s1-dual-eval-rows.jsonl`（285R Shadow Dual-Eval）  
**Population:** Unsatisfied **176 / 285 (61.8%)**

---

## Method（推測禁止の根拠）

1. `decision_trace` の `must` / `must_gaps` / `exclude` / `match` のみを使用  
2. Aux による MATCH 拒否は W-S1 `evaluate_v44_logic_form` に **存在しない** → Aux不足は本176件の原因にならない（証拠: trace に Aux ゲート無し）  
3. `polarity_reverse` 専用フィールドは無い → Polarity 失敗は Must 未充足として現れる  
4. 「行きたかった World」= exclude=False のうち `must_gaps` が最少の World。ただし **bug は exception_flag 単一 Must のため最少ギャップに偏る** → 本文では構造分類を主、intended は補助

---

## ① Unsatisfied 分類

### A. 構造（排他分割・176件）

| 構造 | n | 定義（trace） |
|---|---:|---|
| **Must充足後に Exclusion** | **104** | いずれかの World で `must=True` かつ `exclude=True`。かつ「全 Must 失敗」ではない |
| **全 World Must 失敗** | **72** | 全 World で `must` が True でない |
| **Must充足かつ exclude=False** | **0** | 該当なし（Must が True なら常に exclude=True） |

→ Unsatisfied の直接形は「どの World も `match=True` にならない」。  
その内訳は **Exclusion 停止 104** と **Must 未達 72**。

### B. 理由タグ（1レース複数可・trace根拠）

| 理由 | n（レース） | 根拠 |
|---|---:|---|
| 全World_MATCH失敗 | 176 | `v44_world=unsatisfied` |
| Must Signal不足 | 176* | Must 未達または Exclusion 前の Must ギャップが関与（*構造上ほぼ全件に Must 側条件が絡む） |
| Forbidden/Exclusion作動 | 104 | `must=True & exclude=True` が1つ以上 |
| AND未成立 | （Must複数ギャップ側） | `must_gaps` 長さ≥2 の World が存在 |
| exception_flag欠落 | 176 | 全件 `bug_world.must_gaps` に `exception_flag↑`（コーパスに flag 無し — W-S1 method 明記） |
| Signal欠落(restore失敗) | 31 | `restored_ok=false`（Unsatisfied 内） |
| Aux不足 | **0** | Evaluator が Aux で MATCH を落とさない |
| Polarity逆（明示ログ） | **0** | 専用フィールド無し。失敗は Must ギャップに吸収 |
| Forbidden（Must前） | 0 as separate | Exclusion と同一観測（上表 104） |

### C. 主ブロッカー（レースを1つに割当）

「exclude=False で gaps 最少」の World の失敗モード（参考・bug偏りあり）:

| Primary（参考） | n |
|---|---:|
| exception_flag欠落（bug が最少ギャップ） | 127 |
| Must単一不足: multi_path…（mixed） | 47 |
| Must単一不足: aptitude_fit↑ / upper_ability_band↑ | 2 |

**解釈上の注意:** exception_flag は **全285で欠落**。127 は「bug が1ギャップなので intended に選ばれやすい」統計アーティファクト。  
**実構造は上表 A（104 / 72）を正とする。**

---

## ② World別 — どこへ行きたかったか

### A. Must まで到達したが Exclusion で止まった World（104件コホート内・重複可）

| World | must=True & exclude=True の件数 |
|---|---:|
| core_world | 81 |
| midupper_world | 32 |
| midhole_world | 13 |
| rank7_world | 1 |
| mixed_world | 0 |
| bug_world | 0 |

→ Exclusion コホートの主戦場は **core（81）**、次に **midupper（32）**。

### B. 全 Must 失敗 72件での Must ギャップ（World別・言及回数）

| World | 主な must_gaps（72件集合） |
|---|---|
| core | ability_separation↑ 53 / top_gap↑ 37 |
| midupper | upper_ability_band↑ 43 / aptitude_fit↑ 35 / development_pressure↑ 25 |
| midhole | mid_eval_band_open↑ 50 / top_monopoly↓ 27 |
| rank7 | chaos↑ 56 / ability_subordinate↑ 35 / pace_conflict↑ 25 |
| mixed | multi_path≥2 OR unexplained 72（全件） |
| bug | exception_flag↑（構造的に常時） |

### C. intended（gaps最少・参考）

| intended_world | n |
|---|---:|
| bug_world | 127（exception_flag 単一Must偏り） |
| mixed_world | 47 |
| midupper_world | 2 |

---

## ③ Signal不足ランキング

### レース単位（Unsatisfied 176件で、いずれかの World の must_gaps に出現）

W-S1 trace 上のギャップ文字列（上位）:

| Rank | must_gap | 出現レース数（概位・全World言及集計） |
|---|---|---:|
| 1 | exception_flag↑ | 176（全 Unsatisfied） |
| 2 | multi_path≥2 OR unexplained_single | 高頻度（mixed） |
| 3 | chaos↑ / ability_separation↑ / mid_eval_band_open↑ 等 | 72件コホートで顕著 |
| — | restore失敗 | Unsatisfied 内 **31** |

詳細ランキングは `_w-s1-unsat-analysis.json` の `signal_gap_ranking_*`。

### restore

| | n |
|---|---:|
| Unsatisfied かつ restored_ok | 145 |
| Unsatisfied かつ restore失敗 | 31 |

→ Signal欠落は主因の一部（31/176）だが、**145件は restore 成功でも Unsatisfied**。

---

## ④ Trigger不足 — どの Logic で止まったか

| Logic 停止点 | n | 説明 |
|---|---:|---|
| **Exclusion after Must** | 104 | V44 `MATCH = Must AND NOT Exclude` の Exclude 側 |
| **Must never true (all worlds)** | 72 | Positive Match 入口に立てず |
| **mixed Must = multi_path** | （72+α） | 単一 World 意味では mixed Must 未充足 |
| **bug Must = exception_flag** | 176 構造 | flag 不在 ⇒ bug MATCH 不可能 |
| **Aux** | 0 | 停止点にならない（実装仕様） |

core が 81件で Must 成立しても exclude される事実は、V44 の CORE_EXCLUDE（chaos / sfp / late∧sustained / mid_band 等）が **観測極性下で同時に真**になっていることを示す（trace は exclude bool のみ。個別 Exclude 条項の内訳フィールドは W-S1 ログに無い）。

---

## ⑤ Potential Positive Match（Near Miss）

定義（本監査）:

> ある World で `exclude=False` かつ `must_gaps` が **ちょうど1つ**（Signal 種類を増やさず、既存1軸が極性PASSすれば Must 充足しうる）

| 区分 | n | 内容 |
|---|---:|---|
| いずれかの World で1ギャップ | 176 | 全 Unsatisfied |
| うち **極性Signal 1軸**（true near-miss） | **63** | core/midupper/midhole の top_gap / separation / monopoly / upper_band / aptitude 等 |
| うち **mixed multi_path 論理** | **113** | Signal1本追加では埋まらない設計Must |
| bug exception_flag を「最初の1ギャップ」にした場合 | （別集計で偏り） | flag 自体がコーパスに無い → **Signal追加なしでは不可** |

true near-miss 内訳（World）: midhole 31 / midupper 22 / core 10  
true near-miss 内訳（gap）: top_monopoly↓ 21 / upper_ability_band↑ 14 / mid_eval_band_open↑ 10 / aptitude_fit↑ 7 / ability_separation↑ 6 / top_gap↑ 4 / development_pressure↑ 1  

→ **Signal追加なしで Positive Match になりうる Near Miss = 63件**（極性1軸）。  
113件は mixed 論理ギャップ、残りは Exclusion 側が本体。

詳細: `w-s1-near-miss.md`

---

## ⑥ Governance

# **C — 設計不足**

| 根拠 | |
|---|---|
| Must=True のとき常に exclude=True（0件の「Mustのみ成功」） | Exclusion 設計と観測極性の交差が Unsatisfied の主構造（104） |
| mixed Must が multi_path 依存 | 113件は単一Signalでは解消しない |
| exception_flag 必須なのにコーパスに非存在 | bug 経路が設計上閉じている |
| 副次 **B** | 72件の全Must失敗 + restore失敗31 + 極性Mustギャップ |

**A（実装可能）ではない:** Production Trigger を触れば直る類の単バグではない（Shadow 観測上の仕様ギャップ）。

---

## Index

| Doc | Content |
|---|---|
| `w-s1-unsatisfied-root-cause.md` | 本ファイル |
| `w-s1-near-miss.md` | Near Miss 63 / 113 |
| `w-s1-trigger-blockers.md` | Logic 停止点 |
| `w-s1-governance.md` | Governance C |

---

*Version57 — classification only. No code changes.*
