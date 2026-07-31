# Version72 — Evaluation Protocol

**Date:** 2026-07-28  
**Parent:** `v72-ground-truth-definition.md`  
**Purpose:** 設計評価で Intent Accuracy 等を測るときの **測定規約**  
**実装禁止**（本フェーズはプロトコル定義のみ）

---

## 評価の目的

被評価ラベル（Legacy / Shadow / Blueprint 実装）が、**Contract Expected World（CEW = Intent GT V72）** とどれだけ一致するかを測る。

CEW は V43/V44 からの導出であり、被評価システムの出力ではない。

---

## プロトコル階層

```text
Layer A — Contract Expected World（GT）
          V72 Label Rule に従いレースごとに確定
Layer B — System Under Test（SUT）
          Legacy World / V69 Shadow World 等
Layer C — Metrics
          Acc / Confusion / Per-world Recall / Structural counts
Layer D — Outcome side-metrics（任意・非 GT）
          Hit / Winner Alignment — Gate の Intent 正本にしない
```

---

## Step 1 — CEW 付与

1. コーパス各レースについて、許可 Signal/Concept のみを収集。  
2. `v72-world-label-rule.md` に従い MATCH / Decision Tree を適用。  
3. 出力: `cew_world ∈ Labels`。  
4. 付与ログ必須項目: Must gaps / Exclude hits / \|M\| / 禁止入力非使用宣言。

**禁止:** CEW 付与に winner_rank / 人気 / Prediction score を参照すること。

---

## Step 2 — SUT ラベル取得

| SUT | ソース | 注意 |
|---|---|---|
| Legacy | `classify_world_line_type` | Production 決定。変更しない |
| V69 Shadow | V69 Logic Form 観測 | Decision authority は Legacy のまま |
| V44 Shadow | V44 Logic Form 観測 | 対照用 |

SUT が unsatisfied を出せない場合（Legacy）、その事実を Metrics で明示する（GT 側を歪めない）。

---

## Step 3 — 主メトリクス（設計評価）

| Metric | 定義 | 用途 |
|---|---|---|
| **Contract Intent Accuracy** | `(cew_world == sut_world) / N` | 主 Acc（V65 Acc を置換） |
| Confusion Matrix | rows=CEW, cols=SUT | 誤割当構造 |
| Per-world Recall | `TP_w / support_cew(w)` | 特に rank7 / core / midupper |
| Per-world Precision | `TP_w / support_sut(w)` | 過剰割当検出 |
| Positive Match Rate（SUT） | SUT ≠ unsatisfied かつ非 DEFAULT | 構造 |
| Unsatisfied Rate（CEW / SUT） | 各側の unsatisfied 割合 | V44 整合 |
| DEFAULT→core Count（SUT） | Legacy R8 等 | 契約 Forbidden の残存 |
| difficulty-only midupper（SUT） | R7 単原子等 | Forbidden 残存 |

### 廃止メトリクス（設計主評価から除外）

| 旧 | 理由 |
|---|---|
| V65 Intent Accuracy | GT が非契約（V71） |
| winner_rank 帯一致率を Intent Acc と呼ぶこと | Outcome-as-World |

---

## Step 4 — 副次メトリクス（任意）

Prediction / Hit / Purchase / miss buckets / Winner Alignment は **Production・PE 非干渉確認**や参考に使えるが、

- **Contract Intent Accuracy の定義に入れない**  
- Soft/Cutover の「Intent 改善」判定の **唯一根拠にしない**（CEW Acc を用いる）

Expected Characteristics 観察（V43 §⑥）も副次。

---

## Step 5 — Polarity 運用（評価時）

| 規則 | 内容 |
|---|---|
| 契約 | ↑/↓ は V44 polarity カタログ |
| 製品 Threshold | 変更・新設禁止 |
| 観測 polarity | コーパス内の相対方向（例: batch median）を **評価専用**に用いてよい |
| 記録 | 使用した polarity 方法を Evaluation Report に明示 |

Polarity 方法の変更は GT **定義**の変更ではないが、再現性のため固定して報告する。

---

## Step 6 — Gate への接続（設計）

将来の Shadow/Dual Gate で Intent を用いる場合の **推奨置換**:

| 旧 PASS 条件（V70） | 新（V72 Protocol） |
|---|---|
| V65 Intent Accuracy 改善 | **Contract Intent Accuracy** 改善（CEW vs SUT） |
| rank7 Recall（V65 GT） | rank7 Recall（**CEW** support） |
| core DEFAULT 減少 | 維持（構造 KPI） |
| Hit / Fingerprint | 維持（Production 非干渉） |

本フェーズでは Gate 再実行・実装は行わない。

---

## Step 7 — 報告テンプレ（最小）

```text
Corpus:
CEW distribution:
SUT distribution:
Contract Intent Accuracy:
Confusion (CEW × SUT):
DEFAULT→core (SUT):
Unsatisfied (CEW / SUT):
Polarity method:
Forbidden-input audit: PASS/FAIL
```

---

## 再現性チェックリスト

- [ ] CEW 規則が V44 Logic Form 写しである  
- [ ] winner_rank / 人気 / score が CEW に未使用  
- [ ] V65 ラベルを CEW にフォールバックしていない  
- [ ] SUT と CEW の混同がない  
- [ ] 実装・Trigger・Production を変更していない  
