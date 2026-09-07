# Version68 — Trigger Logic Form Review

**Date:** 2026-07-28  
**Type:** Design Review only（実装・閾値・Signal 追加・World 変更なし）  
**Parents:** V42–V45 Contract / V66 Attribution / V67 Anatomy  
**Fixed:** World Meaning / Purpose / Contract / Signal Meaning / Polarity

---

## 結論（1行）

現行 R7・R1・R8 の Logic Form は、いずれも V43/V44 の思想と **不一致**。改善候補は **構造（AND / OR / Priority / Positive Match / Decision Tree）のみ**。Threshold・Signal 追加は対象外。

---

## 固定したもの（変更禁止）

| 固定 | 正本 |
|---|---|
| midupper = 上位能力 ∧ 展開 ∧ 適性 | V43 §2 / V44 MIDUPPER_MUST |
| mixed = 複数勝ち筋共存（または説明不能） | V43 §5 / V44 MIXED_MUST |
| core = 能力決着の **正検出**（DEFAULT 禁止） | V42 / V43 §1 / V44 CORE_MUST + FORBIDDEN_FORM |
| Signal 意味・極性 | V44 T3 / Signal Roles |

---

## R7 — `difficulty` 単独判定

### 現行 Logic Form（実装観測）

```text
R7_MATCH := difficulty↑          # 単一原子 AND（実質 1 条件）
Priority: 7（R1–R6 FAIL 後）
```

### 思想（固定）

```text
MIDUPPER_MUST := UPPER_AXIS AND DEV_AXIS AND APT_AXIS
# V44: difficulty 単独は DEV_AXIS を満たさない（Forbidden）
# V43: difficulty は Optional / Aux
```

### 評価: **思想と不一致（FAIL）**

| 観点 | 判定 | 根拠 |
|---|---|---|
| Must 数 | FAIL | 思想は 3 軸 AND。現行は 1 原子 |
| difficulty の役割 | FAIL | 思想は Aux。現行は定義本体 |
| V67 証拠 | 整合 | FP 57 すべてが当該単一条件通過；依存=Rule設計 |

---

## R1 — OR 構造

### 現行 Logic Form（実装観測）

```text
R1_MATCH :=
    sfp↑
    AND ( phase↑ OR chaos↑ OR difficulty↑ )
Priority: 1（最優先）
```

### 思想（固定）

```text
MIXED_MUST := MULTI_PATH (≥2 World 意味の同時活性) OR UNEXPLAINED_SINGLE
MIXED_AUX  := support(concurrent pressure)   # 定義本体ではない
MIXED_EXCLUDE := exactly_one_clear_path OR (定義:= phase only)
```

### 評価: **「本当に OR であるべきか」→ 現行 OR は思想の OR ではない（FAIL）**

| 観点 | 判定 | 根拠 |
|---|---|---|
| OR の意味 | FAIL | 思想の OR は「複数勝ち筋」または「説明不能」の代替。現行 OR は **圧力シグナルの代替** |
| 単軸圧力 | FAIL | V44: 単軸高値では Must を満たさない。現行は sfp∧(いずれか1) で成立 |
| Priority=1 | FAIL | 複合圧力近似が最優先 → 他 World の正検出を先に潰す（V66: FP 50） |
| V67 証拠 | 整合 | OR Pass率 ~79%；sfp 通過後 OR はほぼ冗長 |

**結論:** OR 自体が禁止なのではなく、**何を OR しているか**が誤り。思想どおりなら OR は「複数 World マッチ」側に置く。

---

## R8 — DEFAULT

### 現行 Logic Form（実装観測）

```text
R8_MATCH := DEFAULT   # parts=[] ; R1–R7 全 FAIL
→ core_world
```

### 思想（固定）

```text
CORE_MUST := top_gap↑ AND ability_separation↑
CORE_MATCH := CORE_MUST AND NOT CORE_EXCLUDE
FORBIDDEN_FORM := CORE_MATCH := (all other worlds fail)   # V44 明示禁止
count(MATCH)==0 → unsatisfied   # NOT silent core DEFAULT
```

### 評価: **Positive Match 化は可能か → 設計上は必須・現行は不可能な形（FAIL）**

| 観点 | 判定 | 根拠 |
|---|---|---|
| DEFAULT = core | FAIL | V42/V44 Forbidden Form |
| Positive Match 化 | **可能（構造として）** | 既存 Signal 概念 `top_gap` / `ability_separation` を Must AND に使う Form は V44 に既記 |
| 本フェーズの制約 | Signal **追加**禁止 | ただし両概念は 285R 既に算出可能（W-S1 ranking_concepts）。「新 Signal 種の発明」ではない |
| V67 証拠 | 整合 | FP 46 は正条件なしの残余落下 |

**Positive Match 化:** 思想上 **必須**。DEFAULT のままでは思想一致不可。

---

## 総合 Compatibility

| Rule | 思想一致 | 主問題の種類 |
|---|---|---|
| R7 | **No** | Must 軸欠落・Aux の本体化 |
| R1 | **No** | OR 対象の取り違え・Priority |
| R8 | **No** | Forbidden DEFAULT |

Threshold / 新 Signal 種ではなく、**Logic Form 構造**が論点（V67 C と一致）。
