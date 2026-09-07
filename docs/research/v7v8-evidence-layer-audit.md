# Evidence Layer Audit — Version7/8 vs ADR-009/010

**Date:** 2026-07-28  
**推測禁止:** 以下はすべて文書/コード引用に基づく。

---

## 1. Product Version8 Evidence（コード＋設計）

### 1.1 設計上の定義

`docs/ops/v8-self-improvement-cycle.md`:

- Production で許可: `ResultAutomation → Evidence → Archive`
- Research 入力正本: `evidence/improvement/` + `improvement_evidence_index`
- Miss Evidence: `miss_top1|3|5`（同文書 § および `v8.1-analyzer-root-cause.md`）

`docs/ops/v8-operations-baseline.md`:

```
ResultAutomation → race_results → race_evaluations → Miss Evidence → Archive
```

### 1.2 コード上の実体

| 要素 | 場所 | 役割 |
|---|---|---|
| 状態 | `app/ops/state_machine.py` `EVIDENCE_EXPORTING` | RA パイプライン段階 |
| 書込 | `app/ops/result_automation.py` | `evidence/improvement/{event_type}/...json` + DB index |
| 対象 | 同 `_events_from_existing_evals` | `hit_at_1=0` の評価行 → miss イベント |

### 1.3 蓄積されるもの / されないもの

| 蓄積（根拠あり） | 非蓄積（Product V8 に根拠なし） |
|---|---|
| Prediction Miss（hit 失敗） | World ラベル履歴を Evidence 成長の主キーとする設計 |
| fingerprint / path / race_id | Near Miss class / Affinity ベクトル |
| Analyzer 向け Miss JSON | Explanation Completeness / EC Bundle |
| 週次 Research への読取専用供給 | 「説明忠実度」の時系列学習 |

---

## 2. Research V76「World Evidence」

`docs/research/v76-world-evidence.md`:

- 目的: Ready に必要な **証拠の欠落列挙**
- 明示: 実装禁止 / PE・Trigger・Blueprint 変更禁止 / Hit 改善は非目的
- 内容例: 標本分割再現なし、ゲート定量未固定、MUST の観測合否テスト未整備

これは ADR-009 の Completeness 測定に **思想的に近い「測る」**が、  
**永続 Evidence Layer 実装や Affinity/Near Miss 成長**の設計ではない。

---

## 3. Version9.2 Evidence Platform（V8 の外）

`docs/design/v92-evidence-platform.md`（Status: Design only）:

- Prediction Snapshot 保存基盤の設計
- 「Miss Evidence は結果後中心」と明記し、本番 Miss と **併存・混ぜない**
- Hard Lock: PE/CE/RA 変更禁止

→ Product V8 の後続設計。ADR-009 の World/Near Miss Completeness Evidence とは **別物**（Prediction Snapshot）。

---

## 4. ADR-009/010 との対応判定

| ADR-009/010 が求めるもの | Product V7–V8 Evidence | 判定 |
|---|---|---|
| レース記述 Completeness の蓄積 | なし（Miss=Hit 失敗） | **未存在** |
| World / Near Miss / Affinity / Explanation の Evidence 成長 | なし | **未存在** |
| 観測で改善し PE を直接いじらない | V8 サイクルに **類似**（Research のみ改善案） | **部分的に先行** |
| Explanation Confidence | なし（Conversation の prediction confidence 禁止は ADR-003） | **未存在（ADR-010 で新規定義）** |

---

## 5. 結論（Evidence Layer）

1. **Product Version8 に Evidence Layer は存在する。**  
2. その対象は **Prediction Miss 改善**であり、ADR-009 の Core Completeness / ADR-010 の Explanation Confidence **ではない。**  
3. World/Near Miss/Affinity/Explanation をエビデンスで育てる設計は、Product V7–V8 の設計書・ADR・コードから **確認できない。**
