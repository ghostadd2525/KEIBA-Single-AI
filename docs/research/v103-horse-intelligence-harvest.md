# Version10.3 Research — Horse Intelligence Harvest

**Date:** 2026-07-27 (JST)  
**Type:** Research Collector 拡張（Prediction 非改変）  
**Hard Lock:** PE / CE / AI Score / Prediction Logic / ResultAutomation / Challenge / Research Runtime **変更禁止**

---

## 0. Verdict

| 項目 | 結果 |
|------|------|
| Horse Collector | **実装・本番 Harvest 済** |
| Workout Collector | **実装・本番 Harvest 済** |
| Anti-Leak | `observed_at <= prediction_created_at` 強制 |
| Prediction Bundle | **未変更** |
| Tie Resolver | **未実装**（意図どおり） |

### Coverage（complete snapshots, runner×feature cells）

| Feature | Before | After | 判定 |
|---------|-------:|------:|------|
| popularity / win_odds / expected_popularity / trainer | 100% | **100%** | 維持 |
| **sire** | 0% | **100% (619/619)** | **PASS ≥95%** |
| **damsire** | 0% | **100% (619/619)** | **PASS ≥95%** |
| **breeder** | 0% | **100% (619/619)** | **PASS ≥95%** |
| **owner** | 0% | **100% (619/619)** | **PASS ≥95%** |
| sale_price | 0% | **32.0% (198/619)** | PARTIAL（`-` は正規欠損） |
| **oikiri_time** | 0% | **17.1% (106/619)** | **SOURCE_LIMITED** |
| **oikiri_rating** | 0% | **17.1% (106/619)** | **SOURCE_LIMITED** |

静的 Horse Intelligence（sire / damsire / breeder / owner）は **0% → 100%**。  
調教は公開済み出走馬のみ取得可能で、本コーパスでは **約17%**（ソース未掲載が主因。パーサ失敗ではない）。

---

## 1. 実装概要

### Phase1 — Horse Collector

| 項目 | 内容 |
|------|------|
| Profile | `GET https://db.netkeiba.com/horse/{horse_id}` → breeder / owner / sale_price |
| Pedigree | `GET .../ajax_horse_pedigree.html?id={horse_id}` → sire / damsire（`blood_table`） |
| ID 対応 | PI board `entries[].horse_id` / `horse_url` を snapshot runners に通過 |
| Anti-Leak | 静的属性は `RESEARCH_HARVEST_ASOF=1` で `prediction_created_at` 帰属 |

### Phase2 — Workout Collector

| 項目 | 内容 |
|------|------|
| URL | `oikiri.html?race_id={numeric_race_id}&type=1` |
| race_id | board `numeric_race_id`（Win5 ID の自前変換なし） |
| 抽出 | 出走馬 `horse_id` 限定で調教日・タイム・評価字母 |
| Anti-Leak | 調教日 ≤ 予測日のみ採用（必要時 asof clamp） |

### 変更ファイル（Research sidecar のみ）

- `app/research/collector/netkeiba_client.py`（新規）
- `app/research/collector/horse_collector.py`（新規）
- `app/research/collector/workout_collector.py`（新規）
- `app/research/collector/phase1.py` / `runner.py` / `assembler.py`
- `app/research/config.py` / `repository.py` / `analyzer.py`
- CLI: `--reharvest-v103`

---

## 2. Harvest 実行

```bash
# EC2
sudo systemctl stop expect-research-evidence-collector
cd /home/ubuntu/KEIBA-Single-AI/services/win5-ai
PYTHONPATH=. RESEARCH_HARVEST_ASOF=1 \
  python3 -m app.research.collector_runner --reharvest-v103
sudo systemctl start expect-research-evidence-collector
PYTHONPATH=. python3 -m app.research.analyzer_runner  # → v103 docs
```

| 指標 | 値 |
|------|-----|
| Reharvest targets | 50 |
| Snapshots complete | **50** |
| Snapshots failed（レガシー） | 7 |
| Analyzer eval races（∩ results） | **50** |

---

## 3. Analyzer 再実行（V10.2 ロジック）

出力:

- `docs/research/v103-feature-ranking.csv`
- `docs/research/v103-evidence-analysis.md`（自動生成）
- 本ドキュメント / `docs/audit/v103-harvest-validation.md`

市場3特徴は引き続き PROMISING（Soft→Strict +20%）。  
血統・厩舎系は Coverage 100% だがカテゴリカル prior 無しのため Resolver 指標は N/A。  
oikiri は Coverage 不足で Tie eligible ほぼ無し。

---

## 4. 【Decision】

```
Action Type: Research Harvest Extension
Implementation Required: Done (Collector only)
Deployment Required: Done on EC2 (reharvest)
Configuration Required: RESEARCH_HARVEST_ASOF=1 (既存)
Production Required: No Prediction change
Rollback Required: No
Risk: Low（Research sidecar / Anti-Leak 強制）
Expected Next Action:
  - V10.3 完了条件: 静的 Horse Features ≥95% → PASS
  - oikiri はソース公開率の制約を監査に明記（95%未達）
  - 次は Version10.3+ Tie Resolver（別チケット）または oikiri 公開タイミング最適化
```
