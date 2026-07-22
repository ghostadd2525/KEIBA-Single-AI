# Version 2 — Accuracy Improvement 設計レビュー（V2.2 改訂）

**Date:** 2026-07-22（初版承認 2026-07-21 / **V2.2 改訂**）  
**Status:** **V2.2 設計改訂** — RP-V2 系を主要改善候補から除外。実装はこの文書のみでは開始しない。  
**Baseline（ロック）:** Phase255 Final → PE-V2-A PASS 後 = **Hit 218** / Purchase 187 / Winner in Pool **274/285**  
**改善対象:** **AI Core のみ**  
**変更禁止:** Prediction API / PI API / Race Catalog / Web / **Delete Boundary**

**関連提出物:**

| 提出物 | パス |
|--------|------|
| 本改訂設計書 | `docs/releases/v2-accuracy-design-review.md` |
| G1 11 件 責務分類 CSV | `compare/v2_accuracy_g1_layer_classification.csv` |
| Version2.2 Roadmap | `docs/releases/v2-accuracy-v2.2-roadmap.md` |
| RP-V2-A G1 観測 | `docs/ops/v2-rp-v2-a-g1-fail-observation.md` |

---

## 0. エグゼクティブサマリー

### 0.1 V2.1 までの実績

| Initiative | AB | Hit | 判定 | Flag |
|------------|----|----:|------|------|
| **PE-V2-A** | `v2-pe-v2-a-285r-ab` | 216→**218** | **PASS** | 採用候補（本番既定は運用判断） |
| **RP-V2-A** | `v2-rp-v2-a-285r-ab` | 218→**218** | **FAIL** | **OFF 維持・主要候補から除外** |
| CE-V2 | — | — | 未着手 | — |

### 0.2 V2.2 の結論（本改訂）

**RP-V2 系は Version2 Accuracy の主要改善候補から外す。**

| 根拠 | 観測 |
|------|------|
| Winner Rescue | **0/11** |
| NEAR 不成立 | **11/11** が独立条件 `no_near_candidate` を含む |
| 帯緩和の机上 | N+1..N+2 でも Rescue 増は期待できない（deep victim / mid_cap） |
| fire_cap | G1 の原因ではない（first_fail 0 件） |

つまり **パラメータ調整の問題ではなく、Rescue Trigger 自体の不足**である。

### 0.3 3 層モデル（V2.2）

```text
Layer1  Candidate Pool / Entry     PE-V2     「候補を場に入れる」
Layer2  RePick                     RP-V2     「Pool 内の候補並べ替え」（サイズ不変）
Layer3  Candidate Evaluation       CE-V2     「順位・生存スコアの入力品質」
        Delete                     —         変更禁止
```

**採択方針（V2.2）:** Layer1（PE-V2-A）をロックした上で、次の主要レバーは **Layer3（CE-V2）**。  
Layer2 は「Rescue による Hit 押し上げ」を期待せず、**並べ替え専用**に責務を限定できるかのみ検討する（主要ロードマップ外）。

---

## 1. Stage 1 — 285R 残ミス再分類（履歴 + PE 後更新）

### 1.1 Baseline 固定値

| 指標 | Phase255 | PE-V2-A PASS 後（現行 Control） |
|------|--------:|-------------------------------:|
| Corpus | 285R | 285R |
| **Hit** | **216** | **218** |
| Purchase | 189 | **187** |
| Winner in Pool | 270/285 (0.947) | **274/285 (0.961)** |
| rank710 miss | 15 | 14 |
| other_miss | 19 | 18 |
| rank46 | 35 | 35 |

**V2.2 以降の AB Control ロックは Hit=218（PE-V2-A ON / RP OFF）。**

### 1.2 first_loss_stage（PE 後・Treatment=Control 相当）

| first_loss_stage | miss n | 解釈 |
|------------------|------:|------|
| after_delete | 35 | Delete 境界（変更禁止） |
| re_pick | 21 | Pool 内だが RePick/選定で脱落 |
| candidate_pool | 11 | まだ Pool 外 |

### 1.3 4 カテゴリ（PE 後 after_miss）

| after_miss_group | n | Version2 直接対象 |
|------------------|--:|-------------------|
| rank46_miss | 35 | Delete 34 + 例外のみ（禁止境界） |
| rank710_hidden_miss | 14 | **主に Layer2/3**（G1 残り） |
| other_miss_10_13 等 | 13+ | Layer1 残り + 遠位 |
| other_miss_1_3 | 1 | Layer3 |

