# Version 3 — A-05 Validation Race Diff Report

**Date:** 2026-07-24  
**Parent:** [`v3-a05-validation-report.md`](./v3-a05-validation-report.md)  
**Source:** `research/v3_lab/baselines/a05_validation/a05_race_diff.json`

---

## 1. Offline（Control → A-05）· 再現

### Summary

| | n |
|--|---|
| Improved | **7** |
| Worsened | **0** |
| worsened_winner_rank1 | **0** |
| churn_hit | **0** |

### Improved races（Accuracy と同一）

| race_id | winner_rank | control_pick | treatment_pick |
|---------|-------------|--------------|----------------|
| 2024-02-11-東京-10 | 8 | 2020106756 | 2015104714 |
| 2024-04-21-東京-10 | 7 | 2020100145 | 2019104116 |
| 2024-04-28-東京-10 | 7 | 2016105206 | 2018106571 |
| 2024-06-02-京都-10 | 10 | 2019105239 | 2019103430 |
| 2024-06-30-小倉-10 | 11 | 2020106635 | 2019104729 |
| 2026-02-15-京都-11 | 7 | 2018105012 | 2021100913 |
| 2026-03-22-中京-11 | 11 | 2021104434 | 2022103875 |

### Worsened races

なし。

---

## 2. Lab（Control → A-05）

| | n |
|--|---|
| Improved | 0 |
| Worsened | 0 |

---

## 3. Stop

Validation Race Diff 添付のみ。Shadow / Production には着手しない。
