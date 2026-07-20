# Miss 傾向分析（構造ベースライン）

**Date:** 2026-07-20  
**Corpus:** `evidence/improvement/miss/**` = **0 件**（未同期）  
**方法:** Production 検出・分類ロジック + GameDay 既知パターンによる傾向仮説  
**制約:** Prediction Core は変更しない。Canary 通過後のみ Core 変更候補とする。

---

## 1. データ状況

| 項目 | 値 |
|------|-----|
| 実 Evidence 件数 | 0 |
| 分析モード | structural baseline |
| 再実行条件 | `npm run evidence:sync -- --date <開催日>` 後に本分析を更新 |

---

## 2. 分類軸（Production 正）

`classify_miss`（`miss_evidence.py`）:

| miss_category | 条件 | 解釈 |
|---------------|------|------|
| （出力なし） | hit_at_1 | Hit — Evidence なし |
| `miss_top1` | Top1 外・Top3 内 | 本命ズレ（近い） |
| `miss_top3` | Top3 外・Top5 内 | 中位ズレ |
| `miss_top5` | Top5 外 | 大幅ズレ |

傾向仮説（実データなしのため **優先調査順**）:

1. **miss_top1 が最多になりやすい** — GameDay happy_path は winner=model_rank2 → 常に miss_top1 を再現
2. **miss_top5 は feature/fallback 併発と相関しやすい** — mock_fallback + 弱い ranking の組み合わせ
3. **confidence 高 × miss_top1** — 過信クラスタとして Canary で監視すべき

---

## 3. 併発シグナル

Production は同一レースで `feature_missing` と `miss` を両方キューし得る。

| 併発 | 示唆 |
|------|------|
| miss のみ | ranking / 説明の問題寄り |
| miss + feature_missing | データ不足が先因の可能性 → Core より ETL/Feature を優先 |
| miss + prediction_failed | 予測欠落は別系統（本分析対象外を優先） |

**方針:** Core 改善案は「miss のみ」クラスタを優先。feature 併発は Feature Proposal 側。

---

## 4. 傾向クラスタ（仮説 ID）

| cluster_id | 仮説 | 検証に必要な Evidence フィールド |
|------------|------|----------------------------------|
| M-T1-NEAR | miss_top1 が支配的 | `payload.miss_category` |
| M-CONF-HIGH | confidence≥80 かつ miss | `payload.confidence` |
| M-ENGINE-FALLBACK | engine_source≠real_ai の miss | `payload.engine_source` |
| M-FEAT-CO | feature_source に missing | `payload.feature_source` + feature_missing 併発 |

---

## 5. 改善に進める条件

- [ ] 実 miss Evidence ≥ 1 開催日分を Index に載せる
- [ ] miss_category 分布を集計し M-T1-NEAR を確認
- [ ] feature 併発率を算出
- [ ] 併発率が高い場合は Core 案を後回し（Feature Proposal 優先）

現状は構造仮説に基づき **設計のみ** Proposal `IMP-20260720-miss-001` を作成する。
