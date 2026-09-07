# V53 — Assembly Responsibility & Ownership

**Date:** 2026-07-28  
**Scope:** Research only  
**Companion:** `v53-prediction-assembly-boundary.md`

---

## ① Assembly Responsibility（持つべき責務）

コードと契約から導かれる **Assembly の正当責務**（AI Core / Presentation に置いてはならないもの）:

| ID | Responsibility | Evidence |
|---|---|---|
| A1 | **Product DTO 生成** | `prediction_response` / `PredictionBundle` は Product schema（`single.models`, `PredictionBundle.d.ts`） |
| A2 | **Race 情報付与** | `_race_info` が `get_race` + catalog `race_meta` を合成（CE に date/venue 等なし — V52） |
| A3 | **BetBuilder 統合** | `predict` → `build_bet_plan` → `build_bets` → `items`（`single/prediction`） |
| A4 | **Product View 生成** | Bundle は ADR-050 上 Product Public View（非 Canonical） |
| A5 | **Identity bridge** | public_race_id ↔ core_race_id（`diagnose_inference`, `resolve_identity`） |
| A6 | **Mark overlay（Product 規則）** | `_MARK_BY_RANK` → honmei/taikou/…（Mapper）; Challenge が消費 |
| A7 | **Explain Product 合成** | Bundle `explain` narrative/reasons（Mapper）※ Core `explain_payload` とは別系統（V50 C9/C10） |
| A8 | **Fallback / Mock 選択** | Adapter Real vs Mock / `catalog_to_prediction_bundle` |
| A9 | **Provenance meta** | `engine_source`, `fallback_reason`（Bundle 契約外 envelope） |

**Assembly が持つべきでない責務**（後述 Leak）:

- Rank / Confidence / World の再計算・再定義  
- PE Feature/Score/Rank 内部  
- Presentation レイアウト  
- Canonical 事実の破棄（`world=None` 固定は欠陥）

---

## ② Ownership

| Information | Owner | Producer (code) | Assembly role | Notes |
|---|---|---|---|---|
| **Rank** | **AI Core** | Ranker → CE `candidates[].Rank` / `predict_ranking` | **Pass-through / map** to `model_rank` | BetStrategy: “no re-ranking” |
| **Confidence** | **AI Core** | ConfidenceBuilder → `overall_confidence` / per-horse | Pass-through to `ai_confidence` / Bet propagate | BetBuilder: min over legs, no recalc |
| **World** | **AI Core** | WorldClassifier → CE `world` | **Must project** to `evaluation.world` | 現行 Mapper が `None` → **Leak** |
| **SubWorld** | **AI Core** | WorldClassifier → CE `sub_world` | Must project | 同上 `None` |
| **Meta** | **AI Core** | `build_race_meta` / `detect_race_meta` → CE `meta` | Optional expose / not rewrite | Bundle `race_info` とは **別物** |
| **RaceInfo** | **RaceData / Catalog** | `get_race`, catalog race rows, `_race_info` | **Attach / normalize** | Not owned by AI Core |
| **BettingRecommendations** | **Single Product (Bet)** | `build_bet_plan` + `build_bets` | **Integrate** into Bundle | BetBuilder docstring: no CE access |
| **Catalog** | **Expect Product data** | `data.load_races`, domain catalog helpers | **Input source** for list/mock/meta | Parallel to Core; not Core truth |
| **ChallengeMark**（◎○▲△ / mark） | **Product Assembly rule** | Mapper `_MARK_BY_RANK`; Challenge `axis_rivals_from_bundle` reads | **Define overlay from Rank** | Owner ≠ AI Core; derived Product label |

### Ownership rules（監査結論）

1. Canonical facts（Rank, Confidence, World, SubWorld, Meta）の Owner は **AI Core のみ**（V50 と一致）。  
2. RaceInfo / Catalog / BettingRecommendations / ChallengeMark の Owner は **Product 側**（RaceData・Bet・Assembly 規則）。  
3. Assembly は Core 事実の **Owner ではなく Composer**。  
4. ChallengeMark は Rank の関数だが、**意味ラベルの Owner は Product**（Core は mark を出さない）。

---

## ⑥ Responsibility Leak

### AI Core が持つべきでない責務

| Leak? | Item | Evidence |
|---|---|---|
| **No (guarded)** | PredictionBundle 生成 | Facade: “No Product-stage logic” |
| **No (guarded)** | Bet expansion | BetBuilder isolated in `ai_platform.single` |
| **Observed risk** | Compatibility views が Product 入口の事実上の正 | `predict` が CE ではなく `predict_ranking` を使用; bet_strategy: “CE Facade not yet approved” → Canonical 未接続 |

Core が Bundle/Bet を直接持っている事実は **コード上なし**。漏洩は「Product が Compatibility view を正として組む」側。

### Assembly が持つべきでない責務

| Leak? | Item | Evidence |
|---|---|---|
| **Yes** | World 事実の無効化 | `evaluation.world = None` hardcoded in Mapper |
| **Yes** | Canonical 入力の回避 | Assembly 入口が CE ではなく ranking/confidence views |
| **Borderline** | Explain 二重系統 | Core `explain_payload` vs Mapper Bundle explain — Assembly が Core Explain を無視して再創作 |
| **Acceptable if owned** | Mark 規則 | Product overlay — OK if not claimed as Core |
| **Structural** | 責務のモジュール分散 | predict + models + mapper + adapter + mock = 境界が名前として存在しない |

### Product / Presentation が持つべきでない責務

| Layer | Leak? | Item | Evidence |
|---|---|---|---|
| Product HTTP | **Borderline** | “PredictionBundle = 共通契約” を Canonical 扱い | `main.py` コメント; ADR-050 と緊張 |
| Presentation GUI | **No** | 合成 | bind/Guard のみ; RaceData/Bet を呼ばない |
| Challenge | **No** | mark 再定義 | stored Bundle から抽出（読取） |
| Functions | **Borderline** | catalog projection / Ready | Assembly 結果の再解釈; 合成は Upstream |

### Leak summary

| Severity | Finding |
|---|---|
| High | Assembly（Mapper）による World/SubWorld 破棄 |
| Medium | Assembly が Canonical CE を入力に使っていない |
| Medium | Assembly 実体が未命名・分散 |
| Low | Presentation 合成なし（健全） |
| Low | Core に Bet/Bundle なし（健全） |

**結論:** 責務分離は Assembly 境界で **可能**。現行は **一部混在（B）**。分離不能（C）ではない。

---

*V53 Assembly Responsibility — research only.*