---

## 2. 3 層責務の再定義（V2.2 核心）

### 2.1 Layer1 — Candidate Pool / Entry（PE-V2）

| 項目 | 定義 |
|------|------|
| **責務** | 勝者・有力馬を **候補場（Candidate Pool）に入れる** |
| **非責務** | Pool 内の最終 N 頭選定、Delete、スコア再学習 |
| **状態** | **PE-V2-A PASS でロック**。Winner in Pool ↑ が主効果として確認済 |
| **残課題** | first_loss=`candidate_pool` 残 ≈11。PE-V2-B/C は V2.2 後段 |

**成功指標:** `winner_in_pool_rate` 上昇、Hit への寄与は下流依存。

### 2.2 Layer2 — RePick（RP-V2）— 責務の限定

| 項目 | V2.1 までの期待 | V2.2 の定義 |
|------|-----------------|-------------|
| 責務イメージ | 「順位調整」で G1 を Rescue し Hit を押す | **Pool 内の候補並べ替え**（N 不変の selected 入替） |
| 主アクチュエータ | NEAR 境界での max1 displace（TN-A/C/D） | 並べ替え専用に限定できる場合のみ。**Rescue Trigger としての RP-V2-A は棄却** |
| 主要改善候補 | **YES（P1）** | **NO** |

#### 2.2.1 「並べ替え」に限定できるか（検討結論）

| 問 | 結論 |
|----|------|
| RP を「順位調整（モデル rank の書き換え）」と呼ぶべきか | **否。** モデル rank は触らず、selected 集合の入替のみ |
| Pool 内並べ替えとして価値はあるか | **条件付き YES。** `surv≤N` なのに selected 外の 4 件は「選定/compress の並べ替え」が本態 |
| それを RP-V2-A（NEAR）で実現できるか | **NO。** 11/11 で NEAR 不成立。帯緩和でも Rescue≈0 |
| V2.2 で実装するか | **しない。** 主要候補から外し、要否は CE 後に V2.3（仮 RO-V2）で再判断 |

#### 2.2.2 RP-V2 ファセットの扱い

| 設計 ID | V2.2 扱い |
|---------|-----------|
| RP-V2-A | **FAIL 確定。再実装・再 AB 禁止（パラメータ再挑戦含む）** |
| RP-V2-B / C / D | 主要候補から除外。設計凍結 |
| Flag `WIN5_REPICK_V2_*` | 既定 **OFF** 維持 |

### 2.3 Layer3 — Candidate Evaluation（CE-V2）

| 項目 | 定義 |
|------|------|
| **責務** | 勝率・生存スコア等の **入力品質**を変え、Layer1/2 の意思決定を間接改善 |
| **非責務** | 再学習、特徴追加、28 特徴 Contract 変更、Delete |
| **V2.2 位置** | **次の主要改善レバー** |
| 設計 ID（案） | CE-V2-A（温度）、CE-V2-B（near-cut lift）、CE-V2-C（mid 生存再重み・要設計） |

### 2.4 Delete — 変更禁止（不変）

rank46-DEL（≈34）および multi / db_rescued / Delete 閾値は **設計・実装とも禁止**。

### 2.5 層別マトリクス（V2.2）

| 残ミス系統 | Layer1 PE | Layer2 RP | Layer3 CE | Delete |
|------------|:---------:|:---------:|:---------:|:------:|
| candidate_pool 残 | **主（PE-B/C）** | — | 間接 | — |
| re_pick / G1 並べ替え型 | — | 将来 RO 任意 | 間接 | — |
| re_pick / G1 境界型 | — | **非主** | **検討** | — |
| re_pick / G1 遠位型 | — | 非対象 | **主** | — |
| after_delete / rank46 | — | — | — | **禁止** |
| other_1_3 | PE-C | — | **主** | — |

---

## 3. G1（Winner Rescue 母集団 11 件）の層別分類

正本 CSV: `compare/v2_accuracy_g1_layer_classification.csv`  
観測根拠: `docs/ops/v2-rp-v2-a-g1-fail-observation.md`

### 3.1 分類定義

