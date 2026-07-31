# W-S1 Near Miss Report（Potential Positive Match）

**Date:** 2026-07-28  
**Version:** 57  
**Source:** Unsatisfied 176 rows in `w-s1-dual-eval-rows.jsonl`  
**Rule:** 改善・実装禁止。集計のみ。

---

## Definition

**Near Miss（本監査）** = ある Canonical World について:

- `exclude === false`
- `must_gaps` の長さが **1**
- 現状 `match !== true`

意味: **新しい Signal 種類を足さず**、既存1軸が batch-median 極性で PASS すれば Must が揃い、Exclusion が無ければ MATCH 候補。

---

## Counts

| Class | n | Notes |
|---|---:|---|
| Unsatisfied total | 176 | |
| Any-world 1-gap near miss | 176 | 全件が何らかの1ギャップを持つ |
| **Polarity / Signal 1-axis near miss** | **63** | multi_path・exception_flag 以外 |
| mixed **logic** near miss (`multi_path≥2 OR unexplained`) | **113** | 設計Must。1 Signal では非充足 |
| bug `exception_flag` as sole missing Must | 構造的に全件欠落 | コーパスに flag 無し → Signal追加なしでは **不可** |

---

## True Near Miss（63）by World

| near_world | n |
|---|---:|
| midhole_world | 31 |
| midupper_world | 22 |
| core_world | 10 |
| rank7_world | 0 |
| mixed_world | 0（本クラス外） |
| bug_world | 0（本クラス外） |

## True Near Miss（63）by missing Must axis

| missing_must | n |
|---|---:|
| top_monopoly↓ | 21 |
| upper_ability_band↑ | 14 |
| mid_eval_band_open↑ | 10 |
| aptitude_fit↑ | 7 |
| ability_separation↑ | 6 |
| top_gap↑ | 4 |
| development_pressure↑ | 1 |

---

## Logic Near Miss（113）

`mixed_world` の Must:

```text
multi_path >= 2 OR unexplained_single
```

1軸の極性反転では埋まらない。他 World の Positive Match がもう1つ必要、または unexplained flag（存在しない）。

---

## Relation to Exclusion cohort（104）

Must=True かつ exclude=True の World は Near Miss 定義から **除外**（exclude=False が条件）。  
よって Near Miss 63 は主に「Must 未達側」のレースに属する。

---

## Conclusion

- **Potential Positive Match without new Signal types: 63 / 176**  
- 残りは Exclusion（104構造）または mixed/bug の設計Must に支配される。

*Classification only.*
