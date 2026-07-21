# RePick v2 — Exit Criteria Contract

**Contract ID:** `WIN5-REPICK-V2-EXIT/1.0`  
**Date:** 2026-07-21  
**Status:** **Approved**（2026-07-21）  
**Stop Criteria:** [`repick-v2-stop-criteria-contract.md`](./repick-v2-stop-criteria-contract.md)（**Active**）  
**Parent design:** [`repick-v2-design-review.md`](./repick-v2-design-review.md)（条件付き承認 → 実装チケット化済）  
**Implementation ticket:** [`issues/ISSUE-REPICK-V2-001-implementation.md`](./issues/ISSUE-REPICK-V2-001-implementation.md)  
**Mode:** 契約正本（コード実装はチケット範囲。本ファイルは閾値変更禁止）

---

## 0. 契約目的

RePick v2 の実装・AB・Canary・Version2 採用の **合否を事前に固定**する。  
閾値は AB 結果を見て事後変更しない（改訂は `1.1` 昇格審査）。

| 段階 | 本契約の役割 |
|------|----------------|
| 実装チケット化 | **Approved 済** → [`ISSUE-REPICK-V2-001`](./issues/ISSUE-REPICK-V2-001-implementation.md) |
| AB | §2 合格 / §3 失敗 |
| Rollback | §4 |
| Canary 昇格 | §5 |
| Version2 採用 | §6 |
| **Stop / V2 除外** | [`Stop Criteria`](./repick-v2-stop-criteria-contract.md) |

---

## 1. 評価母集団・Baseline・定義

### 1.1 固定母集団

| 記号 | 定義 | n | 役割 |
|------|------|--:|------|
| **G1** | Phase255 285R 上、V1 で `first_loss=re_pick` ∧ `v1_bucket=rank710` ∧ `in_pool=1` ∧ `in_repick=0` ∧ `winner_rank∈[7,10]` | **11** | **主評価母集団（分母）** |
| G0 | `first_loss=re_pick` | 18 | 参考（合否分母にしない） |
| G3 | G0 ∩ `other_miss`（rank≥11） | 6 | 成功に数えない |

G1 の race_id 一覧は設計書 §2.2 を正本とし、本契約承認時に **凍結**する。

### 1.2 Control Baseline（Phase255 / Flag OFF）

| 指標 | Control 値（契約） | 備考 |
|------|-------------------:|------|
| Corpus | 285R | 固定 |
| **Hit** | **216** | V1 final hit |
| Miss | 69 | 216 + 69 = 285 |
| **rank710**（miss 件数） | **15** | bucket=`rank710` |
| **other_miss**（miss 件数） | **19** | bucket=`other_miss` |
| G1 のうち `in_repick=1` | **0** | 定義上すべて未入場 |

AB 再現時、Control（Flag OFF）が上表と一致しない場合は **AB 無効**（実装/環境不備）。合否判定に入らない。

### 1.3 Treatment

```text
Control と同一コーパス・同一パイプライン
+ WIN5_REPICK_V2_ENABLED = ON
+ 初回AB: RV2-A（NEAR）のみ / SLOT・rank6 Flag OFF
+ RePick v2 単独（Pool / Entry / Delete / CE / Learning / Feature 同時変更禁止）
```

### 1.4 メトリクス定義（契約）

| 略称 | 定義式 | 単位 |
|------|--------|------|
| **改善率** | `R_G1 = |{ r ∈ G1 : in_repick_tx(r)=1 }| / 11` | [0,1] |
| **G1_rescue** | `| { r ∈ G1 : in_repick_tx(r)=1 } |` | 件数 0–11 |
| **Hit** | 最終 Hit レース数（Phase255 と同一定義） | 件数 |
| **Hit損失** | `| Hits_control \ Hits_treatment |` | 件数（**0 必須**） |
| **ΔHit** | `Hit_tx − Hit_ctrl` | 件数 |
| **rank710** | Treatment 後の `v1_bucket=rank710` miss 件数 | 件数 |
| **other_miss** | Treatment 後の `v1_bucket=other_miss` miss 件数 | 件数 |
| **churn** | 下記 §1.5 | 比率または件数 |

**改善率の解釈:** 分母は常に **G1=11**。G0/69/発火全レースで割らない。  
`in_repick=1` は **membership 改善**。最終 Hit は別ゲート（接合欠落があり得る）。

