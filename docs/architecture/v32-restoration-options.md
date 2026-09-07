# Version32 — Restoration Options Comparison

**Date:** 2026-07-27  
**ADR:** `v32-world-adr.md`  
**Note:** 設計比較のみ。実装・推奨の最終結論は `v32-recommendation.md`。

V31 の「経路地図 P1–P5」とは ID 対応が異なる。**本表の P1–P5 は V32 ADR 定義を正とする。**

---

## Option definitions

| ID | Definition |
|----|------------|
| **P1** | **116列契約へ完全復元** — daily writer を legacy `pace_model` + market merge 経路に戻し、設計 116 搬送を Production 正本に戻す |
| **P2** | **72列へ pace Signal を正式移植** — PI `build_features` / daily を維持しつつ、設計必須 pace/World Signals（および Ranker 必要列）を **正式契約として生成**する（列数は 72 固定である必要はないが、PI writer を正本に保つ） |
| **P3** | **116 = Research 専用 / 72 = Production 専用** — 二重正本 |
| **P4** | **Signal Service 分離** — 特徴 CSV 幅と独立に **World Input Contract**（必要信号の生成・検証境界）を共通化し、Production/Research が同一入力契約を共有する |
| **P5** | **その他** — 例: FG 内再計算のみ、Loader の global 優先、手パッチ CSV、閾値変更で分布だけ合わせる、等 |

---

## Comparison matrix

### P1 — Full 116 restore

| Criterion | Assessment |
|-----------|------------|
| 設計適合性 | **高** — Original Architecture に最も忠実 |
| 保守性 | **低〜中** — legacy 二系統（pace_model + PI refresh）の再統合・運用負荷 |
| 影響範囲 | **広** — daily CSV 全体、Ranker 入力、CE meta、World 分布、Ops Shadow/compare |
| 回帰リスク | **高** — 列セット急拡大 + 可変 difficulty で PE/World 同時変化 |
| 将来拡張性 | **中** — モノリシック 116 に信号追加が紐づきやすい |

### P2 — Formal pace Signals on PI daily path

| Criterion | Assessment |
|-----------|------------|
| 設計適合性 | **高（信号面）** — 搬送幅より信号回復を優先；Original の「本質」に整合 |
| 保守性 | **中〜高** — 単一 daily writer（PI）を維持できる |
| 影響範囲 | **中〜広** — `build_features`（または同等）と daily schema、PE/World |
| 回帰リスク | **高**（信号が本物なら）／ **危険（部分移植）** — 不完全移植は偽設計値（V30 R3） |
| 将来拡張性 | **中〜高** — ただし「72列」に固執すると契約が再び列数に縛られる |

### P3 — Research 116 / Production 72

| Criterion | Assessment |
|-----------|------------|
| 設計適合性 | **低** — World 最上流が環境ごとに別真理になる |
| 保守性 | **低** — 二重パイプライン・二重デバッグ |
| 影響範囲 | Research と Production で非対称 |
| 回帰リスク | Production はそのまま；Research 改善が Production に翻訳不能 |
| 将来拡張性 | **低** — 統治不能な分岐が固定化する |

### P4 — Signal Service / shared World Input Contract

| Criterion | Assessment |
|-----------|------------|
| 設計適合性 | **最高（役割定義）** — 「World=最上流の勝ち筋分類」を **契約境界**として固定 |
| 保守性 | **高（長期）** / **中（導入時）** — 境界新設コストあり |
| 影響範囲 | 設計上は World 入力面に集中；実装時は生成器配置次第 |
| 回帰リスク | 契約を満たす実装なら予測可能；契約なしの中途半端は高リスク |
| 将来拡張性 | **最高** — chaos 等を同一契約へ追加可能；CSV 幅変更から World を隔離 |

### P5 — Other（代表パターン）

| Variant | 設計適合性 | 備考 |
|---------|------------|------|
| FG のみで `add_win5_*` | 中以下 | V30: 設計主契約（pace→CSV）とズレ；入力欠列で部分式リスク |
| Loader global 優先 | 低〜中 | カバレッジ／鮮度；断絶点の修復ではない |
| 手パッチ CSV | 低 | 再現性なし |
| Trigger 閾値だけ変更 | **不適合** | 信号欠落を隠す；最上流分類の思想に反する |
| Research-only instrumentation | 観測には有用 | Production World 契約の代替にはならない |

---

## Fit to philosophy (preview)

哲学: **World は AI 最上流の勝ち筋分類**

| Option | Fits? | Why |
|--------|:-----:|-----|
| P1 | Yes | 上流信号を歴史的経路で回復 |
| P2 | Yes if complete | 上流信号を現行 writer に正式化 |
| P3 | **No** | 最上流が二枚舌 |
| P4 | **Best role-fit** | 最上流を信号契約として定義 |
| P5 (threshold-only) | **No** | 分類器入力を偽のまま運用 |

---

## Relationship diagram

```text
                    ┌─ P1: restore legacy 116 vehicle
World Input Needs ──┼─ P2: emit required signals on PI vehicle
                    ├─ P4: define contract first; bind via P1 or P2 later
                    ├─ P3: split vehicles by environment  ← rejected by philosophy
                    └─ P5: bypass / partial / threshold   ← mostly non-solutions
```

P4 と P1/P2 は排他ではない: **P4 = 契約の正本化**、P1/P2 = **その契約を満たす供給手段**。

---

## Guardrails

- オプション比較のみ。採用実装なし。
