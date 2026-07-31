# Version48 Governance — Candidate Evaluation Contract Audit

## Verdict: **C** — 公開契約が構造的に崩れている

## 判定

| 選択肢 | 意味 | 本 Audit |
|---|---|---|
| A | CE Contract は設計どおり | 否 |
| B | 一部契約欠落 | 否（欠落ではなく経路分裂） |
| C | 公開契約が構造的に崩れている | **採択** |

---

## Evidence

1. **Canonical 宣言:** `evaluate_candidates` → CorePublicBundle（facade docstring）。
2. **Canonical は World/SubWorld/meta を保持**（`CorePipeline.evaluate` L104–108）。
3. **主予測経路は Canonical を使わない:** Single `predict` は `predict_ranking` + `predict_confidence` のみ（world キー無し）。
4. **PredictionBundle は `evaluation.world = None` をハードコード**（mapper L410–411）。
5. **Required CE fields** は CandidateID/Rank/Confidence のみで、World の必須性が契約文面上あいまい。
6. **Win5 は CE を呼ばない** — 別契約が並存。
7. **Explain が二重** — Core `explain_payload`（flag）と Single mapper explain。

→ 「CE = AI Core の単一 Public Contract」はコード上宣言されているが、**消費側が契約を遵守しておらず、投影が情報を破壊する**ため、公開契約は構造的に崩壊している。

---

## What still works

- Rank / Confidence の予測主経路伝播
- Pool/Ticket を CE に混ぜない境界（排除は成功）
- `evaluate_candidates` / `resolve_core` 直叩きでは World 取得可能（研究・一部ツール）

---

## Relation to V47

| V47 | V48 |
|---|---|
| PE は World を順位に使わない | CE は World を保持するが公開予測が破棄 |
| CorePipeline に World 同梱（混在） | 同梱された World が Public に届かない（契約崩壊） |

---

## What this phase did NOT do

- コード変更 / 実装 / 改善
- Prediction / PE / CE / AI / World / Trigger / Signal / Role / Required / Pool / Production 変更

---

## Artifacts

- `docs/architecture/v48-ce-responsibility.md`
- `docs/architecture/v48-ce-input-contract.md`
- `docs/architecture/v48-ce-output-contract.md`
- `docs/architecture/v48-information-loss.md`
- `docs/architecture/v48-ce-boundary.md`
- `docs/architecture/v48-governance.md`

## Expected Next Action

CE 公開契約崩壊（C）を前提にした次方針の指示待ち。実装は開始しない。
