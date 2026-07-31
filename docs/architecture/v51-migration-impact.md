# V51 — Migration Impact（ADR-050）

**Date:** 2026-07-28  
**Scope:** Compatibility / Risk / Rollback — design inventory only  
**Locks:** 実装禁止（Prediction / PE / CE / AI / World / Trigger / Signal / Production）

---

## ④ Compatibility — PredictionBundle vs CorePublicBundle

### Verdict

**スキーマ非互換。破壊的置換は不可。View Adapter 必須。**

ADR-050 Decision D4 と整合: PredictionBundle は **Product Public View（非 Canonical）** として存続させるのが唯一の安全な移行形。

### Field-level comparison（代表）

| Concern | PredictionBundle 2.0 | CorePublicBundle | Compatible? |
|---|---|---|---|
| Identity | `schema_version`, `race_id` | `race_id` (+ frozen shape) | Partial |
| Ranking | Product marks / horses | `candidates[]` Rank/Score | **No**（写像必要） |
| World | `evaluation.world` = **None** | `world`, `sub_world` | **No**（欠落） |
| Meta difficulty | 限定 / 欠落しがち | `meta.race_leg_difficulty` 等 | **No** |
| Confidence | `ai_confidence` Product | `confidence` Core | Partial（写像） |
| race_info | UI 豊富 | Core 最小 | **No**（View 側で補完） |
| status / warnings | Product | Core / Projector | Partial |
| versions | model/core/product | Core versions | Partial |
| Mock source | fixtures | N/A | Separate |

### Compatibility modes（設計オプション・未実装）

| Mode | Description | Breaking? |
|---|---|---|
| **M0 Status quo** | Bundle = HTTP 契約; CE 非公開 | N/A（ADR 未適用） |
| **M1 Dual-publish** | HTTP meta または並列 endpoint で CE; Bundle 維持 | Low（additive） |
| **M2 CE→View Adapter** | evaluate_candidates → PredictionBundle; world を正しく投影 | Medium（Mapper 置換） |
| **M3 Bundle replace** | HTTP 生 CE のみ | **High / Breaking** |
| **M4 Deprecate predict_*** | Compatibility views 廃止 | High（Single/Analytics） |

**推奨境界（設計）:** M1 → M2。M3/M4 は別 ADR + Client 合意後。

### 現行 Mapper 欠陥との関係

`prediction_response_to_bundle` の `evaluation.world = None` は:

- ADR-050 下では **Canonical の欠陥ではない**（View defect）
- M2 実装時に **修正対象**（CE.world を View に写す）
- M0 のままでは **互換性問題として残存**

---

## ⑤ Migration Risk

### High

| ID | Risk | Why | Blast radius |
|---|---|---|---|
| H1 | GUI ContractGuard 失敗 | `validatePredictionBundle` が schema 固定 | 全 Expect UI |
| H2 | `/v1/predictions` 破壊的変更 | 外部・Functions・Ops が Bundle 前提 | HTTP + CF + tests |
| H3 | Production cutover 一発適用 | Ready 判定・Mock/Real 切替と衝突 | Production |
| H4 | world 露出による Product 意味変化 | UI/Explain が None 前提の可能性 | GUI / Conversation |
| H5 | Mock と Real の契約分岐拡大 | Mock が CE を持たない | Adapter 経路 |

### Medium

| ID | Risk | Why | Blast radius |
|---|---|---|---|
| M-a | Conversation / Challenge | Bundle フィールド前提 | Product UX |
| M-b | Single CLI / Eval | predict_ranking 依存 | Platform tooling |
| M-c | Dual-truth 期間 | Canonical vs View のドキュメント混乱 | Ops / Research |
| M-d | prediction_corpus 保存形 | 歴史 Bundle と新 CE 混在 | Research DB |
| M-e | PI vs win5-ai 公開差 | 二系統 API | Integration |

### Low

| ID | Risk | Why |
|---|---|---|
| L1 | Research CE 利用者 | 既に evaluate_candidates / CorePipeline |
| L2 | Win5 Optimizer | CE 非依存 |
| L3 | PE Feature/Scorer/Ranker | Bundle 非関与 |
| L4 | WorldAssigner 内部 | 既に CE stage |

### Risk × Consumer（要約）

| Consumer | Dominant risk |
|---|---|
| GUI / Functions / HTTP | High |
| Mapper / Adapter | High |
| Conversation / Challenge / Explain | Medium |
| Single / CLI / Eval / Analytics | Medium |
| Research (CE) | Low |
| Win5 / PE internals | Low |

---

## ⑥ Rollback Points

実装を進める場合の **境界**（本フェーズでは未実施）。

```
R0 ── ADR Accepted only（現行）
 │     Rollback: 不要（コード差分なし）
 │
R1 ── Dual-publish / Shadow CE（additive）
 │     Rollback: flag OFF; Bundle-only に戻す
 │     Safe default
 │
R2 ── CE→View Adapter（Mapper 置換）
 │     Rollback: 旧 Mapper + predict_ranking 経路を再有効化
 │     Keep Bundle schema_version 2.0
 │
R3 ── Client Guard / Ready 判定更新
 │     Rollback: 旧 validatePredictionBundle / isReady*
 │     Must be paired with R2 rollback
 │
R4 ── Hard: Bundle 非 Canonical 明示 or endpoint 分離完了
 │     Rollback: 文書 + flag; コードは R2 境界まで戻す
 │
R5 ── Hard cutover: Bundle 廃止 / 生 CE only（非推奨・別 ADR）
       Rollback: 困難 — 事前に R1–R4 必須
```

### Rollback 原則

1. **Product View（Bundle）を最後まで残す** — R5 以外は Bundle 存続  
2. **Flag / Dual** で R1 を必ず挟む  
3. **PE/CE/World 内部ロジックは触らない** — 公開境界と View のみ  
4. **Production Required** は R1 検証 PASS 後のみ（別 Decision）

### 実装時に触ってはいけない Rollback 外領域

| Locked | Reason |
|---|---|
| Feature / Scorer / Ranker | PE 責任外の契約問題 |
| WorldAssigner thresholds | Trigger/World 別トラック |
| demo_ticket_optimizer_core | Win5 非依存 |
| Production DB 破壊的 migration | R5 相当 |

---

## Migration sequencing（設計メモ・未承認）

| Step | Action | Risk after step |
|---|---|---|
| S0 | Impact docs（本 V51） | — |
| S1 | Shadow: CE を meta/debug のみ | Low |
| S2 | View Adapter design（world 投影） | Medium |
| S3 | Client Guard 拡張（View vs Canonical 明示） | Medium |
| S4 | Soft: Real path = CE→View | Medium→High if unflagged |
| S5 | Deprecate predict_* as Product entry | High |
| S6 | Optional: public CE endpoint | Medium |

S1 以降は **別 Decision Gate**。V51 は S0 のみ。

---

*V51 Migration Impact — research only. No code changes.*
