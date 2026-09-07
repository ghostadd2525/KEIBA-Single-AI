# Version103 — Core Contract Surface Audit

**Date:** 2026-07-28  
**Status:** Shadow Audit only · **実装禁止**  
**Parents:** ADR-009 · ADR-010 · V102  
**Locks:** Prediction / Ranking / World / Trigger / Near Miss Logic / Decision / Feature 追加 — **変更禁止**  
**原則:** 新しい意味は作らない。公開面（Contract Surface）だけを監査する。

---

## 一文

**Semantic は既に足りる。問いは「何を first-class で渡すか」だけである。**

---

## 分類結果（要約）

| ID | Item | Classification |
|---|---|---|
| MS-1 | Expected Strategy | **KEEP_DERIVED** |
| MS-2 | Affinity | **PROMOTE_FIRST_CLASS** |
| MS-3 | Exclusion Reasons | **PROMOTE_FIRST_CLASS** |
| MS-4 | Explanation Confidence | **PROMOTE_FIRST_CLASS** |
| MS-5 | Near Miss Class | **PROMOTE_FIRST_CLASS** |
| MS-6 | Natural Explanation | **DO_NOT_EXPORT** |

---

## 評価尺度

| 評語 | 意味 |
|---|---|
| H | 高い（公開・利用・安定の根拠が強い） |
| M | 中 |
| L | 低い |
| — | 非該当 |

導出コスト: **L**=trace 直読 / **M**=固定式の再計算 / **H**=Trigger 再実行や外部知識必須  

---

## 項目別監査

### MS-1 Expected Strategy → `KEEP_DERIVED`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | L | V102: World キー静的マップのみ。レース固有意味なし |
| 重複性 | H | `expected_strategy_key ≡ world_label`（285/285） |
| 導出コスト | L | world_id → V75 レジストリ参照 |
| Contract 安定性 | M | レジストリ改訂で変わるが race payload 汚染を避けられる |
| Single AI 利用価値 | M | 説明文テンプレはクライアント側マップで足りる |
| Win5 AI 利用価値 | L | 購入 Decision に直接不要（ADR-008） |

**判定:** race payload に載せると World と二重。**バージョン付き外部レジストリ参照を維持**（導出・共有マップ）。

---

### MS-2 Affinity → `PROMOTE_FIRST_CLASS`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | H | 連続近さ。Near Miss class と役割が違う（V96/V102） |
| 重複性 | M | Near Miss では `near_world ≡ affinity_top` 多いがベクトル全体は非冗長 |
| 導出コスト | L–M | `must_gaps` / must から V96 式（固定すれば安定） |
| Contract 安定性 | H | 式と MUST_N を Contract 固定すれば再現可能 |
| Single AI 利用価値 | H | 説明・UI・監査（買わせない＝Decision 別） |
| Win5 AI 利用価値 | M | 説明メタ。V97 により Risk SKIP 自動価値は否定済み |

**判定:** unsatisfied 時に `affinity{core,midupper,midhole,rank7}` を **導出結果の serialize** として公開。新 Feature ではない。

---

### MS-3 Exclusion Reasons → `PROMOTE_FIRST_CLASS`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | H | 「なぜ MATCH しなかったか」の中核。bool だけでは説明が閉じにくい |
| 重複性 | L | `exclude:true` と理由リストは補完関係 |
| 導出コスト | M | V44 Exclusion 述語のミラー（Trigger 本体は触らない） |
| Contract 安定性 | H | Trigger/Logic Form 固定下では理由集合も固定 |
| Single AI 利用価値 | H | 説明 UI / 監査 |
| Win5 AI 利用価値 | M | 説明。券種ロジックには使わない |

**判定:** Near Miss（および exclude=true の World）について `exclusion_reasons[]` を first-class 化。意味の新造ではなく **既存述語の露出**。

---

### MS-4 Explanation Confidence → `PROMOTE_FIRST_CLASS`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | H | ADR-010 の正式出力族 |
| 重複性 | M | Completeness と相関するが「消費者向けスカラー/バンドル」として別価値 |
| 導出コスト | L–M | EC-S/W/N/T は現有スロットから計算可（V101 Contract） |
| Contract 安定性 | H | ADR-010 / V101 で定義済み |
| Single AI 利用価値 | H | 説明の確度表示（勝率禁止） |
| Win5 AI 利用価値 | M | 表示・監査。Skip 自動閾値化は別契約なしでは禁止（V101） |

**判定:** `ExplanationConfidenceBundle` を Core Contract Surface に含める（実装は別 Decision）。

---

### MS-5 Near Miss Class → `PROMOTE_FIRST_CLASS`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | H | V95 Taxonomy（NEAR_MISS / PURE_RESIDUAL + near_world） |
| 重複性 | M | Affinity top と重なり得るが **離散クラス**として必要 |
| 導出コスト | L | must∧exclude / all_must_fail |
| Contract 安定性 | H | V94/V95/V102 で定義固定 |
| Single AI 利用価値 | H | Decision Metadata の主キー（Ticket 勝ち筋化は禁止） |
| Win5 AI 利用価値 | H | 同上 |

**判定:** `residual_class` + `near_world` を first-class。Logic 変更ではなく serialize。

---

### MS-6 Natural Explanation → `DO_NOT_EXPORT`

| 軸 | 評定 | 根拠 |
|---|---|---|
| 公開価値 | M | 人向けには有用だが Core 責務外に寄せられる |
| 重複性 | H | 構造化 Trace + ES マップから生成可能＝二重の源 |
| 導出コスト | M–H | 文言テンプレ・言語・版で揺れる |
| Contract 安定性 | L | 散文は回帰・国際化で壊れやすい |
| Single AI 利用価値 | H | **提示層**で生成すべき |
| Win5 AI 利用価値 | M | 同上 |

**判定:** Core は構造化意味のみ。自然文は Single/Win5 の Presentation。Core payload に載せない。

---

## 関連

- `v103-export-matrix.md`
- `v103-payload-contract.md`
- `v103-governance.md`
- V102 Missing / Redundancy
