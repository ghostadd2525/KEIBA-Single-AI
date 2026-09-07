# Version94 — Unsatisfied Residual Clustering

**Generated:** `2026-07-28T12:09:08+00:00`  
**Population:** CEW=`unsatisfied` **176 / 285**  
**Locks:** Prediction / Trigger / World Meaning / PE / Production  
**Question:** 176件は 2〜3 パターンに分かれるか？ → 新 World vs Residual？

## Verdict

**`KEEP_AS_RESIDUAL_WITH_NEAR_MISS_TAXONOMY`**

176件の大半は均質な『新勝ち筋』ではなく、Exclusion近接（104）と Must全失敗（72）の2型。 Exclusion側は既存 World（特に core/midupper）の近接失敗。 新 World 追加より Residual 維持＋既存 World の Exclusion/標本問題の方が先。

- Recommend new World now: **False**
- Recommend keep Residual: **True**

## 1. 構造分割（W-S1 互換・排他）

| 構造 | n | 比率 |
|---|---:|---:|
| Exclusion 停止（Must 充足後 exclude） | 104 | 59.1% |
| 全 World Must 失敗 | 72 | 40.9% |
| other | 0 | 0.0% |

→ **2型が主**（104 / 72）。ここが第一のクラスタリング結果。

## 2. Exclusion 内訳（既存 World 近接）

### `excl_primary:core_world` — n=81 (46.0%)
- struct: `{'exclusion_stop': 81}`
- hit@1: 0.765
- nearest World: `core_world` (cos=0.993)
- exclusion hits: `{'core_world': 81, 'midupper_world': 23}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `core_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

### `excl_primary:midhole_world` — n=13 (7.4%)
- struct: `{'exclusion_stop': 13}`
- hit@1: 0.615
- nearest World: `mixed_world` (cos=0.998)
- exclusion hits: `{'midhole_world': 13}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `midhole_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

### `excl_primary:midupper_world` — n=9 (5.1%)
- struct: `{'exclusion_stop': 9}`
- hit@1: 0.778
- nearest World: `core_world` (cos=0.998)
- exclusion hits: `{'midupper_world': 9}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `midupper_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

### `excl_primary:rank7_world` — n=1 (0.6%)
- struct: `{'exclusion_stop': 1}`
- hit@1: 1.000
- nearest World: `mixed_world` (cos=1.000)
- exclusion hits: `{'rank7_world': 1}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `rank7_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

## 3. 教師なし KMeans（特徴量）

- best k=6 / silhouette=0.268

| k | silhouette | sizes |
|---:|---:|---|
| 2 | 0.246 | `{0: 94, 1: 82}` |
| 3 | 0.228 | `{1: 64, 0: 47, 2: 65}` |
| 4 | 0.235 | `{2: 49, 3: 48, 1: 23, 0: 56}` |
| 5 | 0.249 | `{2: 33, 1: 38, 4: 16, 0: 33, 3: 56}` |
| 6 | 0.268 | `{3: 54, 2: 22, 4: 30, 0: 13, 1: 56, 5: 1}` |

### `kmeans_k6_c0` — n=13 (7.4%)
- struct: `{'exclusion_stop': 13}`
- hit@1: 0.615
- nearest World: `mixed_world` (cos=0.998)
- exclusion hits: `{'midhole_world': 13}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `midhole_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。
- drivers: must_midhole(+3.54z), ability_separation(-1.10z), must_core(-0.92z), struct_all_must_fail(-0.83z), struct_exclusion(+0.83z)

### `kmeans_k6_c1` — n=56 (31.8%)
- struct: `{'all_must_fail': 56}`
- hit@1: 0.679
- nearest World: `mixed_world` (cos=0.999)
- exclusion hits: `{}`
- **judgment:** `DIFFUSE_OR_WEAK_SIGNAL` → `KEEP_RESIDUAL`
- reason: 規模はあるが既存 World（mixed_world）と概念が近い（cos=0.9993279106683824）。 新 World より Threshold/Signal 充足の方が先。
- drivers: struct_all_must_fail(+1.20z), struct_exclusion(-1.20z), n_must_true(-1.06z), must_core(-0.92z), top_monopoly(-0.89z)

