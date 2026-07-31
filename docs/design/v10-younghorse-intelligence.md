# Version10 Design — Young Horse Intelligence

**Status:** Design only（実装なし / コード変更禁止）  
**Date:** 2026-07-27  
**Scope:** 出走歴0（2歳新馬 / 初出走）でも、通常レースと **運用上同等品質** の Prediction 体験を成立させる  
**Hard Lock:** PE / CE / AI / Prediction Logic は変更しない  

**根拠:**  
`docs/research/v9-younghorse-analysis.md` · `docs/research/v91-rank-degeneracy-analysis.md` · `docs/design/v91-tie-resolver.md` · `docs/design/v92-prediction-snapshot.md` · `docs/audit/v10-prioritization-audit.md` · `docs/audit/v94-source-feasibility-audit.md`

**Sibling:** `docs/design/v10-evidence-quality-model.md`

---

## 0. Verdict

| 問い | 結論 |
|------|------|
| 出走歴0で何が足りないか | **過去走 Evidence**（着順・ペース・騎手継続・前走間隔等）が定義不能 |
| Score を上げて同等にするか | **しない**（PE/AI Lock）。スコア空間は新馬で既に潰れている |
| 「同等品質」の定義 | Bundle の `win_prob` ではなく、**一意トップ選定の運用品質**（Strict Hit・説明可能な Evidence・退化時の解決率） |
| 代替戦略 | **不足 Evidence → Tier 代替 Evidence** を Snapshot に固定し、**後段（Tie Resolver / Intelligence Layer）だけ**が読む |

```
通常レース:  過去走 Evidence  →（PE 既存）→ 一意スコア → Strict 選定
初出走:      過去走 = ∅     →（PE 既存・退化多）→ Soft 群
             Tier1–3 Evidence → Snapshot → Intelligence Layer → 一意選定（Score 非改変）
```

---

## 1. 目的・調査対象

### 1.1 目的

出走歴0頭でも、通常レースと同等品質で Prediction できるようにする。

「同等」は次を満たすこと（Score 改変ではない）:

| 品質次元 | 通常レース | 初出走（目標） |
|----------|------------|----------------|
| 一意トップ | 概ね一意 | Degeneracy 時も **Evidence で一意化** |
| Soft≈Strict | ギャップ小 | Soft−Strict ギャップを **回収**（天井≈Soft） |
| 説明可能性 | 印・順位 | Tier Evidence の寄与チェーンをメタに残す |
| リーク耐性 | — | `observed_at ≤ prediction_created_at` |

### 1.2 調査対象（固定）

| セグメント | 定義 |
|------------|------|
| **出走歴0** | `starts_before == 0`（履歴無し） |
| **2歳新馬** | レース名に「新馬」等。本コーパスでは初出走と同一セル |

非対象（本票の主KPI外）: 2歳未勝利（出走歴≥1）、3歳未勝利、継続騎乗比較。

---

## 2. Hard Lock と配置

### 2.1 変更禁止

| 領域 | 本設計 |
|------|--------|
| PE | 未変更 |
| CE | 未変更 |
| AI 推論 | 未変更 |
| Prediction Logic（印・rank・bundle 契約） | 未変更 |
| ResultAutomation Hit 定義のコア | 未変更（観測メタ追加は将来別承認） |

### 2.2 許可される論理レイヤ（設計）

```
┌──────────────────────────────────────────┐
│ Prediction Bundle（本番・イミュータブル）   │
│  win_prob / model_rank / marks          │
└──────────────────┬───────────────────────┘
                   │ prediction_id 紐付けのみ
                   ▼
┌──────────────────────────────────────────┐
│ Prediction Snapshot（Research）           │
│  Tier1–3 Evidence @ pred time            │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ Young Horse Intelligence Layer           │
│  · Debut Gate                            │
│  · Evidence Completeness                 │
│  · Tie Resolver（Score 非改変）           │
│  · Quality Grade（本票 + Quality Model） │
└──────────────────────────────────────────┘
```

