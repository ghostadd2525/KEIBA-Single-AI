# Version31 — Pace CSV Contract Audit

**Date:** 2026-07-27  
**Scope:** Audit only（CSV 修正 / FG / Loader / Trigger / World 変更禁止）  
**Question:** CSV 契約はどこで壊れたか

---

## Executive finding

**116→72 の「列削除コンバータ」は存在しない。**

契約断絶点は:

```text
[Legacy design path — 116 cols]
demo_runners_history_features
  → demo_pace_model_v2.build_pace_features   ← race_leg_difficulty 等を生成
  → demo_merge_market_into_pace              ← market 結合
  → demo_runners_pace_market_features.csv (≈116)
  → (旧) daily 配置

[Current Production daily writer — 72/74 cols]
pi_keibanet.race_refresh.write_daily_features
  → pi_keibanet.features.build_features
       = history 移植 + _add_risk_features (v2)
       ≠ pace_model_v2
  → demo_daily_outputs/{date}/demo_runners_pace_market_features.csv (72/74)
  → FeatureLoader が daily を優先
```

壊れた場所 = **daily CSV の生成器置換**（pace_model パイプライン → PI `build_features`）。  
Slim 化は「116 を読んで 46 列 drop」ではなく、**最初から pace 列を生成しない別パイプライン**である。

---

## Pipeline inventory

| Stage | Owner module | Output | pace / difficulty |
|-------|--------------|--------|-------------------|
| pace_model 出力 | `demo_pace_model_v2.build_pace_features` | `demo_runners_pace_features.csv` | **生成する** |
| CSV 生成（legacy market） | `demo_merge_market_into_pace` | `demo_runners_pace_market_features.csv` | **搬送する** |
| daily CSV 生成（現行） | `race_refresh.write_daily_features` → `build_features` | `demo_daily_outputs/.../demo_runners_pace_market_features.csv` | **生成しない** |
| CSV Slim 化 | （専用 Slim ステップなし） | — | N/A（非生成） |
| Loader | `FeatureLoader._load_daily_csv` then `_load_global_csv` | frame | daily 勝 → 欠列 frame |

---

## ① 116→72 変換箇所

| Candidate | Verdict |
|-----------|---------|
| Explicit column filter / Slim script | **Not found** |
| `build_features` drop list | Only drops `_runner_date_dt`（+ risk 内の一時 `is_*`） |
| `merge_daily_features` | race_id マージのみ。列スキーマは `build_features` 出力に従属 |
| **Generator replacement** | **Yes — 断絶点** |

観測:

- Local last 116 daily: `2026-06-28`
- Local/EC2 first slim daily: `2026-07-25`（72）
- EC2 bak `*.bak.20260724205804` も **72 列**（unblock 前から slim）
- EC2 Shadow `/tmp/pi-features-shadow/.../2026-07-25/...` も **72 列**
- EC2 global `data/demo_runners_pace_market_features.csv` はなお **116 列**（daily 優先のため通常不使用）

---

## ④ pace 列除外ポイント（要約）

| Column | Excluded where | Mechanism |
|--------|----------------|-----------|
| `race_leg_difficulty` | `build_features` 非生成 | pace_model 未呼出 |
| `pace_collapse_risk` | 同上 | 代わりに `pace_collapse_risk_v2` のみ |
| `style_entropy` | 同上 | 非生成 |
| `horse_count` | 同上 | 代わりに `field_size` |
| `leg_*` / `pre_world_*` | 同上 | pace_model / seed 未呼出 |

詳細: `v31-column-removal.md`

---

## ⑤ 正本判定（要約）

| Contract lens | Canonical | Proof |
|---------------|-----------|-------|
| World / Ranker **design**（凍結 28 + Trigger） | **116-col legacy pace→market** | `win5_lgbm_ranker_features.json` に `race_leg_difficulty` 等; V30 設計経路 |
| Production **daily writer ops**（V2 Race Refresh） | **72/74 PI `build_features`** | Addendum: shutuba→runners→`build_features`→daily CSV |
| FeatureLoader **runtime preference** | daily を優先 | `_load_daily_csv` before global |

→ **設計正本は 116。運用日次正本は 72/74。両者は矛盾している。**  
詳細: `v31-contract-owner.md`

---

## Cross-links

- `docs/audit/v31-column-removal.md`
- `docs/audit/v31-schema-diff.md`
- `docs/audit/v31-contract-owner.md`
- `docs/audit/v31-restoration-path.md`
- V30: `docs/audit/v30-*.md`

## Guardrails

- Audit のみ。CSV・Loader・FG・Trigger・World 未変更。