| primary_class | 定義 | 救うべき層 |
|---------------|------|------------|
| **Pool不足** | `winner_in_pool=0` | Layer1 |
| **RePick並べ替え不足** | in_pool ∧ surv≤N ∧ RePick 外 | Layer2（並べ替え）。RP-NEAR 非対象 |
| **RePick境界不足** | in_pool ∧ surv∈{N+1,N+2} ∧ RePick 外 | 旧 RP 想定域だが Trigger 不足 → Layer3 または将来 RO |
| **RePick遠位選定不足** | in_pool ∧ surv≫N+2 ∧ RePick 外 | Layer3 主 |
| **Evaluation不足** | 生存/スコアが低すぎて選定不能 | Layer3 |
| **Delete影響** | Purchase 後の脱落、または multi のみ Hit | Delete 禁止。既得 Hit は対象外 |
| **既得Hit** | 現行で Hit | Accuracy 追加対象外 |

### 3.2 集計（11 件）

| primary_class | n | 備考 |
|---------------|--:|------|
| RePick並べ替え不足 | **4** | 函館 / 中山12-13 / 阪神 / 小倉 |
| RePick境界不足 | **4** | 中京 / アウダーシア / ナムラ / マイノワール |
| Evaluation不足（遠位） | **2** | ウィリアムバローズ / スズカコテキタイ |
| 既得Hit（Delete/multi） | **1** | 2026-01-18-中山-10 |
| Pool不足 | **0** | G1 は全件 in_pool |

### 3.3 レース一覧（要約）

| race_id | winner | surv | primary_class | 救う層 |
|---------|--------|-----:|---------------|--------|
| 2024-01-21-京都-11 | ウィリアムバローズ | 11 | Evaluation不足 | **L3** |
| 2024-02-18-京都-11 | スズカコテキタイ | 13 | Evaluation不足 | **L3** |
| 2024-07-14-函館-10 | レッドラグラス | 4 | RePick並べ替え不足 | L2（将来）/ L3 間接 |
| 2025-12-13-中山-10 | モンドプリューム | 5 | RePick並べ替え不足 | L2（将来）/ L3 間接 |
| 2025-12-14-中京-11 | モズナナスター | 9 | RePick境界不足 | L3 検討 |
| 2026-01-18-中山-10 | モンドプリューム | 5 | 既得Hit | **対象外** |
| 2026-03-15-中山-11 | アウダーシア | 9 | RePick境界不足 | L3 検討 |
| 2026-04-12-阪神-10 | マイネルエニグマ | 3 | RePick並べ替え不足 | L2（将来）/ L3 間接 |
| 2026-04-19-中山-10 | ナムラフランク | 9 | RePick境界不足 | L3 検討 |
| 2026-04-25-京都-10 | マイノワール | 9 | RePick境界不足 | L3 検討 |
| 2026-06-28-小倉-11 | テーオーダヴィンチ | 5 | RePick並べ替え不足 | L2（将来）/ L3 間接 |

**含意:** 「残り 11」の Hit 押し上げを RP-NEAR に期待するのは設計ミス。遠位は CE、並べ替えは別設計（非必須）、境界は victim/スコア問題が残る。

---

## 4. Feature Flag と実装順序（V2.2）

### 4.1 Flag 状態

| Flag | 既定 | V2.2 |
|------|------|------|
| `WIN5_POOL_ENTRY_V2_ENABLED` | false（AB では ON 実績） | **PE-V2-A 成果を Baseline にロック**（運用 ON は別判断） |
| `WIN5_REPICK_V2_ENABLED` | **false** | **OFF 固定・主要開発停止** |
| `WIN5_REPICK_V2_SLOT` / `RANK6` | false | 凍結 |
| `WIN5_CE_CALIBRATION_V2_ENABLED` | false | **次の設計対象** |

### 4.2 実装順序（改訂）

```text
V2.1:  ハーネス → PE-V2-A → RP-V2-A → (CE)
V2.2:  PE-V2-A ロック → CE-V2 設計/AB →（任意）PE-V2-B/C →（任意・V2.3）並べ替え専用
```

**禁止:** RP パラメータ再挑戦、RP+CE 同時 ON、Delete 変更。

### 4.3 変更禁止境界（不変）

Prediction API / PI / Race Catalog / Web / Delete / Phase255 ロック入力。

---