### `kmeans_k6_c2` — n=22 (12.5%)
- struct: `{'all_must_fail': 16, 'exclusion_stop': 6}`
- hit@1: 0.773
- nearest World: `core_world` (cos=0.997)
- exclusion hits: `{'midupper_world': 6}`
- **judgment:** `MIXED_RESIDUAL` → `KEEP_RESIDUAL`
- reason: 均質な勝ち筋パターンとしては弱い。Residual 契約を維持。
- drivers: upper_ability_band(+1.23z), field_size(-1.17z), mid_eval_band_open(+1.05z), difficulty(-0.98z), top_gap(-0.94z)

### `kmeans_k6_c3` — n=54 (30.7%)
- struct: `{'exclusion_stop': 54}`
- hit@1: 0.759
- nearest World: `core_world` (cos=0.998)
- exclusion hits: `{'core_world': 51, 'midupper_world': 26}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `core_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。
- drivers: n_must_true(+1.04z), must_core(+0.97z), struct_all_must_fail(-0.83z), struct_exclusion(+0.83z), must_midupper(+0.78z)

### `kmeans_k6_c4` — n=30 (17.0%)
- struct: `{'exclusion_stop': 30}`
- hit@1: 0.767
- nearest World: `core_world` (cos=0.977)
- exclusion hits: `{'core_world': 30}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `core_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。
- drivers: top_monopoly(+1.43z), field_size(-1.34z), mid_eval_band_open(+1.27z), upper_ability_band(+1.22z), difficulty(-1.17z)

### `kmeans_k6_c5` — n=1 (0.6%)
- struct: `{'exclusion_stop': 1}`
- hit@1: 1.000
- nearest World: `mixed_world` (cos=1.000)
- exclusion hits: `{'rank7_world': 1}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `rank7_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。
- drivers: must_rank7(+13.23z), ability_separation(-1.62z), top_monopoly(-1.41z), upper_ability_band(-1.18z), n_exclude_true(+1.07z)

## 4. Agglomerative（k=3 確認）

silhouette=0.220

### `agglo_k3_c0` — n=71 (40.3%)
- struct: `{'exclusion_stop': 71}`
- hit@1: 0.746
- nearest World: `core_world` (cos=0.999)
- exclusion hits: `{'core_world': 48, 'midupper_world': 32, 'midhole_world': 13, 'rank7_world': 1}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 100% が Exclusion 停止で、主に `core_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

### `agglo_k3_c1` — n=59 (33.5%)
- struct: `{'all_must_fail': 59}`
- hit@1: 0.644
- nearest World: `mixed_world` (cos=0.999)
- exclusion hits: `{}`
- **judgment:** `DIFFUSE_OR_WEAK_SIGNAL` → `KEEP_RESIDUAL`
- reason: 規模はあるが既存 World（mixed_world）と概念が近い（cos=0.9992098924583566）。 新 World より Threshold/Signal 充足の方が先。

### `agglo_k3_c2` — n=46 (26.1%)
- struct: `{'all_must_fail': 13, 'exclusion_stop': 33}`
- hit@1: 0.804
- nearest World: `core_world` (cos=0.987)
- exclusion hits: `{'core_world': 33}`
- **judgment:** `NEAR_MISS_EXISTING_WORLD` → `NOT_NEW_WORLD`
- reason: クラスタの 72% が Exclusion 停止で、主に `core_world` 近接。 新 World ではなく既存 World の Exclusion/Threshold 問題。

## 5. 判断基準（本レポート）

| 条件 | 判定 |
|---|---|
| Exclusion≥70% かつ特定 World 近接 | **NEAR_MISS** → 新 World 禁止。既存 Threshold/Exclusion |
| n≥26 かつ Must全失敗優勢 かつ既存概念 cos 低 | **WORLD_CANDIDATE**（設計のみ・勝ち筋化禁止） |
| 小断片 / 混合 | **KEEP_RESIDUAL** |

## 6. 結論（運用）

1. **今すぐ新しい Positive World を追加すべきではない**（勝ち筋化禁止継続）。
2. Residual 176 は『意味のないゴミ』ではなく、**Exclusion近接 + Must未達**の残差分。
3. 将来の World 追加を検討するなら、まず Exclusion で止まっている **core / midupper** の
   標本・Forbidden 条件を監査（新ラベルより契約修復）。
4. Must全失敗 72 は候補プールだが、均質勝ち筋の証明は本クラスタだけでは不十分 → Residual 維持。

## 関連

- `w-s1-unsatisfied-root-cause.md`
- `v75-world-strategy-contract.md`（unsatisfied Residual）
- `v94-residual-breakdown.md` / `v94-governance.md`
