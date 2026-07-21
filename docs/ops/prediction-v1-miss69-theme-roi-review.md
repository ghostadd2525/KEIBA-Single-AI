# Version1 残ミス 69 — テーマ別 ROI 再評価（設計レビュー）

**Date:** 2026-07-21  
**Status:** **採択**（2026-07-21）— Version2 優先順位確定  
**Corpus:** Phase255 285R — V1 final miss **69**（hit 216）  
**正本明細:** `docs/ops/_pv2_f01_roi_validation_detail.csv`（bucket / first_loss / pool・repick・purchase フラグ）  
**前提決定:** **PV2-F01 は Version2 から除外・Feature Contract Archive**（ROI 18.8% < 20%）  
**Version2 優先:** P0 RePick v2 → P1 Pool+Entry → P2 Delete v2 → P3 CE Calibration / Learning・Feature 保留  
**P0 設計:** [`repick-v2-design-review.md`](./repick-v2-design-review.md)

---

## 0. 採択事項（PV2-F01）

| 項目 | 決定 |
|------|------|
| ROI Validation | **採択** |
| Version2 対象 | **除外** |
| Feature Contract | **Archive**（`prediction-v2-f01-feature-contract-ARCHIVED.md` / `contract.json` status=`archived`） |
| 実装チケット | **作成しない** |
| 理由 | ROI 18.8%・Go 未達／Pool 外・大穴系は市場微小補正で改善不能 |

---

## 1. 残ミス 69 の事実分布（再評価の土台）

### 1.1 V1 bucket

| Bucket | n | 意味（運用） |
|--------|--:|-------------|
| rank46 | **35** | 本命〜中穴帯。多くはパイプライン深部まで到達 |
| other_miss | **19** | 深穴・構造外れが多い |
| rank710 | **15** | 中〜大穴。RePick 脱落が主 |

### 1.2 first_loss_stage（パイプライン初脱落）

| first_loss | n | 主バケツ |
|------------|--:|---------|
| **after_delete** | **35** | rank46×34 |
| **re_pick** | **18** | rank710×11 + other×6 + rank46×1 |
| **candidate_pool** | **15** | other×12 + rank710×3 |
| **purchase** | **1** | rank710×1 |

### 1.3 ユーザー指定 6 テーマへのマッピング

| テーマ | 直接アドレス可能（n） | 根拠 |
|--------|---------------------:|------|
| **Candidate Pool** | **15** | `first_loss=candidate_pool`（勝者未入場） |
| **Entry** | **≈15**（Pool と実質同一母集団） | Win5 の Entry = Pool 入場（CP/閾値壁）。本 69 では Pool 外 15 と一致 |
| **RePick** | **18** | `first_loss=re_pick` |
| **Candidate Evaluation** | **間接 15+18（+Δ）** | 順位・スコアが Pool/RePick 入力を決める。`after_delete` 35 には一次効果なし |
| **Learning** | **間接・上限広め** | 再学習は CE 経由で全段に波及しうるが、Delete ロック・Pool 外は構造限界 |
| **Feature** | **≈0〜5（F01 除外後）** | 市場 Feature は 13 件仮説だったが F01 除外。新規 Contract なしでは着手不可 |

**重要:** `after_delete` **35** は本 6 テーマの **直接 first_loss ではない**。勝者は Pool→RePick→Purchase まで通過し、Delete 以降で落ちている。改善は Product Delete / multi 構成側が主戦場であり、本レビューでは **ROI を低く見積もる残余** として扱う（テーマ別比較の分母を歪めない）。

```text
CE ──► Pool(Entry) ──► RePick ──► Purchase/Entry購入 ──► Delete ──► Final
         ▲15外             ▲18脱落                         ▲35脱落
```

---

## 2. テーマ比較（改善余地 / 期待改善数 / 工数 / リスク）

