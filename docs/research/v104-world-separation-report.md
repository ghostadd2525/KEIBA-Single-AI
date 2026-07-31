# Version104 — World Separation Report

**Generated:** `2026-07-28T13:33:50+00:00`

mean pairwise cosine: **0.9960** → **Separation Grade: WEAK**

Lower cosine ⇒ stronger concept-profile separation. CEW assigns one label; separation here is semantic profile distinctness.

**所見:** 全ペアが cosine≥0.99 かつ separated(<0.98)=False。  
World の意味差は **平均概念ベクトルでは出ず**、Trace の Must/Exclusion ゲートに依存している。  
これは Completeness 問題ではなく、**表現チャネルの偏り**（Fidelity の別面）。

## Pairwise concept-profile cosine

| A | B | cosine | separated(<0.98) |
|---|---|---:|---|
| `core_world` | `midhole_world` | 0.9918 | False |
| `core_world` | `midupper_world` | 0.9970 | False |
| `core_world` | `mixed_world` | 0.9950 | False |
| `core_world` | `rank7_world` | 0.9935 | False |
| `midhole_world` | `midupper_world` | 0.9925 | False |
| `midhole_world` | `mixed_world` | 0.9992 | False |
| `midhole_world` | `rank7_world` | 0.9978 | False |
| `midupper_world` | `mixed_world` | 0.9965 | False |
| `midupper_world` | `rank7_world` | 0.9973 | False |
| `mixed_world` | `rank7_world` | 0.9992 | False |

## vs unsatisfied residual

| World | cosine to unsatisfied mean |
|---|---:|
| `core_world` | 0.9988 |
| `midhole_world` | 0.9898 |
| `midupper_world` | 0.9943 |
| `mixed_world` | 0.9929 |
| `rank7_world` | 0.9897 |
