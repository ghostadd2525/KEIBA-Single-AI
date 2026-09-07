# Version69 — Trigger Refactoring Design（Blueprint）

**Date:** 2026-07-28  
**Status:** Blueprint / 実装仕様のみ — **コード変更なし**  
**Parents:** V68 Logic Form Review / V44 Spec / V46 Migration / W-S0–S1 Shadow  
**Fixed (変更禁止):** World Meaning / Semantic Contract / Signal Meaning / Threshold 数値 / Polarity

---

## 目的

V68 で不合格とされた **R7 / R1 / R8** の Logic Form を、V43/V44 思想に整合する **実装可能な構造**へ設計する。  
本フェーズは Blueprint 完成まで。実装・Cutover は別 Decision。

---

## 設計スコープ

| 変更対象 | 内容 |
|---|---|
| Logic Form | midupper / mixed / core の MATCH 定義 |
| Decision Tree | first-match R1…R8 → MATCH 集合解決 |
| Rule Structure | R7/R1/R8 の役割再配置（Legacy コードは Soft まで不変） |

| 非対象 | 理由 |
|---|---|
| Threshold 定数の書き換え | 禁止 |
| 新 Signal 種の発明 | 禁止（既存概念の配線のみ） |
| World / Polarity 再定義 | 禁止 |

---

## 共通 Decision Tree（新構造・全 Rule 共通）

```text
1. Evaluate PRIMARY_MATCH for {core, midupper, midhole, rank7, bug}
   using Positive Logic Forms (V44 / V69)
2. Evaluate MIXED_MATCH from multi_path / unexplained
3. Let M = { w | MATCH(w) }

Decision:
  |M| = 0  →  unsatisfied
  |M| = 1  →  that world
  |M| ≥ 2  →  mixed_world
```

**廃止（V69 パス）:** 固定 Priority first-match（R1→…→R8 DEFAULT）。  
**維持（Legacy パス）:** `classify_world_line_type` 現行 R1–R8（Cutover まで）。

---

## R7 — midupper（difficulty 単独）

### ① 現行構造

```text
R7_MATCH := difficulty ≥ 0.50     # 単一原子
Priority := 7
→ midupper_world
```

（製品: `classify_world_line_type` / research mirror `R7_midupper_diff`）

### ② 新構造

```text
UPPER_AXIS := upper_ability_band↑     # 既存 ranking_concepts
DEV_AXIS   := OR( phase↑, short_field_pressure↑, high_pace↑ )
              # difficulty 単独では DEV を満たさない（V44）
APT_AXIS   := aptitude_fit↑           # 既存 proxy 可。欠落 ⇒ Must 不成立

MIDUPPER_MUST := UPPER_AXIS AND DEV_AXIS AND APT_AXIS

MIDUPPER_EXCLUDE :=
    (chaos↑ AND high_pace↑)           # rank7 領域
    OR mid_eval_band_open↑            # midhole 領域
    OR (top_gap↑ AND NOT DEV_AXIS AND NOT APT_AXIS)

MIDUPPER_AUX := support(difficulty 中〜)   # Must 置換禁止

MIDUPPER_MATCH := MIDUPPER_MUST AND NOT MIDUPPER_EXCLUDE
```

**極性:** V44 観測 polarity（batch median ↑/↓）。**閾値定数 0.50 の変更ではない**（R7 原子そのものを Must から外す）。

### ③ 変更理由

- V43/V44: midupper は 3 軸。difficulty 単独は Forbidden。  
- V66/V67: R7 が Trigger FP 最大（57）。構造が主因。

### ④ V43/V44 対応

| V44 | V69 |
|---|---|
| MIDUPPER_MUST 3-AND | 同上 |
| difficulty ∈ AUX | 同上 |
| MIDUPPER_EXCLUDE | 同上 |

### ⑤ 期待される改善

- difficulty のみの midupper 過剰割当の解消（V66 R7 FP 経路）。  
- Must 欠落時は midupper 不成立（他 World / unsatisfied へ）— Intent 精度の前提改善。  
- **保証しないもの:** Hit/ROI（PE 非変更）。APT Missing 時は unsatisfied 増の可能性。

### ⑥ Rollback

- V69 フラグ OFF → Legacy R7 経路に戻す。  
- Shadow/Dual ログは保持。Production 決定は Soft まで Legacy。

---

## R1 — mixed（圧力 OR）

### ① 現行構造

```text
R1_MATCH :=
  short_field_pressure ≥ 0.72
  AND (phase ≥ 0.48 OR chaos ≥ 0.42 OR difficulty ≥ 0.42)
Priority := 1  # 最優先 first-match
→ mixed_world
```

### ② 新構造

