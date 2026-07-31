# Version21 Research - Context Map

**Date:** 2026-07-27T10:35:22+00:00  

Where each feature amplifies or weakens (associational).

```
Feature → Condition → Outcome
```

## Breeder

- **Amplifies when:** `venue=新潟` (effect=0.0623, hit=9.1%, n=11)
- **Weakens when:** `category=3yo_maiden` (effect=-0.0286, hit=0.0%, n=14)

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `open` | 1 | 100.0% | 0.9714 | Exploratory |
| `3yo_maiden` | 14 | 0.0% | -0.0286 | Medium |
| `class_1win` | 8 | 0.0% | -0.0286 | Exploratory |
| `2yo_newcomer` | 4 | 0.0% | -0.0286 | Exploratory |
| `other` | 4 | 0.0% | -0.0286 | Exploratory |
| `stakes` | 2 | 0.0% | -0.0286 | Exploratory |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `新潟` | 11 | 9.1% | 0.0623 | Medium |
| `札幌` | 14 | 0.0% | -0.0286 | Medium |
| `中京` | 10 | 0.0% | -0.0286 | Medium |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_<=10` | 13 | 7.7% | 0.0484 | Medium |
| `field_15-16` | 10 | 0.0% | -0.0286 | Medium |
| `field_11-14` | 10 | 0.0% | -0.0286 | Medium |
| `field_17+` | 2 | 0.0% | -0.0286 | Exploratory |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `turf` | 16 | 0.0% | -0.0286 | Medium |
| `dirt` | 12 | 0.0% | -0.0286 | Medium |

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `mile` | 14 | 0.0% | -0.0286 | Medium |
| `sprint` | 12 | 0.0% | -0.0286 | Medium |
| `middle` | 2 | 0.0% | -0.0286 | Exploratory |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `晴` | 9 | 0.0% | -0.0286 | Exploratory |
| `小雨` | 1 | 0.0% | -0.0286 | Exploratory |
| `雨` | 1 | 0.0% | -0.0286 | Exploratory |
| `曇` | 18 | 5.6% | 0.027 | Medium |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 4 | 0.0% | -0.0286 | Exploratory |
| `non_debut` | 31 | 3.2% | 0.0037 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 3 | 0.0% | -0.0286 | Exploratory |
| `重` | 1 | 0.0% | -0.0286 | Exploratory |
| `良` | 25 | 4.0% | 0.0114 | Medium |

## Damsire

- **Amplifies when:** `distance_bucket=sprint` (effect=0.1167, hit=20.0%, n=10)
- **Weakens when:** `field_bucket=field_11-14` (effect=-0.0833, hit=0.0%, n=10)

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_17+` | 4 | 25.0% | 0.1667 | Exploratory |
| `field_11-14` | 10 | 0.0% | -0.0833 | Medium |
| `field_15-16` | 8 | 0.0% | -0.0833 | Exploratory |
| `field_<=10` | 14 | 14.3% | 0.0595 | Medium |

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `2yo_maiden` | 4 | 25.0% | 0.1667 | Exploratory |
| `2yo_newcomer` | 4 | 25.0% | 0.1667 | Exploratory |
| `class_1win` | 7 | 0.0% | -0.0833 | Exploratory |
| `other` | 4 | 0.0% | -0.0833 | Exploratory |
| `stakes` | 3 | 0.0% | -0.0833 | Exploratory |
| `open` | 1 | 0.0% | -0.0833 | Exploratory |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 4 | 25.0% | 0.1667 | Exploratory |
| `non_debut` | 32 | 6.2% | -0.0208 | Medium |

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `sprint` | 10 | 20.0% | 0.1167 | Medium |
| `middle` | 2 | 0.0% | -0.0833 | Exploratory |
| `long` | 1 | 0.0% | -0.0833 | Exploratory |
| `mile` | 13 | 7.7% | -0.0064 | Medium |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `曇` | 16 | 18.8% | 0.1042 | Medium |
| `晴` | 8 | 0.0% | -0.0833 | Exploratory |
| `雨` | 2 | 0.0% | -0.0833 | Exploratory |
| `小雨` | 1 | 0.0% | -0.0833 | Exploratory |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `中京` | 12 | 0.0% | -0.0833 | Medium |
| `札幌` | 13 | 15.4% | 0.0705 | Medium |
| `新潟` | 11 | 9.1% | 0.0076 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 3 | 0.0% | -0.0833 | Exploratory |
| `重` | 1 | 0.0% | -0.0833 | Exploratory |
| `良` | 23 | 13.0% | 0.0471 | Medium |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `turf` | 15 | 13.3% | 0.05 | Medium |
| `dirt` | 11 | 9.1% | 0.0076 | Medium |

