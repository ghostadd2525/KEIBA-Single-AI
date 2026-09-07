# Version81 — World Interaction Report

**Generated:** `2026-07-28T09:18:46+00:00`  
**Corpus:** 285R / CEW labels  
**Scope:** Feature **Interaction only**（単体特徴量ランキング禁止）  
**Metrics:** MI / Information Gain / Lift@top25% / SHAP-interaction proxy（Friedman H / GBM）  
**Pace coverage:** 240/285

## Atomic bases（Interaction 構成要素のみ・単独では順位付けしない）

`history`, `win_prob`, `odds`, `field_size`, `top_gap`, `upper_band`, `ability_sep`, `ability_sub`, `mid_band`, `pace`

## `rank7_world`

n_races=65 / n_horses=1047 / winners=65

### Top 2-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × win_prob` | 0.0124 | 0.0022 | 1.2911 | 0.0513 |
| 2 | `odds × ability_sep` | 0.0180 | 0.0039 | 1.2862 | 0.0002 |
| 3 | `history × odds` | 0.0155 | 0.0050 | 1.2296 | 0.0000 |
| 4 | `odds × upper_band` | 0.0034 | 0.0040 | 1.2911 | 0.0000 |
| 5 | `win_prob × odds` | 0.0063 | 0.0011 | 1.2296 | 0.1856 |
| 6 | `history × upper_band` | 0.0025 | 0.0025 | 1.2911 | 0.0000 |
| 7 | `history × ability_sep` | 0.0010 | 0.0039 | 1.3526 | 0.0000 |
| 8 | `odds × field_size` | 0.0176 | 0.0133 | 0.9222 | 0.1856 |
| 9 | `win_prob × ability_sub` | 0.0119 | 0.0007 | 1.0452 | 0.0010 |
| 10 | `odds × top_gap` | 0.0019 | 0.0021 | 1.2911 | 0.0000 |
| 11 | `win_prob × ability_sep` | 0.0020 | 0.0028 | 1.0452 | 0.0000 |
| 12 | `history × field_size` | 0.0075 | 0.0165 | 0.7378 | 0.1161 |
| 13 | `win_prob × field_size` | 0.0145 | 0.0137 | 0.7992 | 0.0000 |
| 14 | `odds × ability_sub` | 0.0015 | 0.0021 | 1.1066 | 0.0000 |
| 15 | `history × top_gap` | 0.0000 | 0.0001 | 1.0452 | 0.0000 |

### Top 3-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × odds × win_prob` | 0.0165 | 0.0140 | 1.8444 | 0.0597 |
| 2 | `history × win_prob × odds` | 0.0165 | 0.0140 | 1.8444 | 0.0374 |
| 3 | `history × upper_band × odds` | 0.0091 | 0.0030 | 1.4140 | 0.0304 |
| 4 | `win_prob × field_size × upper_band` | 0.0116 | 0.0120 | 0.3689 | 0.0996 |
| 5 | `history × win_prob × field_size` | 0.0107 | 0.0019 | 0.7992 | 0.1186 |
| 6 | `history × field_size × odds` | 0.0093 | 0.0103 | 0.7992 | 0.0337 |
| 7 | `win_prob × field_size × top_gap` | 0.0040 | 0.0020 | 1.1681 | 0.0000 |
| 8 | `win_prob × top_gap × pace` | 0.0146 | 0.0017 | 1.1066 | 0.0000 |
| 9 | `win_prob × pace × upper_band` | 0.0109 | 0.0017 | 0.8607 | 0.0065 |
| 10 | `top_gap × upper_band × odds` | 0.0091 | 0.0020 | 1.3526 | 0.0000 |
| 11 | `ability_sub × pace × win_prob` | 0.0146 | 0.0017 | 0.7378 | 0.0342 |
| 12 | `history × win_prob × pace` | 0.0083 | 0.0005 | 0.9837 | 0.0709 |
| 13 | `history × pace × upper_band` | 0.0025 | 0.0062 | 0.8607 | 0.0154 |
| 14 | `win_prob × field_size × pace` | 0.0012 | 0.0024 | 1.2296 | 0.0000 |
| 15 | `field_size × pace × odds` | 0.0000 | 0.0010 | 1.1681 | 0.0127 |

## `midhole_world`

n_races=24 / n_horses=347 / winners=24

