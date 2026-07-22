# Version 2.2 Accuracy — Roadmap（設計のみ）

**Date:** 2026-07-22  
**Status:** **クローズ（履歴）** — V2 Accuracy 検証終了。以降の計画は `docs/releases/v2-accuracy-v3-roadmap.md`  
**Final:** `docs/releases/v2-accuracy-final-report.md`（PE のみ採用 / Hit 218）  
**Baseline（V2 Final）:** PE-V2-A PASS = **Hit 218** / Purchase 187 / Winner in Pool 274/285  
**前提文書:** `docs/releases/v2-accuracy-design-review.md`（V2.2 改訂）  
**G1 分類:** `compare/v2_accuracy_g1_layer_classification.csv`

> **Update 2026-07-22:** PE PASS / RP FAIL / CE-A FAIL をもって Version 2 Accuracy 検証終了。本 V2.2 Roadmap の未実施 Phase（CE-C / PE-B/C / RO）は **V3 へ持ち越し**。

---

## 0. 方針転換（V2.1 → V2.2）

| V2.1 仮定 | V2.2 結論 |
|-----------|-----------|
| RP-V2-A（NEAR 置換）で G1 を回収し Hit>218 | **FAIL**（218→218 / Rescue 0/11） |
| パラメータ（mid_cap / N+2 / fire_cap）調整で再挑戦 | **棄却** — Trigger 自体が不足 |
| 実装順 PE → RP → CE | **PE 固定 → CE 優先。RP 系は主要候補から外す** |

---

## 1. レイヤー別ロードマップ

```text
Version2.2 Accuracy
│
├─ Layer1 Candidate Pool（PE-V2）     【ロック】
│   └─ PE-V2-A PASS 維持。追加 AB は後段
│
├─ Layer2 RePick（RP-V2）             【主要候補から除外】
│   ├─ RP-V2-A/B/C/D … 新規実装・再AB しない
│   └─ 将来: 「並べ替え専用」に責務限定した別設計が必要なら V2.3+
│
└─ Layer3 Candidate Evaluation（CE-V2）【次の主要レバー】
    └─ スコア/生存順位の入力品質 → Pool・RePick の両方に波及
```

### Phase A — 設計確定（実装なし・本フェーズ）

| ID | 成果物 | 状態 |
|----|--------|------|
| A1 | 3 層責務の再定義 | 本改訂で実施 |
| A2 | G1 11 件の層別分類 | CSV 提出 |
| A3 | RP-V2 を主要候補から外す合意 | 本 Roadmap |
| A4 | CE-V2 設計レビュー（単独） | **設計書提出済** → `docs/releases/v2-ce-v2-design-review.md` |

### Phase B — CE-V2（次の実装候補・まだ実装しない）

| 設計 ID | 目的 | 想定母集団 | Hard Gate（案） |
|---------|------|------------|-----------------|
| **CE-V2-A** | Softmax 温度較正 | other_1_3 + 遠位 G1（2）の間接 | Hit > **218** |
| **CE-V2-B** | Near-cut score lift | rank2–3 / 境界 mid | 同上 |
| **CE-V2-C**（新・要設計） | mid（rank7–10）生存スコア再重み | G1 遠位・境界の surv 押し上げ | 同上 + churn_hit=0 |

**Control ロック:** PE-V2-A ON / RP OFF = Hit **218**。  
**禁止:** RP Flag を同時 ON にした合成 AB。

### Phase C — Layer1 追加（CE の後、または CE FAIL 時の代替）

| 設計 ID | 目的 | 備考 |
|---------|------|------|
| **PE-V2-B** | rank710 の pool_priority | first_loss=candidate_pool 残 11 向け |
| **PE-V2-C** | 浅位 entry guard | other_1_3 残 |

### Phase D — Layer2「並べ替え」再設計（V2.3 候補・非コミット）

RP-V2-A のパラメータ再挑戦は行わない。  
**並べ替え型 4 件**（函館 / 中山12-13 / 阪神 / 小倉）を救うなら、別 ID で:

| 仮 ID | 責務 | 非目標 |
|-------|------|--------|
| **RO-V2**（Reorder Only） | Pool 内の selected 並べ替え / compress 巻き戻し。N 不変 | Rescue Trigger としての NEAR 置換、G1 allowlist |

RO-V2 は **CE-V2 と PE 追加の結果を見てから** 要否判断。V2.2 の必須パスではない。

---

## 2. G1（11）× Phase 対応表

| 分類 | n | V2.2 での扱い |
|------|--:|----------------|
| 既得 Hit（Delete/multi） | 1 | 対象外 |
| RePick並べ替え不足 | 4 | Phase D（任意）または CE 間接 |
| RePick境界不足 | 4 | CE-V2-C 検討 / RO は非優先 |
| Evaluation不足（遠位） | 2 | **Phase B 主対象** |
| Pool不足 | 0 | —（G1 は全件 in_pool） |

**期待 Hit レンジ（仮説・未検証）:**

| Phase | Control | Treatment 仮説 |
|-------|--------:|----------------|
| B CE-V2-A のみ | 218 | **219〜221** |
| B+C | 218 | **220〜223** |
| +D RO（任意） | 上記 | +0〜+3（並べ替え 4 の一部） |

Hard Gate は常に **Treatment.Hit > Control.Hit（現行 218）**。

---

## 3. やらないこと（V2.2）

- RP-V2-A の mid_cap / NEAR 帯 / fire_cap 再調整実装
- RP-V2-B/C/D の実装・AB
- Delete Boundary 変更
- Prediction / PI / Catalog / Web 変更
- 複数 Flag 同時 ON の合成 AB

---

## 4. 次の意思決定ゲート

```text
[今] CE-V2 設計書提出済
  → CE-V2 設計承認？
      YES → Phase B 実装許可を別指示で（推奨順: CE-V2-A → CE-V2-C）
      NO  → PE-V2-B/C 設計へ分岐、または Accuracy 一時停止
```

**実装コードは別指示まで書かない。**

---

## 5. 参照

| 文書 | パス |
|------|------|
| **CE-V2 設計書** | `docs/releases/v2-ce-v2-design-review.md` |
| Accuracy 改訂設計 | `docs/releases/v2-accuracy-design-review.md` |
| G1 層分類 CSV | `compare/v2_accuracy_g1_layer_classification.csv` |
| RP-V2-A AB FAIL | `docs/ops/v2-rp-v2-a-ab-report.md` |
| G1 FAIL 観測 | `docs/ops/v2-rp-v2-a-g1-fail-observation.md` |
| PE-V2-A AB PASS | `docs/ops/v2-pe-v2-a-ab-report.md` |