## Owner

- **Amplifies when:** `category=2yo_maiden` (effect=0.5062, hit=60.0%, n=5)
- **Weakens when:** `category=3yo_maiden` (effect=-0.0938, hit=0.0%, n=14)

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `2yo_maiden` | 5 | 60.0% | 0.5062 | Exploratory |
| `3yo_maiden` | 14 | 0.0% | -0.0938 | Medium |
| `class_1win` | 4 | 0.0% | -0.0938 | Exploratory |
| `2yo_newcomer` | 4 | 0.0% | -0.0938 | Exploratory |
| `other` | 3 | 0.0% | -0.0938 | Exploratory |
| `open` | 1 | 0.0% | -0.0938 | Exploratory |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `晴` | 9 | 0.0% | -0.0938 | Exploratory |
| `雨` | 1 | 0.0% | -0.0938 | Exploratory |
| `曇` | 14 | 7.1% | -0.0223 | Medium |

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `sprint` | 8 | 0.0% | -0.0938 | Exploratory |
| `middle` | 2 | 0.0% | -0.0938 | Exploratory |
| `mile` | 13 | 7.7% | -0.0168 | Medium |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_15-16` | 8 | 0.0% | -0.0938 | Exploratory |
| `field_17+` | 2 | 0.0% | -0.0938 | Exploratory |
| `field_<=10` | 14 | 14.3% | 0.0491 | Medium |
| `field_11-14` | 8 | 12.5% | 0.0312 | Exploratory |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `dirt` | 7 | 0.0% | -0.0938 | Exploratory |
| `turf` | 16 | 6.2% | -0.0312 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 4 | 0.0% | -0.0938 | Exploratory |
| `良` | 20 | 5.0% | -0.0437 | Medium |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 4 | 0.0% | -0.0938 | Exploratory |
| `non_debut` | 28 | 10.7% | 0.0134 | Medium |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `新潟` | 8 | 12.5% | 0.0312 | Exploratory |
| `札幌` | 13 | 7.7% | -0.0168 | Medium |
| `中京` | 11 | 9.1% | -0.0028 | Medium |

## Popularity

- **Amplifies when:** `weather=晴` (effect=0.2185, hit=53.8%, n=13)
- **Weakens when:** `going=稍` (effect=-0.32, hit=0.0%, n=5)

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `middle` | 3 | 66.7% | 0.3467 | Exploratory |
| `long` | 1 | 0.0% | -0.32 | Exploratory |
| `sprint` | 15 | 26.7% | -0.0533 | Medium |
| `mile` | 19 | 36.8% | 0.0484 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 5 | 0.0% | -0.32 | Exploratory |
| `重` | 1 | 0.0% | -0.32 | Exploratory |
| `良` | 33 | 39.4% | 0.0739 | Medium |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_17+` | 4 | 0.0% | -0.32 | Exploratory |
| `field_11-14` | 15 | 46.7% | 0.1467 | Medium |
| `field_15-16` | 14 | 28.6% | -0.0343 | Medium |
| `field_<=10` | 17 | 29.4% | -0.0259 | Medium |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `雨` | 2 | 0.0% | -0.32 | Exploratory |
| `小雨` | 1 | 0.0% | -0.32 | Exploratory |
| `晴` | 13 | 53.8% | 0.2185 | Medium |
| `曇` | 23 | 26.1% | -0.0591 | Medium |

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `open` | 1 | 0.0% | -0.32 | Exploratory |
| `2yo_newcomer` | 7 | 14.3% | -0.1771 | Exploratory |
| `class_1win` | 9 | 44.4% | 0.1244 | Exploratory |
| `other` | 5 | 20.0% | -0.12 | Exploratory |
| `2yo_maiden` | 5 | 40.0% | 0.08 | Exploratory |
| `stakes` | 4 | 25.0% | -0.07 | Exploratory |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `新潟` | 16 | 12.5% | -0.195 | Medium |
| `中京` | 17 | 47.1% | 0.1506 | Medium |
| `札幌` | 17 | 35.3% | 0.0329 | Medium |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 7 | 14.3% | -0.1771 | Exploratory |
| `non_debut` | 43 | 34.9% | 0.0288 | Medium |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `turf` | 23 | 39.1% | 0.0713 | Medium |
| `dirt` | 15 | 26.7% | -0.0533 | Medium |