### 1.5 churn 定義（契約）

RePick 段の意図しない揺らぎを測る。

| 記号 | 定義 |
|------|------|
| **churn_race** | `symdiff(repick_ctrl, repick_tx) > 0` のレース数 / 285 |
| **churn_g1** | G1 外で `symdiff(repick_ctrl, repick_tx) > 0` のレース数 |
| **churn_hit** | Control Hit レースのうち repick 集合が変わった件数 |

合否に使う主 churn は **`churn_g1`（G1 外の意図外変更件数）** および **`churn_hit`**。  
`churn_race` は監視指標（単独 FAIL にしてもよい厳しい帯を §2 に置く）。

---

## 2. AB 合格条件（すべて必須）

以下を **すべて同時充足**で AB = **PASS**。

### 2.1 閾値表（事前契約）

| ID | 指標 | 合格閾値 | 根拠 |
|----|------|----------|------|
| **AB-R1** | **改善率** `R_G1` | **≥ 4/11（≈36.4%）** | Conservative 下限（設計 §3） |
| **AB-R2** | **G1_rescue** | **≥ 4** | AB-R1 と同値の件数形 |
| **AB-H1** | **Hit** | **≥ 216** | Control 非悪化 |
| **AB-H2** | **Hit損失** | **= 0** | 既得 Hit 保護 |
| **AB-H3** | **ΔHit** | **≥ 0** | AB-H1 の言い換え（冗長確認） |
| **AB-K1** | **rank710** | **≤ 15** | Control 非悪化（減少は望ましいが必須ではない） |
| **AB-O1** | **other_miss** | **≤ 19** | Deep 悪化禁止（G3 を「成功」にしない） |
| **AB-C1** | **churn_hit** | **= 0** | Hit レースの membership 不変 |
| **AB-C2** | **churn_g1** | **≤ 8** | G1 外の意図外 repick 変更上限（285 中） |
| **AB-C3** | **churn_race** | **≤ 0.05**（≤14/285） | 全体揺らぎ上限 |
| **AB-I1** | Flag OFF 恒等 | Control と出力ビット一致 | V1 Baseline 保護 |
| **AB-I2** | N 不変 | 発火成功時 `len(repick)` 不変 | 設計 Must |
| **AB-I3** | 匿名トリガ | §7 チェックリスト全 PASS | Winner 非参照 |
| **AB-I4** | 単独差分 | Pool/Entry/Delete/CE/Feature/Learning コードパス差分 0 | P0 境界 |

### 2.2 目標帯（PASS には必須でない・レビュー記載）

| 指標 | 目標 | 扱い |
|------|------|------|
| `R_G1` | **≥ 6/11（≈54.5%）** | 設計目標。未達でも AB-R1 充足なら PASS 可 |
| ΔHit | **≥ +2** | 接合成功の健全性。未達は警告・原因分析必須だが単独 FAIL にしない |

### 2.3 PASS 判定式

```text
AB_PASS :=
  AB-R1 ∧ AB-R2 ∧ AB-H1 ∧ AB-H2 ∧ AB-H3
  ∧ AB-K1 ∧ AB-O1
  ∧ AB-C1 ∧ AB-C2 ∧ AB-C3
  ∧ AB-I1 ∧ AB-I2 ∧ AB-I3 ∧ AB-I4
```

---

## 3. AB 失敗条件（いずれかで FAIL）

| ID | 条件 | 直後アクション |
|----|------|----------------|
| **AF-1** | Hit損失 ≥ 1 | **即停止**・Flag 維持 OFF |
| **AF-2** | Hit < 216 | 即停止 |
| **AF-3** | `R_G1` < 4/11 または G1_rescue < 4 | FAIL（効果不足） |
| **AF-4** | rank710 > 15 | FAIL（rank710 悪化） |
| **AF-5** | other_miss > 19 | FAIL（Deep 悪化） |
| **AF-6** | churn_hit ≥ 1 | FAIL（既得 Hit 揺らぎ） |
| **AF-7** | churn_g1 > 8 または churn_race > 0.05 | FAIL（過剰 churn） |
| **AF-8** | Flag OFF 非恒等 | FAIL（実装欠陥） |
| **AF-9** | 発火成功なのに N 増加 | FAIL |
| **AF-10** | §7 匿名レビューいずれか FAIL（Winner 直接/間接参照） | FAIL・実装差し戻し |
| **AF-11** | G3（Deep）救済を「改善率」に加算して報告 | FAIL（契約違反・再計測） |
| **AF-12** | Control が §1.2 Baseline と不一致 | AB 無効（再準備） |