尺度:
- **改善余地:** 69 内でテーマが一次レバーになりうる上限感（構造的に届くか）
- **期待改善数:** 現実的に回収しうるレース数の設計レンジ（Canary 前の仮説）
- **工数:** 設計〜Flag/AB〜検証までの相対コスト（S/M/L）
- **リスク:** Baseline（Phase255 / V1 Core）破壊・較正悪化・運用複雑度
- **ROI:** 期待改善 ÷（工数×リスク）の相対。**本表の並び = ROI 推奨順**

| ROI順 | テーマ | 改善余地 | 期待改善数（仮説） | 工数 | リスク | ROI | 論拠（要約） |
|------:|--------|----------|-------------------|------|--------|-----|--------------|
| **1** | **RePick** | **高**（18 直接） | **6〜12** | M | Mid | **Highest** | rank710 の多数が RePick 脱落。既存 Purchase miss 分解でも Repick 支配。Product ルール調整＋Flag で検証可能。CE/Feature 依存が相対的に低い |
| **2** | **Candidate Pool** | **高**（15 直接） | **4〜9** | M | Mid | **High** | 構造的「未入場」。allowlist / CP 拡張は過去設計でも議論済み。サイズ膨張リスクあり |
| **3** | **Entry** | **高**（≈15、Pool と重複） | **4〜9**（Pool と重複計上注意） | M | Mid | **High（Pool と同格・重複）** | Entry 閾値壁・CP1/CP2 は Pool 入場と同義。**独立チケットにすると二重計上**。実装単位は Pool/Entry を 1 パッケージにまとめるべき |
| **4** | **Candidate Evaluation** | **中**（間接） | **3〜8** | S〜M | **Low〜Mid** | **Mid-High** | Softmax/近傍較正等は低コスト。Pool 外 15 と RePick 18 の **入力品質**を上げる。`after_delete` 35 への一次効果は弱い |
| **5** | **Learning** | **中〜高（上限）** | **5〜15**（不確実大） | **L** | **High** | **Mid** | 再学習は効果天井が高いが、評価・回帰・Baseline 保護コストが大きい。F01 なし・特徴空間ほぼ V1 のままでは限界も大きい |
| **6** | **Feature** | **低**（F01 除外後） | **0〜5** | M | Mid | **Lowest（現状）** | 市場 Feature は ROI 未達で Archive。新 Feature は **新 Contract + ROI≥20%** 再検証が前提。現状は着手しない |

### 2.1 期待改善数の内訳イメージ（重複なしの上限配分）

69 を **排他的 first_loss** で配分した場合の「テーマが一次オーナー」:

| 排他バケット | n | 一次オーナー候補 |
|-------------|--:|------------------|
| re_pick | 18 | **RePick** |
| candidate_pool | 15 | **Candidate Pool / Entry** |
| purchase | 1 | Entry（購入段）または RePick 近傍 |
| after_delete | 35 | **6 テーマ外（Delete / multi）** ※本レビューでは期待改善に入れないか、CE/Learning の弱い間接のみ |

→ 6 テーマが **直接取りにいける母集団は最大 ≈34**（18+15+1）。残り 35 は別シリーズ（Delete/Product）。

---

## 3. テーマ別設計メモ（実装なし）

### 3.1 RePick（ROI #1）

| 項目 | 内容 |
|------|------|
| 対象ミス | 18（rank710 11 / other 6 / rank46 1） |
| 改善余地 | 高。既存 `purchase_miss_decomposition` でも Repick が支配的 |
| 期待改善 | 安定 membership / NEAR 救済で **6〜12** |
| 工数 | M（ルール・閾値・Flag・AB、Phase255 回帰） |
| リスク | Mid（組み合わせ数・Hit 率トレードオフ） |
| 次アクション（設計のみ） | RePick 専用 ROI ゲート（≥20% 等）を定義してからチケット化を検討 |

### 3.2 Candidate Pool（ROI #2）

