# Version95 — Residual Decision Taxonomy

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parents:** V94 Residual Clustering · V88 Decision Policy · V75 Residual Contract · ADR-008（DL-C6）  
**Locks:** Prediction / World Meaning / Trigger / CEW ラベル生成 — **変更禁止**

---

## 目的

V94 により CEW=`unsatisfied`（n=176）は **新 World ではない**ことが確定した。  
内訳は Decision が読む **Metadata** として分離する。

| 主張 | 判定 |
|---|---|
| unsatisfied を Positive World に昇格 | **禁止** |
| unsatisfied を単一 Residual としてのみ扱う | **粗い**（V94: 2型） |
| Near Miss / Residual を Decision Metadata で区別 | **本フェーズの目的** |

---

## 層位置（固定）

```text
[Trigger / CEW]
  world_id = "unsatisfied"     ← 変更しない（World 契約固定）

[Decision Metadata]            ← V95 新設（設計）
  residual_class ∈ {NEAR_MISS, PURE_RESIDUAL}
  near_world ∈ {core_world, midupper_world, midhole_world, rank7_world, null}
  struct_source ∈ {exclusion_stop, all_must_fail}

[Decision Layer]
  Risk / Pool / Explanation（＋ Ticket は常に保守帯）
```

**MUST:** Metadata は `world_id` を書き換えない。  
**MUST NOT:** Metadata を PE・Trigger・順位にフィードバックする。

---

## Taxonomy（排他）

### 定義（V94 構造と 1:1）

| `residual_class` | 定義（観測） | n (285R) | 比率 |
|---|---|---:|---:|
| **NEAR_MISS** | いずれかの Positive World で `must=True` かつ `exclude=True`（Exclusion 停止） | 104 | 59% |
| **PURE_RESIDUAL** | 全 Positive World で Must 未達（`all_must_fail`） | 72 | 41% |

`other`（Must 充足かつ exclude=False なのに unsatisfied）は V94 で **0件**。契約上は `PURE_RESIDUAL` へフォールバック。

### Near Miss の副ラベル `near_world`

Exclusion で止まった World のうち **primary**（優先順）:

```text
priority: core_world > midupper_world > midhole_world > rank7_world > mixed_world > bug_world
```

V94 実測（primary）:

| `near_world` | n | Decision 上の意味 |
|---|---:|---|
| `core_world` | 81 | 能力決着仮説に近いが Exclusion で MATCH せず |
| `midhole_world` | 13 | 中位帯仮説に近いが Exclusion |
| `midupper_world` | 9 | 上位帯＋適性仮説に近いが Exclusion |
| `rank7_world` | 1 | 混戦仮説に近いが Exclusion（稀） |
| （mixed/bug primary） | 0 | 本コーパスでは primary なし |

**MUST NOT:** `near_world` を CEW として昇格・再ラベルしない。  
**MUST:** Explanation / Risk / Pool の **参照先**としてのみ使う。

### PURE_RESIDUAL

| 属性 | 値 |
|---|---|
| `near_world` | **null**（主張しない） |
| 意味 | 契約 MATCH なし・近接勝ち筋も主張しない真の残余 |
| Ticket | 保守のみ（下記 Policy） |

---

## Metadata スキーマ（設計・未実装）

```text
ResidualTaxonomyMeta
  world_id: "unsatisfied"          # CEW 固定
  residual_class: NEAR_MISS | PURE_RESIDUAL
  near_world: WorldId | null
  struct_source: exclusion_stop | all_must_fail
  excl_worlds: list[WorldId]       # 参考・複数 Exclusion
  taxonomy_version: "v95/1.0"
```

入力根拠（設計）: 既存 `decision_trace`（W-S1 / V44 logic form）の読取のみ。  
**Signal / Threshold / Trigger 本体は変更しない。**

---

## 禁止事項（Taxonomy）

| ID | 禁止 |
|---|---|
| RT-X1 | `NEAR_MISS` を新 CEW World として追加する |
| RT-X2 | `near_world` の Positive Ticket Strategy をそのまま適用する |
| RT-X3 | Taxonomy で Rank / Score / Confidence 再計算を行う |
| RT-X4 | `PURE_RESIDUAL` に勝ち筋 Explanation を付ける |
| RT-X5 | bug_world（exception_flag 欠落アーティファクト）を Near Miss primary の既定にする |

---

## 関連

- `v95-decision-policy.md` — Near Miss / Residual の Risk・Pool・Explanation
- `v95-governance.md`
- `v94-residual-breakdown.md`
- ADR-008 DL-C6（unsatisfied 勝ち筋 Ticket 化禁止）— V95 で **Metadata 拡張として解釈を精密化**（World 追加ではない）
