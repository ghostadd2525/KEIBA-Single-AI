# Version38 — Information Density

## ③ Density chain

```text
World prior entropy
  → SubWorld count / utilization
  → SubWorld entropy
  → Information gain vs flat World bucket
```

- World prior H: `0.000` bits (ratio `0.0%`)

| World | n | H_sub | design capacity | ratio | unused bits | IG (=H_sub) |
|-------|--:|------:|----------------:|------:|------------:|------------:|
| core_world | 0 | 0.000 | 1.000 | 0.0% | 1.000 | 0.000 |
| midupper_world | 51 | 0.672 | 1.585 | 42.4% | 0.913 | 0.672 |
| midhole_world | 0 | 0.000 | 0.000 | N/A | 0.000 | 0.000 |
| rank7_world | 0 | 0.000 | 1.000 | 0.0% | 1.000 | 0.000 |
| bug_world | 0 | 0.000 | 0.000 | N/A | 0.000 | 0.000 |
| mixed_world | 0 | 0.000 | 0.000 | N/A | 0.000 | 0.000 |

## Reading

- **IG ≈ SubWorld entropy** within a World: how much SubWorld splits the World bucket.
- **unused_design_bits**: design capacity not realized (missing / unused SubWorlds).
- Near-zero World prior entropy means almost all races share one World — SubWorld cannot restore World-level diversity.
