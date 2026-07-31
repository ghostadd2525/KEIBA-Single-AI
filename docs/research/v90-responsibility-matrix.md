# Version90 — Responsibility Matrix

**Date:** 2026-07-28  
**Parent:** ADR-008 / `v90-decision-layer-adr.md`  
**実装禁止**

---

## 層 × 関心事

| 関心事 | Prediction Engine | Confidence (Global) | World Label | Decision Layer |
|---|---|---|---|---|
| Rank 生成 | **Owner** | — | — | **禁止** |
| Score 生成 | **Owner** | — | — | **禁止** |
| Rank 変更 | **Owner のみ** | 禁止 | 禁止 | **禁止** |
| Global Calibration | 入力可 | **Owner** | 禁止（主エンジン） | 表示ポリシーのみ可 |
| World Prior 主エンジン | 禁止 | **禁止（未証明）** | — | 禁止 |
| Ticket Strategy | 禁止 | — | Selector 入力 | **Owner** |
| Candidate Pool（表示） | 禁止（公式順は PE） | — | Selector | **Owner**（配列非 mutate） |
| Explanation | 禁止（公式文以外） | — | Selector | **Owner** |
| Risk / 見送り | 禁止 | — | Selector | **Owner** |
| Confidence 表示ラベル | — | 値の供給 | Selector | **Owner**（再ランク禁止） |
| Feature Flag | PE flags 分離 | calib flags 分離 | — | **Decision flags** |
| Production Cutover | PE ゲート | Calib ゲート | Trigger ゲート | **Decision ゲート（別）** |

---

## Owner マトリクス

| 成果物 / API | Owner | 変更承認 |
|---|---|---|
| Official Prediction bundle | PE | ADR-003 |
| Global confidence / p_base' | Calibration Owner | 別 ADR/Decision |
| CEW / Trigger World | World/Trigger Owner | 既存 World ADR 系 |
| Decision Ticket plan | **Decision Owner** | ADR-008 + Flag |
| Decision Pool view | **Decision Owner** | ADR-008 + Flag |
| Decision Explanation | **Decision Owner** | ADR-008 + Flag |
| Decision Risk gate | **Decision Owner** | ADR-008 + Flag |

---

## データフロー契約

```text
PE ──(rank, score)──► Decision   【read-only】
Calib ──(global conf)──► Decision 【optional, display】
World ──(world_id)──► Decision   【selector】
Decision ──(ticket/pool/explain/risk)──► UX / Purchase Adapter
Decision ──✗──► PE                【逆書き込み禁止】
```

---

## Ready World の Decision 責務（V88/V89）

| World | Decision Owner の既定方針 |
|---|---|
| `rank7_world` | Ticket 分散 · Pool 拡張 · 混戦 Explanation · Conf 過信抑制 |
| `unsatisfied` | Ticket 既定維持 · 残余 Explanation · 勝ち筋化禁止 |
| `midhole_world` | Pool/Explain 中心 · 自動 Ticket は控えめ（Partial） |
| Blocked | SKIP / 自動 Ticket 禁止 |

---

## 違反時の扱い

| 違反 | 対応 |
|---|---|
| Decision が Rank を書換 | **Release blocker** / Flag 強制 OFF |
| World weight を PE に注入 | **Architecture violation**（ADR-008 Rejected） |
| Decision Flag と PE Pilot の同時 ON（归因なし） | **禁止**（運用） |
