# Version48 — CE Responsibility Audit

**Date:** 2026-07-28  
**Type:** Research / Audit only（改善・実装禁止）  
**Canonical public boundary (code):**

```text
evaluate_candidates(race_id) -> CorePublicBundle | None
```

出典: `ai_platform/core/facade/core_facade.py` L4–8, L24–30。

## 用語

| 用語 | コード実体 |
|---|---|
| **CE** | Candidate Evaluation = `CorePipeline.evaluate` が返す **CorePublicBundle** + 行投影 `CandidateEvaluationProjector` |
| **CE Facade** | `evaluate_candidates` / `resolve_core` / `predict_ranking` / `predict_confidence` |
| **PE（狭義）** | Scorer+Ranker（CE 内部ステージ） |
| **Prediction（公開）** | Single `predict` → mapper → PredictionBundle / HTTP `/v1/predictions` |

---

## ① CE Responsibility（責務列挙）

### コードが明示する責務

| ID | 責務 | 根拠 |
|---|---|---|
| C1 | 全出走馬の評価行投影（Rank / Confidence） | Projector; “Every runner…projected to CE” |
| C2 | CorePublicBundle の組み立て | `CorePipeline.evaluate` result dict |
| C3 | AI Core 公開境界の提供 | facade: Canonical public boundary = evaluate_candidates |
| C4 | Product 選択を行わない | “No Product-stage selection”; Pool/Repick 非呼出 |
| C5 | World/SubWorld をバンドルへ載せる | result[`world`]/[`sub_world`]; 行の WorldMeta |
| C6 | meta / confidence をバンドルへ載せる | result keys |
| C7 | （条件付）explain_payload 付与 | Flag ON 時のみ |

### CE が内部で実行するが「公開契約の必須フィールド」ではない処理

| ID | 処理 | 公開への残り方 |
|---|---|---|
| P1 Feature→Score→Rank | PE 狭義 | Rank / Confidence に圧縮 |
| P2 World 分類 | 後段ラベル | world キー + WorldMeta（後で消費者により破棄されうる） |

### CE が持たない責務（明示）

| 非責務 | 根拠 |
|---|---|
| Candidate Pool / Repick / Ticket / Purchase | facade / CE docstring |
| Win5 券面最適化 | `demo_ticket_optimizer_core` は `evaluate_candidates` を呼ばない |
| PredictionBundle 契約整形 | Single mapper 側 |

---

## CE が「保持・公開・破棄」する情報（要約）

| 情報 | CE Bundle 保持 | 主公開経路での運命 |
|---|---|---|
| Rank / Confidence | Yes（必須） | Prediction へ伝播 |
| World / SubWorld | Yes（バンドル＋行 Meta） | `predict_ranking` 欠落 → Single/Prediction **world=None** |
| meta | Yes | `predict_ranking` 欠落; `resolve_core` は保持 |
| win_prob / base/adjusted score | evaluate 内部のみ | **CE 行に非投影**（Confidence に置換） |
| Required / Role / Pool | **保持しない** | 最初から契約外 |

詳細は Input/Output/Information Loss 文書。

## Governance 予告

Canonical CE は World を持つが、互換ビューと Prediction が破棄 → **公開契約が経路依存で崩れる** → `v48-governance.md` **C**。
