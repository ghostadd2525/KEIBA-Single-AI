# Version48 — CE Boundary & Consumer Analysis

**Date:** 2026-07-28  
**Type:** Audit only

## ⑤ Contract Boundary

### CE が持つべき（コードが宣言する Public Contract）

| 責務 | 根拠 |
|---|---|
| `evaluate_candidates` による CorePublicBundle 提供 | facade Canonical boundary |
| 全出走の CandidateID / Rank / Confidence | Required CE fields |
| Product 選択をしない | docstring |
| （実装として）World/SubWorld/meta を Bundle に載せる | evaluate result |

### CE が持つべきではない（コードが排除）

| 非責務 | 根拠 |
|---|---|
| Candidate Pool / Repick / Purchase / Ticket | facade L7–8; CE L1–5 |
| Win5 券面決定 | optimizer 非結合 |

### 境界の亀裂（監査所見）

| 亀裂 | 内容 |
|---|---|
| B1 | Canonical Bundle と Compatibility View で公開集合が不一致 |
| B2 | Required CE fields に World が無いのに Bundle は World を持つ → 「必須契約」曖昧 |
| B3 | Prediction 主経路が Canonical を使わず薄い投影のみ使用 |
| B4 | CE が World を生成・保持するが、公開 Prediction が破棄 → Public Contract として機能不全 |
| B5 | PE スコア詳細を CE が保持しないため Explain/監査が別経路に依存 |

---

## ⑥ Consumer Analysis

| Consumer | CE の使い方 | 必要情報（実態） | 契約どおり取得できるか |
|---|---|---|---|
| **Canonical 利用者**（research が `evaluate_candidates` 直叩き） | Full Bundle | Rank+Conf+World+meta | **Yes**（直叩き時） |
| **resolve_core** | 互換フル寄り | world/meta/ranking/confidence | **Yes**（features は常に None） |
| **predict_ranking** | 薄い投影 | rank/score のみ | World/meta **不可** |
| **Prediction / Single HTTP** | predict_ranking + confidence → mapper | 公開 Bundle | World/SubWorld **不可**（None 固定） |
| **Single bet_strategy** | ranking/confidence のみ | 上位馬 | World **不要・取得不可** |
| **Win5 optimizer** | CE 非使用 | 独自 Pool/Role/World | CE 契約 **非適用** |
| **GUI（予測画面）** | PredictionBundle 依存が主 | 表示用 rank/prob | World **取得不可**（Bundle 上） |
| **Explain v2（Core）** | CE `explain_payload` | world/meta/candidates | Flag ON かつ evaluate 直利用時 **Yes**；Prediction 経路では **未到達** |
| **Explain（Single Bundle）** | mapper 独自 | rank/confidence | Core explain_payload **非使用**；World **なし** |

### Consumer verdict summary

| Consumer | Contract health |
|---|---|
| evaluate_candidates 直 | OK（Canonical） |
| resolve_core | OK（World 保持） |
| Prediction/Single/GUI 主経路 | **Broken for World** |
| Win5 | **Outside CE contract** |
| Explain | **Split-brain**（Core flag vs mapper） |

---

## Boundary Statement

```text
CE AS IMPLEMENTED:
  + Public canonical bundle with World
  + Compatibility projections that strip World
  + Prediction path that nulls World
  + Win5 path that bypasses CE

→ "AI Core Public Contract" is not a single contract;
   it is a family of incompatible views.
```
