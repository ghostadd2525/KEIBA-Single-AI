# Version49 Governance — Prediction Contract Audit

## Verdict: **C** — Prediction 契約が分裂

## 判定

| 選択肢 | 意味 | 本 Audit |
|---|---|---|
| A | Prediction は CE 公開契約を利用 | 否（`evaluate_candidates` を公開利用しない） |
| B | 一部独自契約 | 否（主経路全体が CE Canonical と不一致） |
| C | Prediction 契約が分裂 | **採択** |

---

## Evidence

1. **HTTP 公開正本** = `PredictionBundle` (`single-prediction-bundle/2.0`)。
2. **AI Core Canonical** = `evaluate_candidates` → CorePublicBundle（World 保持）だが Prediction 主経路は未使用。
3. **生成入力** = `predict_ranking`（World キー無しの互換ビュー）。
4. **中間 DTO** = `prediction_response`（World フィールド無し）。
5. **Mapper** = `evaluation.world = None` / `sub_world = None` ハードコード。
6. **Mock 経路** = fixture/template Bundle（CE 非経由）が同 HTTP 契約名で並存。

→ 「Prediction が CE を使う」は **内部で evaluate を間接実行するだけ**で、**公開契約として CE を採用していない**。複数 DTO が同名「予測」の下に分裂している。

---

## Answers to audit questions（短答）

| # | 結論 |
|---|---|
| ① Entry | HTTP `/v1/predictions` (+ Adapter/Single/Mock) |
| ② Lineage | HTTP→Adapter→Single predict→**predict_ranking**→Mapper→Bundle |
| ③ Mapper | World/SubWorld **None 固定**; score→win_prob 改名; Core explain 不使用 |
| ④ Canonical | 公開正本 = **PredictionBundle**。生成は **predict_ranking** 系。**evaluate_candidates ではない** |
| ⑤ Duplicate | CE / RankingResult / prediction_response / Bundle / Mock の **多重契約** |
| ⑥ Loss | 主因 = `predict_ranking` 削除 + Mapper None 固定 |
| ⑦ Governance | **C** |

---

## Relation to V48

| V48 | V49 |
|---|---|
| CE は World を保持、Prediction は None | None 化の **コード位置と契約分裂**を確定 |
| 公開契約崩壊（CE 視点） | Prediction 視点でも **正本が CE ではない**と証明 |

---

## What this phase did NOT do

- コード変更 / 実装 / 改善
- Prediction / PE / CE / AI / World / Trigger / Signal / Role / Required / Pool / Production 変更

---

## Artifacts

- `docs/architecture/v49-prediction-contract.md`
- `docs/architecture/v49-contract-lineage.md`
- `docs/architecture/v49-mapper-audit.md`
- `docs/architecture/v49-information-loss.md`
- `docs/architecture/v49-governance.md`

## Expected Next Action

Prediction 契約分裂（C）を前提にした次方針の指示待ち。実装は開始しない。
