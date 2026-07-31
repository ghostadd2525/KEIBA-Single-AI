# Version40 — Boundary Quality & Trigger Diagnosis

**N:** `56`

## 5. Stability (signal +/-0.02 / +/-0.05)

- Mean flip rate: `7.6%`
- Unstable races (>=25% flips): `12` (`21.4%`)

| World | n | mean flip rate |
|-------|--:|---------------:|
| core_world | 42 | 2.4% |
| midupper_world | 3 | 16.7% |
| midhole_world | 1 | 50.0% |
| mixed_world | 10 | 22.5% |

## 6. Distribution quality

| Metric | Value |
|--------|------:|
| Entropy (bits) | 1.085 |
| Entropy ratio | 42.0% |
| IG vs collapse | 1.085 |
| Mean soft margin | -0.3479 |
| Mean silhouette | -0.4502 |
| Agree best-fit rate | 14.3% |
| Ambiguous rate | 28.6% |
| TV to design | 0.529 |

Shares: `{"core_world": 0.75, "midupper_world": 0.05357142857142857, "midhole_world": 0.017857142857142856, "rank7_world": 0.0, "bug_world": 0.0, "mixed_world": 0.17857142857142858}`

## 7. Trigger diagnosis (no threshold changes)

| World | Diagnosis | obs share | design | ratio | inbound NM | outbound NM | reason |
|-------|-----------|----------:|-------:|------:|-----------:|------------:|--------|
| core_world | **過剰** | 75.0% | 30.0% | 2.50 | 0 | 23 | default sink 75.0% (design 30.0%); agree_best_fit=0.0% |
| midupper_world | **不足** | 5.4% | 35.0% | 0.15 | 15 | 3 | share 5.4% vs design 35.0% |
| midhole_world | **不足** | 1.8% | 5.0% | 0.36 | 13 | 1 | share 1.8% vs design 5.0% |
| rank7_world | **不足** | 0.0% | 15.0% | 0.00 | 10 | 0 | never assigned but 10 inbound near-miss races |
| bug_world | **不足** | 0.0% | 5.0% | 0.00 | 18 | 0 | never assigned but 18 inbound near-miss races |
| mixed_world | **適正** | 17.9% | 10.0% | 1.79 | 4 | 10 | share near design (17.9% vs 10.0%) with observable assignment |
