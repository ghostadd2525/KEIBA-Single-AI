# Version106 — Win5 AI Consumer Contract

**Date:** 2026-07-28  
**Status:** Shadow Observation / Audit only · **実装禁止**  
**Parents:** ADR-009 · ADR-010 · ADR-008 · V103 · V105 · V88/V92/V95 · V97  
**Locks:** 同上（Core / Decision Logic / Evidence — **変更禁止**）  
**評価対象:** Consumer Readiness のみ

---

## 一文

**Win5 の候補数・保険・難易度は Decision/Product の運用概念である。Core は World/Near Miss/EC という Selector を供給し、難易度スカラーや保険チケットを Core に新設しない。**

---

## 1. Consumer ユースケース ↔ Core 充足

| UC | 要求（ユーザー監査項目） | Core で足りる入力 | 既存 Decision 対応 | Readiness |
|---|---|---|---|---|
| **UC-W1 候補数決定** | 何頭まで候補に入れるか | `world_id`, Near Miss Class / `near_world`, Prediction ranks | Candidate Pool / TopK·PoolN（V88; V92 `Top5_Pool7` 等） | **PARTIAL** — Selector 充足。Pool 定数は Registry |
| **UC-W2 保険戦略** | 本命外の抑え・分散 | World / NM（保守・抑制プロファイル） | Risk + Ticket 保守（V88 unsatisfied; V95 Near Miss） | **PARTIAL** — 抑制 Selector 充足。保険券そのものは Decision（PCS-7） |
| **UC-W3 レース難易度判断** | 難しい/混戦か | World（例: rank7=混戦语义 V88）、NM、EC（説明の確定度） | **「難易度」first-class は Core に無い** | **DERIVE_OR_EXTERNAL** — 新 Semantic 禁止。KEEP_DERIVED |

---

## 2. Payload 別 — Win5 必須度

| Payload | 候補数 | 保険 | 難易度判断 | 根拠 |
|---|---|---|---|---|
| World | **必須** | **必須** | **必須**（语义プロキシ） | V88 Pool/Risk; rank7 混戦説明 |
| Near Miss | **必須**（unsatisfied 時 Pool 拡張抑制） | **必須**（保守） | **推奨** | V95; DL-C6 |
| Near Miss Class | **必須** | **必須** | **推奨** | V95 NM vs Pure; V103 MS-5（Win5 H） |
| Affinity | **不要**（Pool 自動拡張キーにしない） | **不要**（V97 Risk SKIP 無価値） | **推奨**（説明のみ） | V97; V103 Win5=M |
| Exclusion Reasons | **不要** | **不要** | **推奨**（監査説明） | V103 MS-3 Win5=M |
| Explanation Confidence | **不要**（候補数の直接閾値禁止） | **不要**（Skip 自動閾値禁止） | **推奨**（「説明が閉じない」≠市場難易度） | V101 MUST NOT |
| Transition | **不要** | **不要** | **推奨** | 説明・監査 |
| Must Gaps | **推奨** | **推奨**（未充足の根拠） | **推奨** | decision_trace |

---

## 3. 「難易度」の扱い（重要）

| 選択肢 | 判定 |
|---|---|
| Core に `race_difficulty` を追加 | **禁止**（新 Semantic / Feature） |
| World + Near Miss + EC + field_size（レースカード）から Consumer が合成 | **KEEP_DERIVED** |
| オッズ分散・人気歪みを難易度にする | **Market / EV-D 入力**（Core 外・ADR-010） |

V88 は rank7 を「混戦寄り」と **Explanation/Ticket 分散**に接続済み。これは難易度スカラーの代替セマンティクスであり、追加定義しない。

---

## 4. 不足 Payload 抽出（Semantic 新造なし）

| Gap ID | 不足の見え方 | 分類 | 扱い |
|---|---|---|---|
| WG-1 | `candidate_count` が Core に無い | **Decision Registry** | World/NM → V88/V92 Pool 表で導出 |
| WG-2 | `insurance_ticket` が Core に無い | **Decision 出力** | PCS-7: Ticket を Core に含めない |
| WG-3 | `race_difficulty` が Core に無い | **KEEP_DERIVED / External** | World/NM/EC/race meta から Consumer 合成。新 Semantic 禁止 |
| WG-4 | field_size が Semantic Payload に無い | **Race Card / Product** | V88 が field_size を Ticket 分散条件に使用 — Core 意味ではない |
| WG-5 | Affinity で保険/Skip したいが価値なし | **非 Gap** | V97 NO_VALUE — 要件側を捨てる |
| WG-6 | PROMOTE serialize 未配線 | **Wiring Gap** | V103 Not authorized |

**新 Semantic / Feature 候補: なし。**

---

## 5. Win5 AI Consumer Contract（要約 MUST）

| ID | 規則 |
|---|---|
| W-CC-0 | Core read-only。Positive Ticket 化に Near Miss/Affinity を使わない（DL-C6; V103） |
| W-CC-1 | 候補数は Decision Pool Policy。Core は World/NM Selector のみ |
| W-CC-2 | 保険は Decision Risk/Ticket。Core は抑制プロファイル Selector のみ |
| W-CC-3 | 難易度スカラーを Core に要求しない。KEEP_DERIVED または Market |
| W-CC-4 | EC を候補数・保険の自動閾値にしない（V101） |
| W-CC-5 | EV-S を EV-D ROI 成功指標に混ぜない（V105; ADR-009） |

---

## 6. Verdict（Win5）

| 軸 | Verdict |
|---|---|
| 候補数決定 | **PARTIAL_READY** |
| 保険戦略 | **PARTIAL_READY** |
| レース難易度判断 | **KEEP_DERIVED_REQUIRED**（Core first-class 不足ではない） |
| **Overall** | **PARTIAL_READY** — Core Contract 固定のまま Consumer 導出で足りる |

---

## Related

- `v106-single-consumer-contract.md`
- `v106-payload-requirement-matrix.md`
- `v106-contract-gap-report.md`
- `v106-governance.md`
