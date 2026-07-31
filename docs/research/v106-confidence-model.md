# Version10.6 Research — Confidence Model

Confidence は 0〜1 で算出し、以下を合成する。

- Evidence一致数: considered features のうち Shadow pick を支持した割合
- Tier一致: 支持 feature の Tier weight（S=1.0, A=0.8, B=0.6, C=0.4）
- Coverage: V10.4 feature coverage の平均
- Missing: 当該 tie race で complete に評価できた feature 比率

式:

```
confidence = 0.45*evidence_match_ratio + 0.20*tier_agreement + 0.20*coverage_score + 0.15*missing_score
```

| Metric | Value |
|--------|------:|
| p50 | 1.0 |
| p75 | 1.0 |
| min | 0.55 |
| max | 1.0 |
| avg | 0.875 |
