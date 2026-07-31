# UI9 — Reason Audit

**Date:** 2026-07-30  
**Verdict: FAIL**

固定テンプレート（馬番・馬名スロット差し替え）であることが証明された。  
レースごとの「AI判定内容に応じた文章変化」は、ユーザーが読む summary / narrative では確認できない。

---

## 1. PredictionBundle 由来か？ 固定テンプレートか？

**両方。ただし本質は固定テンプレート。**

| 層 | 役割 |
|---|---|
| PredictionBundle.explain | 文言は Bundle に載って UI へ届く |
| 生成ロジック | BFF `explainBuilder.js` の **固定句 + スロット** |

ユーザーが見た文:

> N番{馬名}を◎にしたのは、AI予測では1番手で、2番手との差も相対的に大きいため。 上位争いになりやすく、好位・先行が活きやすい展開です。

これは LLM 自由文ではなく、`buildHonmeiReason` の式:

```text
`${namePart}を◎にしたのは、${rankHint}ため。 ${tendency}`
```

- `namePart` = 馬番+馬名（レース依存スロット）
- `rankHint` = decision_key が `ce_rank1_gap_lead` なら固定句A、否则固定句B（2択）
- `tendency` = `world|sub_world` → `RACE_TENDENCY` 辞書の固定句

---

## 2. 生成ファイル（追跡）

| 段階 | ファイル | 証拠 |
|---|---|---|
| Core | `services/win5-ai/.../core/explain/__init__.py` `build_explain_payload` | world / decision_key / gap 等の **構造化**（日本語長文 summary はここではない） |
| PI | `services/pi-keibanet-api/.../service.py` | `explain_payload` を prediction に載せる |
| BFF Mapper | `functions/_lib/piPredictionMapper.js` | `buildExplainV21(...)` 呼び出し |
| **文言組立（正）** | **`functions/_lib/explainBuilder.js`** | `RACE_TENDENCY` / `buildHonmeiReason` / `legacyCompat` → `narrative` |
| UI | `public/assets/api/prediction-bind.js` | `.pace-card p` ← `explain.narrative`；`#reasonsSectionBody` ← `reason.summary`（v2） |
| UI 骨格 | `public/race.html` | 「最終着順予想」「◎を選んだ理由」見出し |

`prediction-bind.js` は **生成せず表示のみ**。文章の正は **BFF explainBuilder**。

---

## 3. 3レース比較 → FAIL

Artifacts: `docs/research/artifacts/ui9/compare.json`

| | Race A | Race B | Race C |
|---|---|---|---|
| race_id | 2026-07-26-01-01 | 2026-07-26-01-07 | 2026-07-26-01-11 |
| ◎ | 1番ドルチェテソーロ | 7番エントリバリーズ | 15番レブルアン |
| world | midupper_world | midupper_world | midupper_world |
| decision_key | ce_rank1_gap_lead | ce_rank1_gap_lead | ce_rank1_gap_lead |

馬名除去後の骨格は **6レースすべて同一**（unique_skeletons = 1）:

```text
N番HORSEを◎にしたのは、AI予測では1番手で、2番手との差も相対的に大きいため。 上位争いになりやすく、好位・先行が活きやすい展開です。
```

→ **馬名だけ差し替え = FAIL 基準に該当。**

※ factors 内の「推定勝率 11.5%」等はレースで変わるが、画面の主文（narrative / summary）には出ていない。

---

## 4. 「最終着順予想」と「◎を選んだ理由」

| セクション | DOM | 代入元 | 別ロジック？ |
|---|---|---|---|
| 最終着順予想 | `.pace-card p` | `bundle.explain.narrative` | **否** |
| ◎を選んだ理由 | `#reasonsSectionBody` | `explain.reason.summary`（v2） | **否** |

実測: 全サンプルで `narrative === reason.summary`（`same_narrative_summary: true`）。

**正の生成元:** `buildHonmeiReason` → `reason.summary`  
`narrative` は `legacyCompat` が summary をコピー（長さ ≤80 時は全文）。

着順そのものは `#paceTrack` の馬番ドットのみ。見出し下の `<p>` は **理由文の使い回し**。

---

## 5. パイプライン要約

```text
Feature/CE ranks + world
  → Core explain_payload（構造化）
  → PI prediction.explain_payload
  → BFF explainBuilder.buildHonmeiReason（日本語テンプレ組立）★ここが文章の正
  → PredictionBundle.explain.{reason.summary, narrative}
  → UI が同一文字列を2箇所に表示
```

---

## 判定

| 基準 | 結果 |
|---|---|
| PASS: レースごとに文章が AI 判定に応じて変化 | **未達** |
| FAIL: 固定テンプレ / 馬名だけ差し替え | **該当 → FAIL** |

```
【Decision】
Action Type: Audit
Implementation Required: No（本フェーズは監査のみ）
Deployment Required: No
Production Required: No
Risk: Low（監査）
Expected Next Action: 停止（文章改善が必要なら別 Phase）
```