## Sire

- **Amplifies when:** `surface=dirt` (effect=0.0631, hit=9.1%, n=11)
- **Weakens when:** `category=3yo_maiden` (effect=-0.0278, hit=0.0%, n=15)

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `2yo_newcomer` | 4 | 25.0% | 0.2222 | Exploratory |
| `3yo_maiden` | 15 | 0.0% | -0.0278 | Medium |
| `class_1win` | 7 | 0.0% | -0.0278 | Exploratory |
| `2yo_maiden` | 4 | 0.0% | -0.0278 | Exploratory |
| `stakes` | 3 | 0.0% | -0.0278 | Exploratory |
| `other` | 3 | 0.0% | -0.0278 | Exploratory |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 4 | 25.0% | 0.2222 | Exploratory |
| `non_debut` | 32 | 0.0% | -0.0278 | Medium |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `dirt` | 11 | 9.1% | 0.0631 | Medium |
| `turf` | 15 | 0.0% | -0.0278 | Medium |

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `mile` | 13 | 7.7% | 0.0491 | Medium |
| `sprint` | 10 | 0.0% | -0.0278 | Medium |
| `middle` | 2 | 0.0% | -0.0278 | Exploratory |
| `long` | 1 | 0.0% | -0.0278 | Exploratory |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_<=10` | 13 | 7.7% | 0.0491 | Medium |
| `field_15-16` | 11 | 0.0% | -0.0278 | Medium |
| `field_11-14` | 10 | 0.0% | -0.0278 | Medium |
| `field_17+` | 2 | 0.0% | -0.0278 | Exploratory |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `札幌` | 15 | 6.7% | 0.0389 | Medium |
| `中京` | 12 | 0.0% | -0.0278 | Medium |
| `新潟` | 9 | 0.0% | -0.0278 | Exploratory |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `曇` | 17 | 5.9% | 0.031 | Medium |
| `晴` | 8 | 0.0% | -0.0278 | Exploratory |
| `雨` | 1 | 0.0% | -0.0278 | Exploratory |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 3 | 0.0% | -0.0278 | Exploratory |
| `重` | 1 | 0.0% | -0.0278 | Exploratory |
| `良` | 22 | 4.5% | 0.0177 | Medium |

## Trainer

- **Amplifies when:** `field_bucket=field_<=10` (effect=0.1286, hit=21.4%, n=14)
- **Weakens when:** `category=class_1win` (effect=-0.0857, hit=0.0%, n=8)

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `open` | 1 | 100.0% | 0.9143 | Exploratory |
| `2yo_maiden` | 4 | 25.0% | 0.1643 | Exploratory |
| `class_1win` | 8 | 0.0% | -0.0857 | Exploratory |
| `2yo_newcomer` | 6 | 0.0% | -0.0857 | Exploratory |
| `other` | 4 | 0.0% | -0.0857 | Exploratory |
| `3yo_maiden` | 12 | 8.3% | -0.0024 | Medium |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_<=10` | 14 | 21.4% | 0.1286 | Medium |
| `field_15-16` | 10 | 0.0% | -0.0857 | Medium |
| `field_11-14` | 8 | 0.0% | -0.0857 | Exploratory |
| `field_17+` | 3 | 0.0% | -0.0857 | Exploratory |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `dirt` | 10 | 20.0% | 0.1143 | Medium |
| `turf` | 15 | 0.0% | -0.0857 | Medium |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 6 | 0.0% | -0.0857 | Exploratory |
| `non_debut` | 29 | 10.3% | 0.0177 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 3 | 0.0% | -0.0857 | Exploratory |
| `重` | 1 | 0.0% | -0.0857 | Exploratory |
| `良` | 22 | 13.6% | 0.0506 | Medium |

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `middle` | 2 | 0.0% | -0.0857 | Exploratory |
| `sprint` | 9 | 11.1% | 0.0254 | Exploratory |
| `mile` | 14 | 7.1% | -0.0143 | Medium |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `雨` | 2 | 0.0% | -0.0857 | Exploratory |
| `小雨` | 1 | 0.0% | -0.0857 | Exploratory |
| `曇` | 13 | 15.4% | 0.0681 | Medium |
| `晴` | 10 | 10.0% | 0.0143 | Medium |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `札幌` | 10 | 10.0% | 0.0143 | Medium |
| `新潟` | 13 | 7.7% | -0.0088 | Medium |
| `中京` | 12 | 8.3% | -0.0024 | Medium |