## 5. AB 評価フレーム（V2.2 更新）

### 5.1 Control ロック

| 項目 | 値 |
|------|-----|
| Control | PE-V2-A ON + RP OFF + CE OFF |
| Hit | **218** |
| Hard Gate | **Treatment.Hit > 218** |
| G-Loss | churn_hit = 0 |
| G-Single | 単一 Flag のみ ON |

### 5.2 メトリクス

| メトリクス | 用途 |
|------------|------|
| Hit | 唯一の採用 Hard Gate |
| Purchase | 記録必須 |
| Winner in Pool 率 | Layer1 帰属 |
| Winner Rescue | **RP 専用だった指標。V2.2 では主ゲートに使わない**（RP 非注力） |
| first_loss_stage 分布 | 層別効果の切り分け |

### 5.3 履歴 AB（参照）

| AB | 結果 | 文書 |
|----|------|------|
| PE-V2-A | PASS 216→218 | `docs/ops/v2-pe-v2-a-ab-report.md` |
| RP-V2-A | FAIL 218→218 / Rescue 0/11 | `docs/ops/v2-rp-v2-a-ab-report.md` |

---

## 6. 実装前チェックリスト（V2.2）

- [x] V2.1 設計承認・PE→RP→CE 順
- [x] PE-V2-A PASS（Hit 218）
- [x] RP-V2-A FAIL 受領・観測資料
- [x] **V2.2: RP-V2 を主要候補から除外**
- [x] **V2.2: 3 層責務再定義 + G1 分類 CSV + Roadmap**
- [x] CE-V2 設計書作成（`docs/releases/v2-ce-v2-design-review.md`）
- [x] CE-V2 設計承認
- [x] CE-V2-A 実装 + 285R AB — **FAIL**（Hit 218→216 / churn_hit=2）
- [ ] Facet C — **CE-V2-A PASS まで着手禁止**
- [x] Delete / v1.1 境界 非変更
- [x] PE-V2-A 正式採用・ロック（Hit 218）
- [x] RP-V2 主要候補から除外

---

## 7. 参照

| 文書 | パス |
|------|------|
| **CE-V2 設計書** | `docs/releases/v2-ce-v2-design-review.md` |
| Version2.2 Roadmap | `docs/releases/v2-accuracy-v2.2-roadmap.md` |
| G1 層分類 CSV | `compare/v2_accuracy_g1_layer_classification.csv` |
| G1 FAIL 観測 | `docs/ops/v2-rp-v2-a-g1-fail-observation.md` |
| **CE-V2-A AB** | `docs/ops/v2-ce-v2-a-ab-report.md` |
| RP-V2-A AB | `docs/ops/v2-rp-v2-a-ab-report.md` |
| v1.1 Release | `docs/releases/v1.1.md` |
| Baseline | `docs/ops/stable-baseline-v1.0.0.md` |

---

## 付録 A — V2.1 §2 設計（履歴・参照用）

以下は V2.1 時点の責務別設計 ID。V2.2 では **RP-V2-\*** を主要パスから外す。PE/CE の ID 定義は引き継ぎ、期待値は Control=218 前提に更新する。

### A.1 PE-V2（有効）

| ID | 名称 | V2.2 |
|----|------|------|
| PE-V2-A | Deep-rank allowlist | **PASS 済・ロック** |
| PE-V2-B | rank710 pool rescue | 後段候補 |
| PE-V2-C | Shallow entry guard | 後段候補 |

### A.2 RP-V2（主要候補から除外）

| ID | 名称 | V2.2 |
|----|------|------|
| RP-V2-A | G1 NEAR rescue | **FAIL・除外** |
| RP-V2-B | SLOT recovery | 除外 |
| RP-V2-C | Shallow NEAR | 除外 |
| RP-V2-D | G2 rank6 | 除外 |

### A.3 CE-V2（次の主）

| ID | 名称 | V2.2 |
|----|------|------|
| CE-V2-A | Softmax 温度較正 | **次設計** |
| CE-V2-B | Near-cut score lift | 次設計 |
| CE-V2-C | mid 生存再重み（新） | 要設計レビュー |

---

**Next:** Version 2 Accuracy **検証終了**（Final Report）。採用は PE-V2-A のみ。続きは `docs/releases/v2-accuracy-v3-roadmap.md`。
