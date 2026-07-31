# Version 3 Lab (P5 Freeze) — Offline only

**Status:** P5 Lab Foundation Frozen  
**Design:** `docs/releases/v3-design-report.md`  
**Report:** `docs/releases/v3-p5-freeze-report.md`  
**Baseline:** `baselines/lab_baseline_p5.json`

## Boundary

| Do | Do not |
|----|--------|
| Offline Lab under `research/v3_lab` | Import from Pages / PI / win5-ai production |
| All `F_V3_*` default OFF → identity | Accuracy algorithm work without new approval |
| Use frozen contracts / registry / baseline | Modify Representation / Admission / Selection without approval |
| Prepare Accuracy experiments | Implement Evaluation / Purchase in this freeze |

## Frozen Pipeline

```text
Representation → Admission → Selection → Evaluation(stub) → Purchase(stub)
```

## Regenerate Baseline

```bash
cd research
set PYTHONPATH=.
python -m v3_lab.freeze
```

## Tests

```bash
cd research/v3_lab
python -m unittest discover -s tests -v
```
