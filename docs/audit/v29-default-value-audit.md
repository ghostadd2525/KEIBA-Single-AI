# Version29 — DEFAULT=0.5 Value Audit

**Date:** 2026-07-27T13:34:28+00:00  

## Constant

- Name: `STABLE_FEATURE_DEFAULTS['race_leg_difficulty']`
- Value: `0.5`
- File: `demo_probability_feature_utils.py`
- Applier: `enrich_stable_features`
- Caller: `FeatureGenerator.build_feature_matrix` (Production Core)

## Scope classification

| Scope | Applies? |
|-------|:--------:|
| Research only | `False` |
| Prediction Bundle numeric field only | `False` |
| Production Core CE + World Trigger path | `True` |

## Evidence

- FeatureGenerator.build_feature_matrix → enrich_stable_features runs inside CorePipeline.evaluate before WorldClassifier.classify_world
- Live: loader missing col=`True`, after FG=`[0.5]`, CE meta=`0.5`, research=`0.5`

## Implication (factual)

DEFAULT=0.5 is applied **before** World Trigger classification on Production Core. Research V25 merely copies the already-defaulted meta value.

## Guardrails

- No fix / no threshold change in this audit
