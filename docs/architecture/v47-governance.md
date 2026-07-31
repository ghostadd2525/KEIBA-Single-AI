# Version47 Governance — PE Responsibility Decomposition

## Verdict: **C** — 責務が構造的に混在

## 判定基準

| 選択肢 | 意味 | 本 Audit |
|---|---|---|
| A | 責務分離は適切 | 否 |
| B | 一部責務混在 | 否（局所ではなくパイプライン構造） |
| C | 責務が構造的に混在 | **採択** |

---

## Evidence

1. **同一 `CorePipeline.evaluate` に** Feature→Score→Rank→Confidence→**World 生成**→CE 投影が直列同居（`candidate_evaluation/__init__.py` L64–93）。
2. **Scorer/Ranker は World/SubWorld/Pool/Role を参照しない**（パッケージ内マッチ 0）一方、World は順位後に付与されるだけ → 「消費」ではなく「後付けラベル」。
3. **公開 Prediction は `world=None`**（mapper）で勝ち筋をさらに切断。
4. **Scorer 内にハードコード調整・softmax 温度・タイ解消・モデル欠落 fallback** があり、明示 World 政策とは別の暗黙順位政策が同居（Hidden Policies H1–H6）。
5. Pool/Ticket 非呼出は docstring で守られており、**購入責務の混入は無い**（この一点は境界 PASS）。

---

## Responsibility Separation Score（監査用）

| 観点 | 状態 |
|---|---|
| Score vs Rank 分離 | モジュール分離あり（比較的明確） |
| Rank vs Confidence | 同パイプライン後段（混在中） |
| Rank vs World | 同パイプライン・World 非消費（構造矛盾） |
| PE vs Pool | 分離（明示） |
| PE vs Prediction facade | World drop で契約切断 |

→ 全体として **C（構造的混在）**。

---

## Relation to V35 / V36 / V43–V46

| Version | 関係 |
|---|---|
| V35 | World 非消費・事後ラベルの先行証明。本 V47 は責務マトリクスへ一般化 |
| V36 | I3 World→PE が設計推奨。実装は未到達（本 Audit が再確認） |
| V43–V46 | World 側契約〜移行設計。PE 側は依然 World 非消費 |

---

## What this phase did NOT do

- コード変更 / 実装 / 改善
- Prediction / PE / CE / AI / World / Trigger / Signal / Role / Required / Pool / Production 変更

---

## Artifacts

- `docs/architecture/v47-pe-responsibility.md`
- `docs/architecture/v47-pe-input-contract.md`
- `docs/architecture/v47-pe-dependency.md`
- `docs/architecture/v47-pe-decision-pipeline.md`
- `docs/architecture/v47-pe-boundary.md`
- `docs/architecture/v47-governance.md`

## Expected Next Action

PE 責務分解（判定 C）を前提にした次方針の指示待ち。実装は開始しない。