FAIL 時: 追加実装・Canary・Production 判断 **禁止**。原因分析は RePick v2 層に限定（Pool/Delete へ逃げない）。

---

## 4. Rollback 条件

Flag 既定は常に OFF。以下で **即時 Rollback = Flag 強制 OFF + Canary/採用停止**。

| ID | トリガ | 範囲 |
|----|--------|------|
| **RB-1** | AB FAIL（§3 いずれか） | 全環境 |
| **RB-2** | Canary 中に Hit損失 ≥ 1 | 全環境 |
| **RB-3** | Canary 中に rank710 または other_miss が Control 比で悪化継続（連続 2 評価窓） | 全環境 |
| **RB-4** | churn_hit ≥ 1（本番相当ログ） | 全環境 |
| **RB-5** | 匿名契約違反が発覚（Winner 参照・結果リーク） | 全環境 + コード差し戻し |
| **RB-6** | 運用判断（Human）による緊急停止 | 全環境 |

Rollback 後の再 ON は、本契約の **再 AB PASS** が必要（黙って Canary 再開禁止）。

---

## 5. Canary 昇格条件

前提: **AB_PASS（§2）**。

| 段階 | 条件 | 次 |
|------|------|-----|
| **C0** | AB_PASS + Human Review 記録 | Canary 候補 |
| **C1** | Flag ON を **限定ミーティング/日次 ≤10%**（または承認済みレース部分集合） | 監視 |
| **C2** | Canary 窓（最短 2 評価サイクル）で Hit損失=0 ∧ rank710≤Control帯 ∧ other_miss≤Control帯 ∧ churn_hit=0 | **C3 へ** |
| **C3** | 匿名 journal 監査（発火全件）で §7 再確認 PASS | **Version2 採用審査（§6）へ進める資格** |

Canary 中に §4 該当で即 Rollback。  
**C3 未達で本番既定 ON は禁止。**

---

## 6. Version2 採用条件（本番既定 ON）

以下を **すべて**満たしたときのみ、`WIN5_REPICK_V2_ENABLED` の **製品既定を ON に変更**する提案が可能。

| ID | 条件 |
|----|------|
| **AD-1** | AB_PASS |
| **AD-2** | Canary C3 完了 |
| **AD-3** | 改善率 `R_G1` **≥ 6/11**（採用は設計目標帯を要求。AB 合格の 4/11 より厳格） |
| **AD-4** | ΔHit **≥ +2**（採用時は接合効果を要求） |
| **AD-5** | rank710 **≤ 13**（Control 15 から **−2 以上**） |
| **AD-6** | other_miss **≤ 19**（悪化なし） |
| **AD-7** | churn_hit = 0 かつ churn_g1 ≤ 8（Canary 最終窓でも維持） |
| **AD-8** | §7 匿名レビュー最終 PASS |
| **AD-9** | Pool/Entry/Delete/Learning/Feature を同時に既定 ON にしていない（RePick v2 単独採用） |
| **AD-10** | Human 署名（採用承認） |

AD-3/AD-4/AD-5 未達でも AB_PASS なら **Flag は OFF のまま「研究完了・採用見送り」**とし得る（失敗ではない）。

---

## 7. 匿名トリガ — Winner 非参照レビュー（実装前・実装後必須）

### 7.1 原則

```text
Trigger / Actuator / Victim 選定は、レース結果の winner を
直接にも間接にも参照してはならない。
```

評価レポートで G1 との一致率を出すことは許可（**事後メトリクス**）。  
実行時パスに winner を入れてはならない。

### 7.2 直接参照 — 禁止（いずれかで §7 FAIL）

| 禁止 | 例 |
|------|-----|
| D1 | `horse_id == race_winner_id` / 馬名一致 |
| D2 | 結果 CSV / 着順 / `winner` 列の読取（推論・RePick 時） |
| D3 | Winner-Anchored allowlist（「この race の勝者だけ rescue」）を本番トリガに使う |
| D4 | 旧 T-R7N の `cand ≡ winner` 契約の移植 |

