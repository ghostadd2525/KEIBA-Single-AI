# AI-Core Improvement — Canary 実験計画（2026-07-20）

**Phase:** AI-Core Improvement  
**Production:** 現状維持（変更なし）  
**Prediction Core:** **未変更**（Canary `pass` + Human Review 後のみ対象）

---

## 0. Evidence 前提

| 項目 | 状態 |
|------|------|
| `evidence/improvement/**` | **空**（0 events） |
| 分析モード | 構造ベースライン + GameDay 再現パターン |
| 次アクション | 開催日後に `evidence:sync` → Index 再生成 → Report 更新 |

空 corpus のため本 Canary は **実験計画の確定**まで。実行メトリクスは Evidence 同期後。

---

## 1. 実験 A — miss（IMP-20260720-miss-001）

### 仮説

近傍ミス（`miss_top1`）が支配的なら、Top1 較正設計で hit_at_1 を改善できる。

### 手順

1. Evidence 同期（推奨）または GameDay miss fixture でベースライン固定
2. `feature_missing` 併発レースを除外
3. 設計どおりの較正ルールを **オフライン比較**（Prod Core 非適用）
4. Criteria ゲートを埋めて Report を `pass`/`fail` 更新
5. **pass のときのみ** Core 実装 PR を許可 → RC → Review → Deploy

### 成果物

| 種類 | パス |
|------|------|
| Config | `canary/configs/IMP-20260720-miss-001.json` |
| Criteria | `canary/criteria/IMP-20260720-miss-001.json` |
| Report | `canary/reports/IMP-20260720-miss-001.json` → `pending` |

---

## 2. 実験 B — feature_missing（IMP-20260720-feature_missing-001）

### 仮説

欠落は供給・メタ問題が主因。Core 変更より ETL/Feature ゲート設計が先。

### 手順

1. 検出ルール（fallback_reason / feature_source）でベースライン集計
2. 供給完了定義・メタ正規化の設計をオフライン検証
3. Criteria 評価（Core 変更は rollback トリガ）
4. pass 後の実装対象は **データ供給・運用ゲート**（Core 非対象）

### 成果物

| 種類 | パス |
|------|------|
| Config / Criteria / Report | `IMP-20260720-feature_missing-001`（Report=`pending`） |

---

## 3. 実行順序（推奨）

```
1) Feature Canary（B）を先に計画・評価
2) Feature 併発が下がった開催日集合で Miss Canary（A）
3) A が pass → はじめて Prediction Core 変更を検討
```

---

## 4. 明示的にやらないこと

- Production コード変更
- Prediction Core の先行パッチ
- Canary pending/fail の RC 化
- OPS-Monitor / Result Automation の無効化

---

## 5. ゲート要約

| Proposal | Core 変更候補? | 現 status |
|----------|----------------|-----------|
| IMP-20260720-miss-001 | Yes（pass 後のみ） | canary **pending** |
| IMP-20260720-feature_missing-001 | **No**（供給・メタ） | canary **pending** |
