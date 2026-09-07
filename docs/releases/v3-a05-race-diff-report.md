# Version 3 — A-05 Race Diff Report

**Date:** 2026-07-24  
**Parent:** [`v3-a05-accuracy-report.md`](./v3-a05-accuracy-report.md)  
**Source:** `research/v3_lab/baselines/a05_accuracy/a05_race_diff.json`

---

## 1. Lab（Control → A-05）

| | n |
|--|---|
| Improved | **0** |
| Worsened | **0** |

A-05 は Lab Accuracy 上で pick を変更しない（Control Hit 218 のまま）。

参考: Control → A-03 は Pool×9 を改善（従来どおり）。

---

## 2. Offline（Control → A-05）

### 2.1 Summary

| | n |
|--|---|
| Improved | **7** |
| Worsened | **0** |
| worsened_winner_rank1 | **0** |
| churn_hit | **0** |
| pick_churn | 46（Hit 非悪化の pick 変更を含む） |

### 2.2 Improved races（7）

| race_id | winner_rank | control_pick | treatment_pick |
|---------|-------------|--------------|----------------|
| 2024-02-11-東京-10 | 8 | 2020106756 | 2015104714 |
| 2024-04-21-東京-10 | 7 | 2020100145 | 2019104116 |
| 2024-04-28-東京-10 | 7 | 2016105206 | 2018106571 |
| 2024-06-02-京都-10 | 10 | 2019105239 | 2019103430 |
| 2024-06-30-小倉-10 | 11 | 2020106635 | 2019104729 |
| 2026-02-15-京都-11 | 7 | 2018105012 | 2021100913 |
| 2026-03-22-中京-11 | 11 | 2021104434 | 2022103875 |

すべて deep 帯（winner_rank 7–11）の回復。本命破壊なし。

### 2.3 Worsened races

なし。

---

## 3. Offline 参考: Control → A-03

| | n |
|--|---|
| Improved | 11 |
| Worsened | 28（うち winner_rank=1 が 28） |
| ΔHit | −17 |

A-05 は A-03 の深掘り改善の一部（7/11）を残しつつ、悪化 28 を全遮断。

---

## 4. Stop

Race Diff は Accuracy Round の添付。Validation には着手しない。