### 7.3 間接参照 — 禁止（いずれかで §7 FAIL）

| 禁止 | 例 |
|------|-----|
| I1 | 勝者だけが持つラベル・フラグ・事後特徴でのフィルタ |
| I2 | 「G1 の 11 race_id だけ発火」を **本番常設 allowlist** にする（評価凍結リストの流用） |
| I3 | 学習/ルールが winner ラベルでフィットした係数を、同一レースで再適用するリーク |
| I4 | journal 以外の制御フローが `roi_class` / `first_loss` / miss 分析列に依存 |
| I5 | victim 選定が「勝者を残す」目的関数になっている（結果依存） |

**許可される入力（匿名）:** `model_rank`, pool 所属, survival 順 / `surv_pos`, N, world/sub_world, 既存保護フラグ（RP/Alpha-paid 等の **事前**属性）。

### 7.4 レビュー確認チェックリスト（契約）

実装チケット起票前・AB 前・Canary C3・採用前に、以下を記録する。

| # | 確認項目 | 結果 |
|---|----------|------|
| 1 | Trigger 条件に winner / 着順 / 結果 I/O が無い | ☐ |
| 2 | 候補集合が G1′（model_rank∈[7,10] ∧ in_pool ∧ ∉repick ∧ cut）のみ | ☐ |
| 3 | Actuator が N 不変 displacement のみ | ☐ |
| 4 | Victim が survival テール + 保護規則のみ（結果非依存） | ☐ |
| 5 | 本番に Winner-Anchored / G1 race allowlist 常設が無い | ☐ |
| 6 | 評価用 Winner 一致率は **オフラインレポートのみ** | ☐ |
| 7 | Flag OFF 経路が Trigger を完全スキップ | ☐ |

**設計時点の確認（本契約作成時）:**  
親設計 [`repick-v2-design-review.md`](./repick-v2-design-review.md) §2.3 / §5.4 / §5.5 は、本番トリガを **G1′ 匿名**とし、T-R7N Winner-Anchored を本番不採用と明記している。  
→ **設計レビュー上は直接参照なし**。間接参照（I2: G1 allowlist 常設化）を実装が踏まないよう、本 §7 を Exit 必須とする。

---

## 8. 実装チケット化ゲート

```text
実装チケット作成 := Exit Criteria Status == Approved
                 ∧ Stop Criteria Active
```

| 状態 | チケット |
|------|----------|
| ~~Draft~~ | ~~作成禁止~~ → **解除済** |
| **Approved**（本契約） | [`ISSUE-REPICK-V2-001`](./issues/ISSUE-REPICK-V2-001-implementation.md) **open** |
| Stop 発火 | チケット **blocked** |
| Exclude 発火 | チケット **wontfix** |

---

## 9. 改訂規則

| 変更 | 扱い |
|------|------|
| 閾値の緩和・分母変更 | **禁止**（黙って変更しない）→ `1.1` 審査 |
| 指標の追加（監視のみ） | 可（合否式に入れない限り） |
| G1 レース差し替え | 原則禁止。データ誤り訂正のみ `1.1` |

---

## 10. 承認欄

| 項目 | 内容 |
|------|------|
| 設計レビュー | 条件付き承認（2026-07-21） |
| Exit Criteria | **Approved**（2026-07-21） |
| Stop Criteria | **Active**（2026-07-21） |
| 実装チケット | **ISSUE-REPICK-V2-001**（open） |

**承認ステータス:** **Approved**

---

## 付録 A — 閾値一覧（早見）

| 指標 | AB 合格 | AB 失敗 | Version2 採用 |
|------|---------|---------|----------------|
| 改善率 R_G1 | ≥ **4/11** | < 4/11 | ≥ **6/11** |
| Hit | ≥ **216** | < 216 または損失≥1 | ≥216 かつ ΔHit≥**+2** |
| rank710 | ≤ **15** | > 15 | ≤ **13** |
| other_miss | ≤ **19** | > 19 | ≤ **19** |
| churn_hit | **0** | ≥1 | **0** |
| churn_g1 | ≤ **8** | >8 | ≤ **8** |
| churn_race | ≤ **0.05** | >0.05 | （監視維持） |
