# Version10.6 Research — Resolver Governance

**Date:** 2026-07-27T06:58:47+00:00  
**Purpose:** Shadow Resolver の Production 採用可否を自動判定  
**重要:** Prediction順位変更禁止 / ResolverはShadowのみ / Production反映禁止  

## 0. Current Status

- Current Status: `sample_insufficient`
- Eligible: `False`
- Confidence Median: `1.0`

| 指標 | 値 |
|------|----|
| Tie races | 9 |
| Resolver Win / Lose / Draw | 2 / 0 / 7 |
| Strict Improvement | 2 (22.2%) |
| ROI Change | 22.2% |
| Coverage Avg | 100.0% |
| Confidence Median | 100.0% |

## 1. Gate 判定

| Gate | Threshold | Actual | Pass |
|------|-----------|--------|------|
| Tie races | >= 100 | 9 | False |
| Resolver Win Rate | >= 60.0% | 22.2% | False |
| Resolver Lose Rate | <= 5.0% | 0.0% | True |
| Strict Improvement | >= 5.0% | 22.2% | True |
| ROI Change | >= 0.0% | 22.2% | True |
| Coverage | >= 95.0% | 100.0% | True |
| Confidence Median | >= 70.0% | 100.0% | True |

## 2. Segment Snapshot

| Segment | Tie | Status | Win | Lose | StrictΔ | Confidence p50 |
|---------|----:|--------|----:|-----:|--------:|---------------:|
| `age_group:unknown` | 9 | sample_insufficient | 2 | 0 | 2 | 1.0 |
| `all_tie` | 9 | sample_insufficient | 2 | 0 | 2 | 1.0 |
| `class:unknown` | 9 | sample_insufficient | 2 | 0 | 2 | 1.0 |
| `distance:unknown` | 9 | sample_insufficient | 2 | 0 | 2 | 1.0 |
| `surface:unknown` | 9 | sample_insufficient | 2 | 0 | 2 | 1.0 |
| `venue:中京` | 4 | sample_insufficient | 0 | 0 | 0 | 0.775 |
| `venue:新潟` | 3 | sample_insufficient | 1 | 0 | 1 | 1.0 |
| `venue:札幌` | 2 | sample_insufficient | 1 | 0 | 1 | 1.0 |
