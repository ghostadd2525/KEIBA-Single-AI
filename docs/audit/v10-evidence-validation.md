# Version10 Audit — Evidence Platform Validation

**Date:** 2026-07-27  
**Type:** Implementation validation（Phase1 P0）  
**Hard Lock:** PE / CE / AI / RA / Challenge / Research Runtime — **未変更確認**

---

## 0. Verdict

| 項目 | 結果 |
|------|------|
| Research パッケージ実装 | **PASS** |
| Phase1 Evidence（A/B） | **PASS**（コード + 単体テスト） |
| Anti-Leak | **PASS**（単体テスト） |
| Product 変更禁止 | **PASS**（grep 確認） |
| 本番 EC2 実データ E2E | **未実施**（サイドカー未デプロイ） |

---

## 1. 単体テスト

```bash
cd services/win5-ai
python -m unittest tests.research.test_v10_evidence_platform -v
```

| テスト | 内容 | 結果 |
|--------|------|------|
| AntiLeakTests | 未来 observed_at 拒否 | PASS |
| Phase1CollectorTests | 人気/単勝/想定人気/厩舎 | PASS |
| AssemblerTests | partial 判定 | PASS |
| QualityTests | coverage 50% | PASS |
| PathTests | repo / evidence root | PASS |

---

## 2. 変更境界監査

| パス | 変更 |
|------|------|
| `app/challenge/` | **なし** |
| `app/ops/result_automation.py` | **なし** |
| `app/engine/` (PE/AI) | **なし** |
| `scripts/ops/v8/` (Research Runtime) | **なし** |
| `app/main.py` | Research API 2 ルート追加のみ |
| `pi_keibanet/service.py` | `trainer` フィールド露出のみ |

Prediction 永続化経路（Conversation / RA / Challenge）は **コード未変更**。  
Trigger は **ポーリング**（`list_predictions_without_snapshot`）で観測。

---

## 3. Phase1 機能検証（オフライン）

### 3.1 Mock board

入力:

```json
{
  "odds_updated_at": "2026-07-26T09:00:00+09:00",
  "entries": [
    {"horse_number": 1, "odds": 2.5, "popularity": 1, "trainer": "A厩舎"},
    {"horse_number": 2, "odds": 5.0, "popularity": 2, "trainer": "B厩舎"}
  ]
}
```

`prediction_created_at = 2026-07-26T10:00:00+09:00`

| フィールド | 馬1 | 馬2 |
|------------|-----|-----|
| win_odds | 2.5 | 5.0 |
| popularity | 1 | 2 |
| expected_popularity | 1 | 2 |
| trainer | A厩舎 | B厩舎 |
| anti_leak_violations | 0 | |

### 3.2 Anti-Leak 拒否

`observed_at = 2026-07-26T11:00:00+09:00`（prediction より未来）  
→ 値は **null**、`missing_reason=anti_leak_rejected`

---

## 4. DB / Store スキーマ

Migration: `011_research_evidence.sql`

| テーブル | 用途 |
|----------|------|
| `research_collect_jobs` | 非同期ジョブ |
| `research_prediction_snapshots` | Snapshot index + payload |
| `research_source_events` | ソース別成功/失敗 |
| `research_evidence_daily` | 日次 KPI |

JSON: `evidence/research/prediction-snapshots/{date}/{race_id}/{prediction_id}.json`

---

## 5. 本番 E2E 手順（デプロイ後）

1. EC2: migration 適用（expect-ai 再起動 or `migrate()`）
2. PI `trainer` 露出デプロイ
3. systemd timer または cron で `collector_runner --loop`
4. 既存 prediction が存在する場合、1 サイクル後:

```bash
curl -s http://127.0.0.1:8000/v1/admin/research/evidence/monitoring | jq .
curl -s http://127.0.0.1:8000/v1/research/prediction-snapshots/{id} | jq .
```

5. 期待:
   - `snapshots_total` 増加
   - `anti_leak_violations_total == 0`
   - Partial は発売前/オッズ未発表で許容

---

## 6. 既知ギャップ（Phase2 以降）

| 項目 | 状態 |
|------|------|
| 血統 / 牧場 / Tier3 | 未実装（設計のみ） |
| Evidence Catalog ファイル | DB daily のみ（catalog JSON は将来） |
| systemd unit | 手順書のみ（別デプロイ） |
| BFF `/api/ops/evidence-collector` → EC2 プロキシ | Pages Functions 実装済、Tunnel 要確認 |

---

## 7. 成果物チェック

| 成果物 | パス |
|--------|------|
| 設計 | `docs/design/v10-evidence-collection-platform.md` |
| Ops | `docs/ops/v10-evidence-monitoring.md` |
| 監査 | 本ファイル |

---

## 8. 参照

- `tests/research/test_v10_evidence_platform.py`
- `app/research/collector_runner.py`