Intelligence Layer は **PE の外側**。入力は Bundle（読取）+ Snapshot。出力は:

- `official_top_pick`（Shadow→将来 Soft Launch）
- `evidence_chain`
- `yh_quality_grade`
- 常に `score_mutated=false`

---

## 3. 不足 Evidence → 代替 Evidence

### 3.1 通常レースが持つが、出走歴0では欠けるもの

| 不足 ID | 通常レースの Evidence | 初出走での状態 |
|---------|----------------------|----------------|
| E-past-finish | 前走着順・着差 | **欠落（定義不能）** |
| E-past-pace | ペース・脚質実測 | **欠落** |
| E-past-class | 昇級・クラス実績 | **欠落** |
| E-jockey-cont | 継続騎乗 / 乗替 | **N/A（debut_no_prior）** |
| E-rest | 間隔・ローテ | **欠落 or デビュー固定** |
| E-form | 近走調子曲線 | **欠落** |

これらを PE に「埋める」ことはしない。代替は **別チャネルの Evidence**。

### 3.2 代替マップ（中核）

| 不足 | 代替 Tier | 代替 Evidence | 代替の論理 |
|------|-----------|---------------|------------|
| 過去走パフォーマンス | **Tier1** | 人気 / 単勝 / 想定人気 | 市場が事前情報を集約 |
| 個体能力の代理 | **Tier2** | 厩舎 / 父 / 母父 / 生産牧場 | 仕上がり・血統・生産の事前 |
| 当日の仕上がり | **Tier3** | 馬体重 / 追切 / 調教 | 発表後の身体・調教信号 |
| 騎手継続 | — | **代替なし**（ゲート除外） | 定義不能を無理に埋めない |

### 3.3 Tier 定義

| Tier | 名称 | 役割 | 活性化の目安 |
|------|------|------|----------------|
| **Tier1** | 市場情報 | タイ解決の主信号。同等品質の最短経路 | 発売後〜締切前に Snapshot 可能なら必須 |
| **Tier2** | 能力情報 | 市場未充足・早朝予測・Soft 外補強の事前 | 枠出以降ほぼ静的。常時収集 |
| **Tier3** | 当日状態 | 仕上がり差分。市場と直交 | 発表ウィンドウ後のみ。欠測は正規 Missing |

**消費順序（Resolver / Intelligence）:** Tier1 → Tier2 → Tier3 → 弱フォールバック（枠・馬番）。  
欠損 Tier はスキップ（Fail-Open）。Score / `win_prob` は使わない（タイ内同一のため無効）。

---

## 4. Evidence カタログ（評価）

評価軸の定義は Sibling `v10-evidence-quality-model.md` に従う。  
以下は Young Horse / 初出走セグメント向けの設計値（V9.1–9.4 実測 + 仮説）。

凡例:

- **Pred前取得:** Prediction 永続化時点で原則取得可能か  
- **Quality:** モデル上の目標グレード（A–D）  
- **Coverage:** 出走歴0コーパスで値が埋まる想定割合  
- **欠損率:** 1 − Coverage（正規 N/A は分母除外可）  
- **AI改善期待:** Strict / Soft回収への期待（PE非改変前提）

### 4.1 Tier1 — 市場情報

| Evidence | 取得元 | Pred前取得 | Quality | Coverage | 欠損率 | AI改善期待 |
|----------|--------|:----------:|:-------:|:--------:|:------:|:----------:|
| **人気** `popularity` | JRA odds API `type=1` 内 popularity / Netkeiba shutuba | **条件付 YES**（発売後） | **A** | 発売後 **高（目標 ≥90%）** / 発売前 **0%** | 発売前 High / 後 ≤10% | **High** |
| **単勝** `win_odds` | JRA odds API `type=1`（PI board 既存）/ shutuba | **条件付 YES** | **A** | 同上 | 同上 | **High** |
| **想定人気** `expected_popularity` | 派生: `win_odds` 昇順ランク | **単勝に連動** | **A** | 単勝に等しい | 単勝に等しい | **High** |