| 項目 | 内容 |
|------|------|
| 対象ミス | 15（other 12 / rank710 3） |
| 改善余地 | 高だが **深穴 other** は「入れても RePick/購入で落ちる」二次リスク |
| 期待改善 | **4〜9**（入場後の生存まで含めると下限寄り） |
| 工数 | M |
| リスク | Mid（Pool 肥大 → 下流コスト・ノイズ） |

### 3.3 Entry（ROI #3・Pool と一体）

| 項目 | 内容 |
|------|------|
| 対象ミス | ≈15（Pool 外と同一）+ purchase 1 |
| 設計方針 | **Candidate Pool と同一パッケージ**で扱う。単独 ROI ランキングは Pool と二重計上しない |
| 期待改善 | Pool と同じ **4〜9**（合算しない） |

### 3.4 Candidate Evaluation（ROI #4）

| 項目 | 内容 |
|------|------|
| 対象ミス | 直接 first_loss は少ない。入力として Pool/RePick に効く |
| 改善余地 | 中。Core Top1 ≠ Win5 Hit のギャップあり（過去 ROI でも指摘） |
| 期待改善 | 較正系で **3〜8**（保守） |
| 工数 | S〜M（既存 Softmax / miss 較正 Flag） |
| リスク | Low〜Mid（Flag OFF = V1 恒等を維持すれば低い） |
| 備考 | 旧 PV2-C01 / R01 系は **F01 なしでも** 独立に評価可能 |

### 3.5 Learning（ROI #5）

| 項目 | 内容 |
|------|------|
| 対象ミス | 間接。構造 Pool 外・Delete は学習だけでは埋まらない |
| 改善余地 | 天井は高いが **不確実性が最大** |
| 期待改善 | **5〜15**（幅広・要 Holdout） |
| 工数 | L |
| リスク | High（V1 28 特徴凍結・Baseline 回帰） |
| 前提 | 新 Feature なしの再学習は効果が頭打ちしやすい |

### 3.6 Feature（ROI #6・現状）

| 項目 | 内容 |
|------|------|
| PV2-F01 | **Archive / V2 除外** |
| 改善余地 | 現状低。新仮説は **別 Contract + ROI Validation** 必須 |
| 期待改善 | **0〜5**（未契約） |
| 工数 | M（契約〜検証） |
| リスク | Mid |
| 方針 | **実装・チケットともに作らない**（本件の明示方針） |

---

## 4. ROI 順の推奨ロードマップ（設計のみ）

```text
[採択済] PV2-F01 Archive ─────────────────────────────────────────┐
                                                                   │
1) RePick テーマ ROI Validation（18 件母集団）  ← 次の設計フォーカス
2) Candidate Pool / Entry 一体パッケージ（15 件）※二重計上禁止
3) Candidate Evaluation（Flag 較正・低リスク）
4) Learning（3 のシグナルと Holdout が揃ってから）
5) Feature（新 Contract がある場合のみ。F01 は再開しない）
                                                                    │
並行注意: after_delete 35 は Delete/Product 別トラック ─────────────┘
```

**Version2（Prediction Core）の当面の焦点:**  
市場 Feature（F01）ではなく、**Product 側の RePick / Pool(Entry)** が残ミス ROI 上は優位。Core 単体なら **Candidate Evaluation（較正）** が次点。

---

## 5. 二重計上・過大評価の禁止

1. **Entry と Candidate Pool** の期待改善数を加算しない（同一 15）。  
2. **Feature の 13**（旧 F01）を他テーマに加算しない（F01 除外済み）。  
3. **after_delete 35** を RePick/Pool の期待改善に入れない。  
4. Learning の上限と CE の期待改善を単純合算しない（同じレースを二重に数える）。

---

## 6. 結論（一文）

**残ミス 69 に対し ROI が最も高い改善テーマは RePick、次いで Candidate Pool/Entry（一体）、その次が低リスクの Candidate Evaluation。Learning は高コスト、Feature（F01）は Archive 済みで現状最下位。実装・チケットは本レビューの範囲外。**
