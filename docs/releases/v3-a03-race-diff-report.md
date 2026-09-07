# Version 3 — A-03 Race Diff Report

**Date:** 2026-07-24  
**Corpus:** `a03-285-*`（285R）  
**Artifact:** `research/v3_lab/baselines/a03_validation/a03_race_diff.json`

---

## 1. A-03 単独（Baseline → A-03）

| 区分 | 件数 |
|------|------|
| Improved | **9** |
| Worsened / churn | **0** |
| Unchanged hit | 218 |
| Unchanged miss | 58 |

### 層別改善

| miss_layer | n |
|------------|---|
| **Pool** | **9** |

Eval / Boundary / Reorder / Delete の改善・悪化はなし。

---

## 2. A-01 + A-03（A-01 → A-01+A-03）

| 区分 | 件数 |
|------|------|
| Improved | **9** |
| Worsened / churn | **0** |
| Unchanged hit | 246 |
| Unchanged miss | 30 |

### 層別改善

| miss_layer | n |
|------------|---|
| **Pool** | **9** |

A-01 が既に回収した Eval 28 は維持（churn 0）。追加改善は Pool のみ。

---

## 3. Pool 改善 9 件（両パネル共通）

| race_id | winner_rank | 備考 |
|---------|-------------|------|
| a03-285-271 | 8 | Coverage promote |
| a03-285-272 | 9 | |
| a03-285-273 | 10 | |
| a03-285-274 | 8 | |
| a03-285-275 | 9 | |
| a03-285-276 | 10 | |
| a03-285-277 | 8 | |
| a03-285-278 | 9 | |
| a03-285-279 | 10 | |

**再現確認:** Validation 2 ラウンドおよび両パネルで件数・層とも一致。

---

## 4. 悪化レース

両パネルとも **なし**。