**設計メモ**

- 現状実測: refresh 経路で人気・単勝 **0% filled**（V9.1）→ Young Horse Intelligence の **最大ブロッカー**
- 発売前 Prediction では Tier1 全体 Missing → Tier2 へフォールバックし、`yh_quality_grade` を下げる（「同等」未達を明示）
- Anti-leak: Snapshot は予測時刻以前のみ。結果後の確定人気で上書き禁止

### 4.2 Tier2 — 能力情報

| Evidence | 取得元 | Pred前取得 | Quality | Coverage | 欠損率 | AI改善期待 |
|----------|--------|:----------:|:-------:|:--------:|:------:|:----------:|
| **厩舎** `trainer` | Netkeiba shutuba HTML（`_trainer` 既存）→ CSV/DB 露出 | **YES**（枠出後） | **A–B** | 露出後 **≥90%** | ≤10% | **High** |
| **父** `sire` | Netkeiba 血統ページ / pedigree DB（未整備） | **YES**（静的・要コレクタ） | **B**（ID正規化後 A） | コレクタ後 **≥80%** | ≤20% | **High** |
| **母父** `damsire` | 同上 | **YES** | **B** | **≥75%** | ≤25% | **High** |
| **生産牧場** `breeder` / `farm` | Netkeiba 馬プロフィール / 産地表記（未接続） | **YES**（静的・要コレクタ） | **B–C** | 初期 **50–80%**（表記ゆれ） | 20–50% | **Med–High** |

**設計メモ**

- 厩舎は **最短 Tier2**（parse 済・未露出）。P0-B（V10 Prioritization）と一致
- 父・母父・生産牧場は過去走ゼロの **古典的事前情報**。PE 特徴には入れず、Resolver prior / Mining 専用
- `trainer_prior` / `sire_prior` / `farm_prior`: 当該レースより前の新馬成績のみ（リーク防止）。定義は Quality Model §Prior

### 4.3 Tier3 — 当日状態

| Evidence | 取得元 | Pred前取得 | Quality | Coverage | 欠損率 | AI改善期待 |
|----------|--------|:----------:|:-------:|:--------:|:------:|:----------:|
| **馬体重** `horse_weight` | Netkeiba 当日ボード（未実装）。※斤量と混同禁止 | **発表後のみ YES** | **B** | 発表前 **0%** / 後 **高** | 発表前 正規 Missing | **Med** |
| **追切** `workout_rating` | 調教/追切ページ（未接続・スケール未定義） | **調教公開後 YES** | **C**（スケール確定後 B） | 初期 **低〜中** | High | **Med–High**（仮説） |
| **調教** `training_time` | 同上（時計・ラップ） | **公開後 YES** | **C** | 同上 | High | **Med** |

**設計メモ**

- Tier3 はウィンドウが狭い。早朝 Prediction では意図的 Missing → Grade に反映
- Soft 外 3R（本命群外）の救済は Tier3 単独では期待しすぎない（別 Research）

### 4.4 明示的非代替（使わない）

| 項目 | 理由 |
|------|------|
| タイ内 `win_prob` | ビット同一で情報量ゼロ |
| `jockey_continued` | 初出走 N/A |
| 距離・開催・頭数・天候 | レース共通 → タイ内非分散 |
| 斤量を馬体重代用 | 契約違反・誤情報 |

---

## 5. 「通常レースと同等品質」の達成モデル

### 5.1 Quality Grade（運用）

詳細は `v10-evidence-quality-model.md`。要約:

