# Version106 — Single AI Consumer Contract

**Date:** 2026-07-28  
**Status:** Shadow Observation / Audit only · **実装禁止**  
**Parents:** ADR-009 · ADR-010 · ADR-008 · V103 Payload · V105 · V88/V95 Decision Policy  
**Locks:** Prediction / Ranking / Score / Trigger / World / Near Miss / Affinity / EC / Evidence / Decision Logic — **変更禁止**  
**評価対象:** Consumer Readiness のみ（Hit / ROI / Decision 最適化 / Evidence 追加 / 新 Semantic・Feature — **禁止**）

---

## 一文

**Single AI は Core Payload で「どの Decision Policy を選ぶか／何を説明するか」は足りる。券種・買い目の実行そのものは Decision Registry＋Prediction 読取の責務であり、Core 欠落ではない。**

---

## 1. Consumer ユースケース ↔ Core 充足

| UC | 要求 | Core で足りる入力 | Core 外（設計上） | Readiness |
|---|---|---|---|---|
| **UC-S1 券種選択** | World / Residual に応じた Ticket Strategy 切替 | `world_id`, `near_miss.residual_class`, `near_miss.near_world`（V88/V95） | Decision Policy 表（V88/V95）・資金・オッズ | **PARTIAL** — Selector は充足。Policy 本体は KEEP_DERIVED |
| **UC-S2 買い目生成** | 公式 Rank 上のフォーメーション | `prediction.ranks/scores/top1` + Pool 方針の Selector（World/NM） | Pool サイズ定数（例: V92 TopK/PoolN）・オッズ・stake | **PARTIAL** — 馬順は充足。枚数/保険は Decision |
| **UC-S3 説明生成** | なぜこの World/残余か | World, trace, Transition, Must Gaps, Exclusion Reasons, Near Miss Class, Affinity, EC | 自然文テンプレ（Presentation; V103 MS-6 DO_NOT_EXPORT） | **READY**（構造化）。散文は KEEP_DERIVED |

---

## 2. Payload 別 — Single 必須度

凡例: **必須** = 当該 UC の Selector/説明に必要 · **推奨** = 品質向上 · **不要** = Single UC に不要（または禁止用途）

| Payload | 券種 | 買い目 | 説明 | 根拠 |
|---|---|---|---|---|
| World (`world_id`) | **必須** | **必須**（Policy キー） | **必須** | V88; ADR-008 |
| Near Miss（存在） | **必須**（unsatisfied） | **必須**（保守帯判定） | **必須** | V95; DL-C6 |
| Near Miss Class | **必須**（NM vs Pure） | **推奨** | **必須** | V95; V103 MS-5 |
| Affinity | **不要**（自動券種に使わない） | **不要** | **推奨** | V97 NO_VALUE; V103 MS-2（説明） |
| Exclusion Reasons | **不要**（券種ゲートに直結しない） | **不要** | **必須** | V103 MS-3; V95 Explain |
| Explanation Confidence | **不要**（Skip 閾値化禁止） | **不要** | **必須**（確度表示） | ADR-010; V101 MUST NOT |
| Transition | **推奨** | **不要** | **必須** | V103 既 first-class; ADR-009 |
| Must Gaps | **推奨**（Blocked 判定補助） | **不要** | **必須** | decision_trace; V101 入力 |

Prediction Rank/Score は Core Payload 既出（V103）— 買い目 **必須**。本監査は意味変更しない。

---

## 3. 不足 Payload 抽出（Semantic 新造なし）

| Gap ID | 不足の見え方 | 分類 | 扱い |
|---|---|---|---|
| SG-1 | 自然文の「なぜ」本文が Core に無い | **不要（Core）** | Presentation が Exclusion/World/NM から生成（MS-6） |
| SG-2 | Expected Strategy 本文が race に無い | **KEEP_DERIVED** | `expected_strategy_ref` + V75 レジストリ（V103 MS-1） |
| SG-3 | 券種枚数・フォーメーション定数が Core に無い | **Decision Registry** | V88/V95/V92 Policy — Core に載せない（PCS-7） |
| SG-4 | オッズ・予算が Core に無い | **Market / Product 入力** | ADR-010 がオッズを Core EC から排除。新 Semantic にしない |
| SG-5 | PROMOTE 4 件の製品 serialize 未配線 | **Wiring Gap** | V103「Not authorized」— 意味不足ではない |

**新 Semantic / Feature 候補: なし（禁止遵守）。**

---

## 4. Single AI Consumer Contract（要約 MUST）

| ID | 規則 |
|---|---|
| S-CC-0 | Core は read-only。CEW / Rank を書き換えない |
| S-CC-1 | 券種・買い目は Decision Layer が生成。Core は Selector＋Prediction のみ |
| S-CC-2 | Affinity を Positive Ticket / 自動 Skip 閾値に使わない（V97; V101） |
| S-CC-3 | EC を勝率・購入推奨度に表示しない（ADR-010） |
| S-CC-4 | Near Miss を本採用 World Ticket にコピーしない（V95; DL-C6） |
| S-CC-5 | 説明散文は Consumer/Presentation。Core に要求しない（PCS-5） |

---

## 5. Verdict（Single）

| 軸 | Verdict |
|---|---|
| 説明生成 | **READY**（構造化入力充足。配線は別） |
| 券種選択 | **PARTIAL_READY**（Selector 充足 / Policy・Market は Core 外） |
| 買い目生成 | **PARTIAL_READY**（Rank 充足 / 枚数・stake は Decision） |
| **Overall** | **PARTIAL_READY** — Core 改善不要。Consumer/Decision Registry・配線の問題 |

---

## Related

- `v106-win5-consumer-contract.md`
- `v106-payload-requirement-matrix.md`
- `v106-contract-gap-report.md`
- `v106-governance.md`
