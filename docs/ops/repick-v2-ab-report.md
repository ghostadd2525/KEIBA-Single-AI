# RePick v2 — AB Report (ISSUE-REPICK-V2-001)

**Generated:** 2026-07-21T10:21:19  
**AB_PASS:** **False**  
**Flag recommendation:** `OFF`（Exit 未達 → 既定 OFF 維持）

---

## 1. 実装差分

| ファイル | 内容 |
|----------|------|
| `v2_repick_v2.py` | **新規** — `WIN5_REPICK_V2_ENABLED` 既定 OFF、匿名 G1′ NEAR、N不変 max1、journal |
| `demo_ticket_optimizer_core.py` | thin hook（T-R7F 後 → `apply_win5_repick_v2`） |
| `test_repick_v2.py` | **新規** — Unit Test |
| `_run_repick_v2_ab_evaluation.py` | **新規** — Phase255 スタック上の単独 AB |
| 本レポート / JSON / CSV | `compare/repick_v2_*` |

**非変更:** Collector / ETL / Prediction V1 28特徴 / Pool / Entry / Delete / T-R7N 等

---

## 2. Unit Test 結果

```text
python -m unittest test_repick_v2 -v
Ran 5 tests — OK
```

| テスト | 結果 |
|--------|------|
| Flag OFF 恒等 | PASS |
| NEAR displacement + N不変 | PASS |
| Winner を優先しない（匿名） | PASS |
| no_victim でサイズ維持 | PASS |
| ソースに winner 決定パスなし | PASS |

---

## 3. AB 実行結果

| arm | Hit | rank710 | other_miss | n |
|-----|----:|--------:|-----------:|--:|
| Control (Flag OFF) | **215** | **16** | 19 | 285 |
| Treatment (Flag ON) | **220** | **11** | 19 | 285 |

- **R_G1** = **4/11 ≈ 36.4%**（Exit 下限ちょうど）
- **ΔHit** = +5 / **Hit損失** = 0
- **fired_tx** = 100（匿名 NEAR 発火）
- Control 契約値 Hit=216 / rank710=15 と **不一致** → Exit **AF-12（AB 無効寄り）**

G1 トレース要約（`compare/repick_v2_ab_trace.csv`）:

| 救済（in_repick_tx=1） | 4件 | 中京-11 / 中山-11 / 中山-10(04-19) / 京都-10(04-25) |
| 発火したが winner 非入場 | あり | 例: 阪神-10（匿名 cand ≠ winner） |
| no_near_candidate | 多数 | FAR/SLOT は初回 AB 対象外 |

---

## 4. Exit Criteria 判定

| gate | 結果 | 備考 |
|------|------|------|
| AB-R1 / AB-R2 改善率 ≥4/11 | **PASS** | 4/11 |
| AB-H1/H2/H3 Hit | **PASS** | Tx≥216, 損失0, Δ≥0 |
| AB-K1 rank710 ≤15 | **PASS** | 11 |
| AB-O1 other_miss ≤19 | **PASS** | 19 |
| AB-C1 churn_hit=0 | **FAIL** | 77 |
| AB-C2 churn_g1≤8 | **FAIL** | 95 |
| AB-C3 churn_race≤0.05 | **FAIL** | 0.351 |
| AB-I1 Control=契約 | **FAIL** | Hit 215≠216, rank710 16≠15 |
| AB-I2 N不変 | **PASS** | |
| AB-I3 匿名 | **PASS** | Unit + 設計 |
| AB-I4 単独 | **PASS** | |

**総合: AB_PASS = False**

Stop: 正式 AB FAIL **1回目**（連続カウンタ=1）。ST-F1（連続2）未達。

---

## 5. Canary 判定

| 段階 | 判定 |
|------|------|
| C0（AB_PASS + Human） | **不可**（AB_PASS=False） |
| C1–C3 | **未実施** |
| Canary 昇格 | **No** |

---

## 6. Rollback 可能性確認

| 項目 | 状態 |
|------|------|
| モジュール既定 `WIN5_REPICK_V2_ENABLED` | **False** |
| AB 後 `restore_defaults()` | Flag OFF に戻済 |
| 製品既定 ON | **していない** |
| Rollback 操作 | **不要**（常時 OFF = 既に Rollback 状態） |
| Exit RB-1 | AB FAIL → Flag 強制 OFF（充足） |

**結論: Exit 未達のため Feature Flag は OFF のまま。Canary / Version2 採用は行わない。**

---

## Artifacts

- `compare/repick_v2_control_fire_path.csv`
- `compare/repick_v2_treatment_fire_path.csv`
- `compare/repick_v2_ab_trace.csv`
- `compare/repick_v2_ab_result.json`