### Top 2-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `win_prob × field_size` | 0.0356 | 0.0038 | 1.3295 | 0.0160 |
| 2 | `history × pace` | 0.0177 | 0.0020 | 1.3295 | 0.0000 |
| 3 | `history × field_size` | 0.0000 | 0.0058 | 1.3295 | 0.0000 |
| 4 | `history × win_prob` | 0.0000 | 0.0049 | 0.9971 | 0.0000 |
| 5 | `win_prob × ability_sep` | 0.0066 | 0.0185 | 0.4986 | 0.0262 |
| 6 | `win_prob × ability_sub` | 0.0084 | 0.0097 | 0.8309 | 0.0000 |
| 7 | `win_prob × top_gap` | 0.0084 | 0.0095 | 0.4986 | 0.0117 |
| 8 | `history × top_gap` | 0.0000 | 0.0007 | 1.1633 | 0.0000 |
| 9 | `win_prob × upper_band` | 0.0164 | 0.0153 | 0.3324 | 0.0010 |
| 10 | `history × upper_band` | 0.0000 | 0.0029 | 0.9971 | 0.0000 |
| 11 | `odds × pace` | 0.0123 | 0.0016 | 0.8309 | 0.0262 |
| 12 | `win_prob × mid_band` | 0.0018 | 0.0070 | 0.4986 | 0.0000 |
| 13 | `win_prob × pace` | 0.0229 | 0.0000 | 0.9971 | 0.0011 |
| 14 | `ability_sub × pace` | 0.0043 | 0.0001 | 1.0223 | 0.0000 |
| 15 | `history × odds` | 0.0000 | 0.0052 | 0.8309 | 0.0000 |

### Top 3-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × odds × win_prob` | 0.0209 | 0.0095 | 1.6619 | 0.0777 |
| 2 | `history × win_prob × odds` | 0.0209 | 0.0095 | 1.6619 | 0.0119 |
| 3 | `history × field_size × top_gap` | 0.0026 | 0.0113 | 1.1633 | 0.0342 |
| 4 | `ability_sub × pace × win_prob` | 0.0309 | 0.0019 | 1.1633 | 0.0196 |
| 5 | `win_prob × field_size × pace` | 0.0419 | 0.0048 | 1.4957 | 0.0000 |
| 6 | `history × win_prob × top_gap` | 0.0309 | 0.0070 | 0.4986 | 0.1496 |
| 7 | `win_prob × field_size × odds` | 0.0178 | 0.0030 | 1.3295 | 0.0129 |
| 8 | `win_prob × pace × upper_band` | 0.0344 | 0.0023 | 0.8309 | 0.0227 |
| 9 | `history × field_size × pace` | 0.0174 | 0.0061 | 1.3295 | 0.0000 |
| 10 | `top_gap × history × pace` | 0.0242 | 0.0007 | 0.8309 | 0.0737 |
| 11 | `mid_band × history × field_size` | 0.0000 | 0.0207 | 0.3324 | 0.1023 |
| 12 | `field_size × pace × odds` | 0.0183 | 0.0008 | 1.1633 | 0.0049 |
| 13 | `top_gap × pace × odds` | 0.0216 | 0.0070 | 0.4986 | 0.0103 |
| 14 | `history × pace × odds` | 0.0142 | 0.0012 | 1.1633 | 0.0000 |
| 15 | `win_prob × top_gap × pace` | 0.0317 | 0.0016 | 0.8309 | 0.0105 |

## `unsatisfied`

n_races=176 / n_horses=2451 / winners=176

### Top 2-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × win_prob` | 0.0086 | 0.0045 | 1.4312 | 0.0465 |
| 2 | `win_prob × odds` | 0.0123 | 0.0037 | 1.3404 | 0.0175 |
| 3 | `history × odds` | 0.0143 | 0.0054 | 1.2495 | 0.0011 |
| 4 | `win_prob × field_size` | 0.0185 | 0.0027 | 1.2722 | 0.0029 |
| 5 | `odds × ability_sep` | 0.0091 | 0.0027 | 1.2268 | 0.1915 |
| 6 | `win_prob × ability_sep` | 0.0158 | 0.0020 | 1.2495 | 0.1213 |
| 7 | `odds × mid_band` | 0.0110 | 0.0028 | 1.2041 | 0.0000 |
| 8 | `history × ability_sep` | 0.0005 | 0.0044 | 1.4312 | 0.0000 |
| 9 | `win_prob × ability_sub` | 0.0163 | 0.0011 | 1.1586 | 0.0317 |
| 10 | `history × field_size` | 0.0080 | 0.0029 | 1.1813 | 0.0000 |
| 11 | `history × ability_sub` | 0.0085 | 0.0021 | 1.2722 | 0.0000 |
| 12 | `win_prob × pace` | 0.0172 | 0.0005 | 1.1359 | 0.0372 |
| 13 | `history × upper_band` | 0.0000 | 0.0022 | 1.1813 | 0.0000 |
| 14 | `odds × field_size` | 0.0032 | 0.0030 | 1.1132 | 0.0000 |
| 15 | `history × top_gap` | 0.0091 | 0.0021 | 1.0223 | 0.0000 |

