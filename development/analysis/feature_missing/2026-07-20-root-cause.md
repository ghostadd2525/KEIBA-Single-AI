# feature_missing 原因分析

**Date:** 2026-07-20  
**Corpus:** `evidence/improvement/feature_missing/**` = **0 件**  
**方法:** Production 検出条件の逆引き + GameDay `feature_missing` シナリオ  
**制約:** Production 現状維持。Core 変更は Canary 通過後のみ。

---

## 1. Production 検出条件（正本）

`result_automation.py` PREDICTION_MATCHING 内:

```
feature_signals =
  fallback_reason ∈ {
    market_feature_missing,
    feature_missing,
    platform_missing
  }
  OR feature_source に "missing" / "none"
```

原因は **予測結果メタの欠落シグナル**であり、ETL 生データの直接検査ではない。

---

## 2. 原因カテゴリ（仮説）

| 原因 ID | カテゴリ | 典型シグナル | 一次対応の置き場 |
|---------|----------|--------------|------------------|
| F-ETL-LATE | 開催日データ未着・遅延 | platform_missing, engine mock | ETL / データ供給 |
| F-MARKET | 市場系 Feature 欠落 | market_feature_missing | Feature パイプライン |
| F-META-NONE | feature_source 未設定/none | feature_source=missing\|none | Adapter メタ付与 |
| F-FALLBACK- cascade | fallback 後も評価継続 | engine_source=mock_fallback + miss 併発 | 公開品質ゲート（Core 外） |

GameDay では `feature_source=missing` + `mock_fallback` + `fallback_reason=feature_missing` で **確実に 1 イベント再現**できる。

---

## 3. 因果の切り分け

```
ETL 失敗/遅延
  → feature 不足
    → fallback / feature_source=missing
      → feature_missing Evidence
        →（任意）miss Evidence 併発
```

**Root cause を Core の ranking と誤認しないこと。**  
Feature 欠落下の miss は「データ問題」として扱う。

---

## 4. 推奨アクション優先度

1. **運用・供給:** 開催日 AM の ETL status / coverage を Monitor で担保（既存 OPS-Monitor）
2. **設計:** Feature 充足ゲートを Proposal 化（本分析 → `IMP-20260720-feature_missing-001`）
3. **Core:** Feature 充足後の miss のみを対象（Canary 後）

---

## 5. 実 Evidence 到着後の確認項目

- [ ] `fallback_reason` 分布
- [ ] `feature_source` 分布
- [ ] `engine_source` 分布
- [ ] 同 race_id の miss 併発率
- [ ] 開催日 × venue の偏り