| Grade | 条件（出走歴0） | 意味 |
|-------|-----------------|------|
| **Q-Parity** | Tier1 充足 +（Tier2 厩舎 or 血統いずれか）+ Resolver 解決 | **同等品質達成** |
| **Q-Strong** | Tier1 充足、Resolver 解決 | 市場で一意化可能 |
| **Q-Partial** | Tier1 欠・Tier2 充足 | 早朝/発売前。同等未達だが説明可能 |
| **Q-Weak** | Tier1–2 欠、Tier3 のみ or ほぼ欠落 | 現行と同等以下（退化時は馬番フォールバック） |

通常レースの「暗黙 Q-Parity」に、初出走を **Evidence 充足で持ち上げる**のが本設計のゴール。

### 5.2 成功 KPI（Research Gate）

対象: 2歳新馬 / 出走歴0。

| KPI | 初期ゲート |
|-----|------------|
| Soft Recovery（Soft∧¬Strict） | Resolver 正答 ≥ 50%（Shadow） |
| Strict Hit（新馬） | 0% → ≥ 30%（Soft 天井 57% の半分超） |
| Q-Parity 率 | 発売後予測で ≥ 70% |
| Tier1 Missing（発売後） | ≤ 10% |
| `score_mutated` | 常に false |
| 非新馬回帰 | Strict 悪化なし（Resolver 非発火維持） |

### 5.3 Soft 外について

Soft も外すレースは **Intelligence だけでは通常品質に届かない**。  
本票のスコープは「退化の解消による同等化」。候補プール拡張は別チケット。

---

## 6. ライフサイクル（設計）

```
1. Debut Gate
   race ∈ {2歳新馬} OR starts_before==0
        │
2. Capture Snapshot（V9.2）
   Tier1–3 collectors（欠落は Missing 理由付き）
        │
3. Completeness Eval（Quality Model）
   → yh_quality_grade, tier_fill_bitmap
        │
4. Tie Detect（V9.1）
   |G|<=1 → pass-through（既存選定）
   |G|>=2 → Resolver(Tier1→2→3)
        │
5. Emit Intelligence Meta（Research / 将来 Shadow UI）
   evidence_chain, grade, unresolved_reason
```

Prediction 成功は Snapshot / Intelligence 失敗に **依存しない**（Research 分離）。

---

## 7. ロードマップ（設計段階の Wave）

| Wave | 内容 | 同等品質への寄与 |
|------|------|------------------|
| **V10.0** | Tier1 取得経路修正 + Snapshot、`trainer` 露出 | Q-Strong / Q-Parity への最短 |
| **V10.1** | `sire` / `damsire` / `breeder` コレクタ | Tier2 充実・発売前 Partial 改善 |
| **V10.2** | Tier3（体重・追切・調教） | 当日差分・仮説検証 |
| **V10.3** | Shadow Resolver → Soft Launch（別承認） | Strict KPI |

実装は別承認。本票は設計のみ。

---

## 8. リスク

| リスク | 緩和 |
|--------|------|
| 発売前に「同等」を約束できない | Grade で明示。Parity は Tier1 必須 |
| 市場バイアス = 人気追従 | Soft 回収と Challenge を分離評価。prior と交差検証 |
| 血統・牧場の表記ゆれ | ID 正規化・Quality 下限で Resolver 不採用 |
| Soft 外を Tier で救えると誤解 | 天井を Soft に固定して文書化 |
| Snapshot 事後更新 | イミュータブル + Anti-leak |

---

## 9. 変更境界

| 領域 | 本設計 |
|------|--------|
| コード | **未変更** |
| PE / CE / AI / Prediction Logic | **未変更** |
| 成果物 | 本ファイル + `v10-evidence-quality-model.md` |

---

## 10. 参照

- `docs/design/v10-evidence-quality-model.md`  
- `docs/design/v91-tie-resolver.md`  
- `docs/design/v92-prediction-snapshot.md`  
- `docs/design/v93-feature-catalog.md`  
- `docs/audit/v10-prioritization-audit.md`  
- `docs/research/v91-rank-degeneracy-analysis.md`