### Top 3-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × win_prob × odds` | 0.0146 | 0.0163 | 1.9537 | 0.0096 |
| 2 | `history × odds × win_prob` | 0.0146 | 0.0163 | 1.9537 | 0.0045 |
| 3 | `win_prob × field_size × pace` | 0.0248 | 0.0076 | 1.6130 | 0.0000 |
| 4 | `field_size × pace × odds` | 0.0073 | 0.0071 | 1.5448 | 0.0055 |
| 5 | `win_prob × field_size × upper_band` | 0.0170 | 0.0182 | 0.5452 | 0.2168 |
| 6 | `field_size × upper_band × odds` | 0.0184 | 0.0193 | 0.2499 | 0.0424 |
| 7 | `history × field_size × pace` | 0.0077 | 0.0070 | 1.6357 | 0.0000 |
| 8 | `history × pace × odds` | 0.0117 | 0.0035 | 1.1586 | 0.0056 |
| 9 | `history × field_size × odds` | 0.0096 | 0.0069 | 1.1813 | 0.0000 |
| 10 | `history × top_gap × odds` | 0.0076 | 0.0035 | 1.1359 | 0.0111 |
| 11 | `history × upper_band × odds` | 0.0091 | 0.0046 | 1.4085 | 0.0000 |
| 12 | `win_prob × field_size × odds` | 0.0029 | 0.0022 | 1.2041 | 0.0159 |
| 13 | `mid_band × history × field_size` | 0.0061 | 0.0147 | 0.4998 | 0.0781 |
| 14 | `history × win_prob × upper_band` | 0.0076 | 0.0017 | 1.2949 | 0.0000 |
| 15 | `top_gap × history × pace` | 0.0033 | 0.0016 | 1.1813 | 0.0060 |

## `core_world`

n_races=8 / n_horses=133 / winners=8

### Top 2-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `win_prob × odds` | 0.0134 | 0.0281 | 1.4669 | 0.0859 |
| 2 | `history × win_prob` | 0.0028 | 0.0322 | 1.9559 | 0.0000 |
| 3 | `history × field_size` | 0.0000 | 0.0117 | 1.4669 | 0.0749 |
| 4 | `history × odds` | 0.0009 | 0.0060 | 1.9559 | 0.0074 |
| 5 | `history × top_gap` | 0.0010 | 0.0064 | 1.4669 | 0.0000 |
| 6 | `history × mid_band` | 0.0000 | 0.0117 | 1.4669 | 0.0000 |
| 7 | `win_prob × top_gap` | 0.0000 | 0.0064 | 1.4669 | 0.0859 |
| 8 | `history × upper_band` | 0.0000 | 0.0057 | 0.9779 | 0.0000 |
| 9 | `win_prob × ability_sep` | 0.0000 | 0.0060 | 1.4669 | 0.0000 |
| 10 | `history × ability_sep` | 0.0000 | 0.0057 | 0.9779 | 0.0000 |
| 11 | `win_prob × field_size` | 0.0000 | 0.0057 | 0.9779 | 0.0447 |
| 12 | `win_prob × mid_band` | 0.0000 | 0.0060 | 1.4669 | 0.0000 |
| 13 | `win_prob × upper_band` | 0.0000 | 0.0060 | 0.9779 | 0.0000 |
| 14 | `history × ability_sub` | 0.0010 | 0.0057 | 0.4890 | 0.0000 |
| 15 | `odds × field_size` | 0.0311 | 0.0000 | 0.9779 | 0.0000 |

### Top 3-way

| Rank | Interaction | MI | IG | Lift | SHAP-proxy |
|---:|---|---:|---:|---:|---:|
| 1 | `history × odds × win_prob` | 0.0000 | 0.0667 | 2.4449 | 0.0645 |
| 2 | `win_prob × field_size × top_gap` | 0.0002 | 0.0378 | 1.4669 | 0.0554 |
| 3 | `history × top_gap × odds` | 0.0177 | 0.0296 | 2.4449 | 0.0037 |
| 4 | `history × field_size × top_gap` | 0.0000 | 0.0164 | 1.9559 | 0.1250 |
| 5 | `history × win_prob × odds` | 0.0000 | 0.0667 | 2.4449 | 0.0303 |
| 6 | `win_prob × field_size × upper_band` | 0.0302 | 0.0282 | 0.4890 | 0.0535 |
| 7 | `history × win_prob × upper_band` | 0.0142 | 0.0060 | 1.4669 | 0.0455 |
| 8 | `top_gap × upper_band × history` | 0.0000 | 0.0282 | 0.4890 | 0.0070 |
| 9 | `history × win_prob × top_gap` | 0.0000 | 0.0274 | 1.4669 | 0.0000 |
| 10 | `history × field_size × odds` | 0.0019 | 0.0117 | 1.4669 | 0.0000 |
| 11 | `win_prob × top_gap × upper_band` | 0.0000 | 0.0308 | 0.0000 | 0.0074 |
| 12 | `field_size × upper_band × odds` | 0.0111 | 0.0368 | 0.0000 | 0.0000 |
| 13 | `mid_band × history × field_size` | 0.0000 | 0.0154 | 0.9779 | 0.0000 |
| 14 | `win_prob × field_size × odds` | 0.0025 | 0.0060 | 0.4890 | 0.0016 |
| 15 | `history × win_prob × field_size` | 0.0000 | 0.0057 | 0.9779 | 0.0000 |

## `midupper_world`

insufficient（n_races=6）

## `mixed_world`

insufficient（n_races=6）
