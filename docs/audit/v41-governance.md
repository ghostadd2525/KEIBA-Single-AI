# Version41 Governance — World Decision Trace

## Verdict: **C** — Decision Engine構造が主因

## Evidence（件数ベース）

| 項目 | 値 |
|---|---|
| n | 56 |
| core_share | 75.0% (42/56) |
| fitness_agree | 14.3% (8/56) |
| core via `R8_core_default` | **42/42** |
| core で R1–R7 全FAIL | **42/42** |
| core で soft best-fit ≠ decision | **42/42** |

### Primary（binding fail / 選択理由）

| 分類 | 全Race | coreのみ |
|---|---:|---:|
| Signal不足 | 0 | 0 |
| Trigger不足 | 39 | 39 |
| Boundary | 9 | 3 |
| Evaluation Order | 6 | 0 |
| Default/Fallback | 0 | 0 |
| その他 | 2 | 0 |

### Secondary（core 42件に付随する構造タグ）

| タグ | core件数 |
|---|---:|
| Default/Fallback | **42/42** |
| Evaluation Order | **42/42** |
| Signal不足（非binding / phase欠落等） | 40/42 |

### Fitness mismatch 内訳

| best-fit → decision | 件数 |
|---|---:|
| midhole → core | 22 |
| midupper → core | 18 |
| midupper → mixed | 5 |
| その他 | 3 |
| **DEFAULT→core vs best-fit Trigger未達** | **42** |
| first-match優先度で best-fit 敗退 | 6 |

## Interpretation

1. `core_world` は正の Trigger を持たず、`R8_core_default` のみである。
2. Trace 上、core 42件はすべて「R1–R7 FAIL → R8 DEFAULT」で確定している。
3. soft fitness は同一42件で midhole/midupper 等を最適としているが、それらの Trigger は閾値未達（主に `late_stop` / `difficulty` / `short_field_pressure`）で FAIL する。
4. したがって「Fitness最適 ≠ 実際World」は推測ではなく、**first-match + DEFAULT** の直接帰結である。
5. `phase` 欠落は40件で観測されるが、mixed 系ルール付随であり、core偏重の binding 理由（best-fit の Trigger FAIL）ではない（Signal不足 primary = 0）。

**結論:** binding 失敗の多くは Trigger不足だが、それがすべて `core_world` になる機構は Decision Engine 構造（first-match + core=DEFAULT）である。よって主因は **C**。

## Labels

- A: Signalが主因
- B: Boundaryが主因
- C: Decision Engine構造が主因
- D: 複数要因

## Artifacts

- `docs/audit/v41-decision-trace.md`
- `docs/audit/v41-trigger-trace.md`
- `docs/audit/v41-fitness-mismatch.md`
- `docs/audit/v41-root-cause-classification.md`
- `docs/audit/v41-governance.md`
- `evidence/research/reports/v41-world-decision-trace.json`

## Constraints honored

- Prediction / PE / CE / AI / World / Trigger / Signal / SubWorld / Role / Required / Candidate Pool / Production: **未変更**
- 改善・閾値変更・Simulation政策変更: **なし**
- 根拠: 実コード `TRIGGER_RULES` / `first_match_world` / `trigger_proximity_fitness` + V39同一 Signal 復元パック