## Win Odds

- **Amplifies when:** `weather=晴` (effect=0.2185, hit=53.8%, n=13)
- **Weakens when:** `going=稍` (effect=-0.32, hit=0.0%, n=5)

### Condition axis `distance_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `middle` | 3 | 66.7% | 0.3467 | Exploratory |
| `long` | 1 | 0.0% | -0.32 | Exploratory |
| `sprint` | 15 | 26.7% | -0.0533 | Medium |
| `mile` | 19 | 36.8% | 0.0484 | Medium |

### Condition axis `going`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `稍` | 5 | 0.0% | -0.32 | Exploratory |
| `重` | 1 | 0.0% | -0.32 | Exploratory |
| `良` | 33 | 39.4% | 0.0739 | Medium |

### Condition axis `field_bucket`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `field_17+` | 4 | 0.0% | -0.32 | Exploratory |
| `field_11-14` | 15 | 46.7% | 0.1467 | Medium |
| `field_15-16` | 14 | 28.6% | -0.0343 | Medium |
| `field_<=10` | 17 | 29.4% | -0.0259 | Medium |

### Condition axis `weather`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `雨` | 2 | 0.0% | -0.32 | Exploratory |
| `小雨` | 1 | 0.0% | -0.32 | Exploratory |
| `晴` | 13 | 53.8% | 0.2185 | Medium |
| `曇` | 23 | 26.1% | -0.0591 | Medium |

### Condition axis `category`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `open` | 1 | 0.0% | -0.32 | Exploratory |
| `2yo_newcomer` | 7 | 14.3% | -0.1771 | Exploratory |
| `class_1win` | 9 | 44.4% | 0.1244 | Exploratory |
| `other` | 5 | 20.0% | -0.12 | Exploratory |
| `2yo_maiden` | 5 | 40.0% | 0.08 | Exploratory |
| `stakes` | 4 | 25.0% | -0.07 | Exploratory |

### Condition axis `venue`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `新潟` | 16 | 12.5% | -0.195 | Medium |
| `中京` | 17 | 47.1% | 0.1506 | Medium |
| `札幌` | 17 | 35.3% | 0.0329 | Medium |

### Condition axis `debut`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `debut` | 7 | 14.3% | -0.1771 | Exploratory |
| `non_debut` | 43 | 34.9% | 0.0288 | Medium |

### Condition axis `surface`

| Condition | N | Hit | Effect | Conf |
|-----------|--:|----:|-------:|------|
| `turf` | 23 | 39.1% | 0.0713 | Medium |
| `dirt` | 15 | 26.7% | -0.0533 | Medium |

## Decision

```
Action Type: Causal Evidence Research (associational)
Prediction Mutation: FORBIDDEN
Use: context for Knowledge / Shadow design — not product wiring
```
