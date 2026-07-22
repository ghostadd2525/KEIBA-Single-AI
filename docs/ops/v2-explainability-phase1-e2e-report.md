# Version 2 Explainability Phase 1 — E2E 確認レポート（RC）

**Date:** 2026-07-22  
**Race:** `2026-07-25-01-06`（新潟 6R / 豊栄特別 — `fixtures/pi-prediction/niigata-6r.json` + 設計 §1.3 相当 CE meta）  
**Verdict:** **PASS → Release Candidate（RC）**

機械可読結果: [`v2-explainability-phase1-e2e-report.json`](./v2-explainability-phase1-e2e-report.json)  
再現コマンド:

```bash
python -m unittest discover -s services/win5-ai/platform/core-overlay/tests -p test_explain_payload.py -v
node --test tests/contract/explain-v2.test.mjs tests/contract/explain-v2-e2e.test.mjs
```

---

## 1. Feature Flag 組み合わせ

| Core `WIN5_EXPLAIN_V2_ENABLED` | PI `EXPLAIN_V2_ENABLED` | BFF `EXPLAIN_V2_ENABLED` | Web `v2_explain` | 期待 | 結果 |
|---|---|---|---|---|---|
| OFF | OFF | OFF | OFF | v1.1 空 explain / 「理由データなし」 | PASS |
| ON | OFF | ON | ON | PI 非透過 → 空 | PASS |
| ON | ON | OFF | ON | BFF 非組立 → 空 | PASS |
| ON | ON | ON | OFF | explain 2.1 生成・UI は legacy `reasons[]` | PASS |
| ON | ON | ON | ON | v2 UI（decision_key / summary / confidence / trace） | PASS |

**原則確認:** 全 Flag OFF ≡ v1.1（explain 空）。いずれかの上流 Flag OFF で payload が UI まで到達しない。

---

## 2. 実レース表示フィールド

対象: 新潟 6R（本命 4 番 コルドンブルー）

| フィールド | 確認 |
|------------|------|
| `reason.summary` | 非空・馬名/番号を含む |
| `reason.decision_key` | key / label 非空（CE 由来） |
| `confidence_reason` | summary + components（contribution / weight） |
| `decision_trace.stages` | stage / status / delta.summary 完備 |
| Web HTML | `.explain-v2` / decision-key / summary / confidence / trace。`理由データなし` なし |

---

## 3. legacy 後方互換

| 観点 | 結果 |
|------|------|
| BFF が `reasons[]` / `narrative` を自動生成 | PASS |
| Web `v2_explain` OFF → 既存 `reason-list` 描画 | PASS |
| explain 2.1 を無視し reasons/narrative のみでも描画 | PASS |
| `race.html` の mascot 用 `explain.narrative` 経路 | 互換維持（narrative 供給） |

---

## 4. explain_payload 欠損耐性

| ケース | 結果 |
|--------|------|
| BFF ON + payload 無し | 空 explain → 「理由データなし」（例外なし） |
| `decision_key` 欠落の部分 explain | summary 表示・`undefined` 文字列なし |
| Web Flag ON/OFF 双方 | UI 崩れなし |

---

## 5. RC 判定

- 契約テスト（`explain-v2`）: PASS  
- E2E（`explain-v2-e2e`）: PASS  
- Core 単体（`test_explain_payload`）: PASS  

**Version 2 Explainability Phase 1 をリリース候補（RC）として完了扱いとする。**

**本番有効化:** 各レイヤ Flag を段階的に ON（Core → PI → BFF → Web）。既定は引き続き OFF。  
**Phase 2（Pool / Entry / RePick Explain）:** 本確認完了後に着手（本レポートでは未着手）。