```text
PRIMARY := {core, midupper, midhole, rank7, bug} の MATCH 集合

MULTI_PATH := |PRIMARY| ≥ 2
UNEXPLAINED_SINGLE := exception_flag↑ AND |PRIMARY| = 0
                     # exception 欠落時は本枝不成立（Must を埋めない）

MIXED_MUST := MULTI_PATH OR UNEXPLAINED_SINGLE

MIXED_EXCLUDE := |PRIMARY| = 1    # 単一明確パス

MIXED_AUX := support(
  short_field_pressure↑
  AND concurrent_pressure(phase↑, chaos↑, difficulty↑)
)   # 現行 R1 圧力式を Aux へ降格。Must 非置換

MIXED_MATCH := MIXED_MUST AND NOT MIXED_EXCLUDE
```

**Decision Tree 上:** mixed は `|M|≥2` でも付与（MULTI_PATH と整合）。  
**廃止:** Priority=1 による圧力 first-match。

### ③ 変更理由

- V44: OR は勝ち筋単位。圧力 OR は Aux。  
- V67: OR Pass率 ~79% で弱選択；sfp 通過後 OR ほぼ冗長。

### ④ V43/V44 対応

| V44 | V69 |
|---|---|
| MIXED_MUST = multi_path ∨ unexplained | 同上 |
| 圧力バンドル = Aux | 現行 R1 式を Aux に移設 |
| phase only 定義禁止 | MATCH から圧力単軸を排除 |

### ⑤ 期待される改善

- 圧力近似による誤 mixed（V66 R1 FP 50）の削減。  
- 他 World の正検出が Priority=1 に潰されない。

### ⑥ Rollback

- V69 mixed 評価 OFF → Legacy R1 first-match に戻す。

---

## R8 — core DEFAULT

### ① 現行構造

```text
R8_MATCH := DEFAULT   # parts=[]
→ core_world when R1–R7 all FAIL
```

### ② 新構造

```text
CORE_MUST := top_gap↑ AND ability_separation↑
             # 既存 ranking_concepts（新 Signal 種ではない）

CORE_EXCLUDE :=
    chaos↑
    OR short_field_pressure↑
    OR (late_stop↑ AND sustained↑)
    OR mid_eval_band_open↑
    OR multi_path_active          # |PRIMARY without core| 等で表現可
    OR exception_flag↑

CORE_AUX := support(race_grade) OR support(distance 長距離寄り)
            OR support(short_field_pressure↓)

CORE_MATCH := CORE_MUST AND NOT CORE_EXCLUDE
# AUX は補強のみ

# 残余
if no MATCH in any world:
    → unsatisfied     # NOT core
```

**廃止:** `DEFAULT → core_world`。

### ③ 変更理由

- V42/V44: FORBIDDEN_FORM。core は能力決着の正検出。  
- V67: R8 FP 46 は正条件なしの残余落下。

### ④ V43/V44 対応

| V44 | V69 |
|---|---|
| CORE_MUST Gap∧Sep | 同上 |
| FORBIDDEN DEFAULT | 削除 |
| count=0 → unsatisfied | Decision Tree 葉 |

### ⑤ 期待される改善

- Intent 外 core 過剰（V65/V66）の構造的抑制。  
- unsatisfied の正当な出現（Positive Match 原則）。

### ⑥ Rollback

- V69 core 評価 OFF → Legacy R8 DEFAULT に戻す（Soft 以前は Production 未使用のため影響なし）。

---

## 実装モジュール仕様（未コーディング）

| モジュール（案） | 責務 |
|---|---|
| `v69_logic_form.py`（research/shadow） | MIDUPPER/MIXED/CORE MATCH 評価（本 Blueprint） |
| 既存 `v44_shadow_eval.py` | 参照・段階的置換可。V69 は R7/R1/R8 焦点の明示実装 |
| `classify_world_line_type` | **Cutover まで不変** |
| `TRIGGER_RULES` mirror | Legacy 観測用に保持。V69 パスは別構造 |

### 極性・閾値ポリシー

- ↑/↓ は **既存 V44 Shadow の batch-median polarity**（製品 Threshold 定数は変更しない）。  
- Legacy R1–R8 の数値定数（0.72 等）は Legacy パス専用のまま凍結。

### APT / exception Missing

- Must 欠落 ⇒ 当該 World MATCH=false。  
- 全体 |M|=0 ⇒ unsatisfied。  
- Aux や DEFAULT で埋めない。

---

## 非目標

- PE / Prediction / Hit ROI 改善  
- Signal パイプライン新設  
- Soft/Cutover の即時実施  

---

## 関連

- Migration: `v69-rule-migration.md`  
- Governance: `v69-governance.md`
