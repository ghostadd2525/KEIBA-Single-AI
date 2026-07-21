# RePick V2.1 — Trigger Narrowing Design

**Date:** 2026-07-21  
**Status:** Design only（**コード実装禁止**）  
**Parent 採択:**  
- Failure Analysis [`repick-v2-failure-analysis.md`](./repick-v2-failure-analysis.md)  
- Baseline/Churn [`repick-v2-baseline-churn-analysis.md`](./repick-v2-baseline-churn-analysis.md)  
- AB Report [`repick-v2-ab-report.md`](./repick-v2-ab-report.md)  
**Cause judgment（採択）:** 失敗主因は **補正ではなく Trigger Selection（発火条件が広い）**  
**目的:** 既 Hit **77** 件への不要発火を削減する  

---

## 0. 硬制約（Must）

| 制約 | 扱い |
|------|------|
| 匿名トリガのみ | Must |
| Winner 情報 | **禁止**（直接・間接） |
| 結果列（Hit / after_miss / first_loss / 着順） | **禁止**（本番トリガ） |
| allowlist / G1 race 常設 | **禁止** |
| Collector | **非変更** |
| V1 Baseline | **非変更**（Flag OFF = 恒等） |
| 補正量（δ・スコア再計算等） | **変更禁止** |
| max1 displacement / N 不変 | **変更禁止** |
| Actuator / victim 優先規則の「強さ」変更 | 原則禁止 ※TN-C は発火ゲートのみ |
| 設計改訂範囲 | **Trigger 条件の追加・狭角化のみ** |

**非目標:** SLOT 解禁、rank6、Winner-Anchored、学習、新 Feature。

**オフライン評価との区別:**  
本設計の **期待件数** は AB 事後データ（結果列あり）で **推定**する。  
推定に結果列を使うことは許可。**本番トリガに結果列を入れない。**

---

## 1. 現状（V2.0）と問題

### 1.1 V2.0 Trigger（現行）

```text
Flag ON
∧ model_rank(cand) ∈ [7,10]
∧ cand ∈ pool ∧ cand ∉ selected
∧ N < surv_pos(cand) ≤ N+2     # RV2-A NEAR
∧ removable victim 存在
→ max1 displacement
```

### 1.2 観測（採択済）

| 指標 | n |
|------|--:|
| 発火 | **100** |
| 順位変更あり | **100** |
| Hit維持（既 Hit への不要 churn） | **77** |
| Hit改善 | **5** |
| Hit悪化 | **0** |
| Hit非該当 | **18** |
| R_G1 | **4/11** |

**判断:** 補正は破壊的でない（Hit悪化0）。**Trigger が広すぎる。**

---

## 2. Trigger 候補（匿名のみ）

いずれも **本番入力は pre-result 構造量のみ**（survival 順・model_rank・N・selected 集合・world メタ）。

| ID | 名称 | 追加条件（V2.0 AND） | 意図 |
|----|------|----------------------|------|
| **TN-A** | **NEAR_STRICT** | `surv_pos(cand) = N+1` のみ（N+2 除外） | 境界直近のみ。帯を半分に近く削る |
| **TN-B** | **MARGIN_GATE** | `surv(N-th) − surv(cand) ≤ τ`（τ は固定・事前契約） | 「わずかに落ちた」候補だけ |
| **TN-C** | **DEEP_VICTIM_REQUIRED** | victim 候補に `model_rank ≥ 11` が **必須**（無いなら不発火；V2.0 の fallback 禁止） | 本命帯を押し出さない／発火機会を減らす |
| **TN-D** | **MID_CAP** | `\|{h∈selected: model_rank∈[7,10]}\| < K`（推奨 K=2） | 既に mid が多いレースでは追加支払しない |
| **TN-E** | **SINGLE_BOUNDARY_CAND** | 候補を survival 順の **N+1 位のみ**に限定（N+2 を候補集合に入れない） | TN-A と同型・選定を一意化 |
| **TN-F** | **SUBWORLD_GATE** | `sub_world ∈ S`（例: `midupper_route` のみ。例外 race allowlist **禁止**） | 旧研究の世界条件を匿名で再利用 |
| **TN-G** | **STRENGTH_ORDER** | `surv(cand) ≥ surv(victim)`（または win_prob） | 弱い mid が強いテールを蹴るのを抑制 |

### 2.1 推奨パッケージ（V2.1 案）

```text
V2.1 Trigger = V2.0
            ∧ TN-A (NEAR_STRICT)
            ∧ TN-C (DEEP_VICTIM_REQUIRED)
            ∧ TN-D (MID_CAP, K=2)
```

| 採用 | 理由 |
|------|------|
| TN-A | 結果非依存で帯を明確に縮小 |
| TN-C | Hit悪化0を維持しつつ、浅い victim fallback による不要発火を削る |
| TN-D | 「既に mid を持つレース」への追加 churn を抑制（既 Hit と相関しうる匿名代理） |
| 見送り（初回） | TN-B（τ 校准が別AB）、TN-F（世界分布の再計測が必要）、TN-G（効果は TN-C と重複しやすい） |

**Actuator:** V2.0 と同じ（N 不変・max1・victim 優先 rank≥11）。TN-C は「victim 不在なら発火しない」ゲートであり、補正量・max1 は変えない。

---

## 3. 期待発火件数

基準: V2.0 Treatment 発火 **100**（AB 採択データ）。

| 案 | 推定発火 | 推定方法（オフライン） | 信頼度 |
|----|--------:|------------------------|--------|
| V2.0（現状） | **100** | 実測 | 確定 |
| TN-A のみ | **45〜60** | N+1/N+2 未分割のため幅付き（均一仮定なら ≈50） | 中 |
| TN-C のみ | **70〜90** | fallback 発火の削減分のみ | 低〜中 |
| TN-D (K=2) のみ | **55〜75** | selected 内 mid 個数の再集計が必要（未実施）→幅 | 低 |
| **V2.1（A∧C∧D）** | **20〜40** | 積集合・保守レンジ | 中 |
| 参考: 結果列で「after≠Hit」理想天井 | **23** | Failure Analysis 事後フィルタ（**本番不可**） | 参考上限 |

**設計ターゲット:** 発火 **≤ 35**（理想 **≤ 25**、結果列フィルタ 23 に近づけるが到達保証はしない）。

---

## 4. 期待改善率

分母は Exit どおり **G1=11**（`R_G1 = G1_rescue / 11`）。

| 案 | 期待 G1_rescue | 期待 R_G1 | 備考 |
|----|---------------:|----------:|------|
| V2.0 実測 | **4** | **4/11 ≈ 36.4%** | AB 合格線ちょうど |
| V2.1（狭化） | **3〜4** | **27〜36%** | TN-A で境界外の G1 救済が落ちるリスク |
| 楽観 | **4** | **≥ 4/11** | 現行 4 件がすべて N+1 かつ deep victim・MID_CAP 通過する場合 |
| 悲観 | **2〜3** | **< 4/11** | AB-R1 再 FAIL リスク → Stop カウンタ注意 |

**Hit改善（参考・全コーパス）:** V2.0 の **5** 件を可能な限り維持。狭化で **3〜5** を見込む。

**明示リスク:** Trigger 狭化は churn 改善と引き換えに **R_G1 が 4 未満になる**可能性。V2.1 AB で AB-R1 未達なら Exit FAIL（設計どおり停止）。補正を強めて取り返すことは **本設計では禁止**。

---

## 5. 推定 churn

Exit 定義に合わせる。

| 指標 | V2.0 実測 | V2.1 推定 | Exit 閾値 |
|------|----------:|----------:|-----------|
| churn_hit | **77** | **15〜35** | = 0 |
| churn_g1 | **95** | **15〜35** | ≤ 8 |
| churn_race | **0.35**（100/285） | **0.07〜0.14**（20〜40/285） | ≤ 0.05 |

**重要:** V2.1 でも **churn_hit=0 は保証しない**。  
既 Hit レースでも匿名構造だけ見ると NEAR mid が残りうる。  
推定では churn_hit を **大幅削減（77→20 前後）**するが、Exit AB-C1（=0）は **なお未達の可能性が高い**。

| churn ゲート | V2.1 での見込み |
|--------------|----------------|
| AB-C1 churn_hit=0 | **厳しい**（残余 15〜35 の想定） |
| AB-C2 churn_g1≤8 | **厳しい〜境界**（発火≤35でも G1 外が大半なら未達） |
| AB-C3 churn_race≤0.05 | 発火 ≤14 なら達成可能。**20〜40 では未達寄り** |

→ Trigger 狭化の **第一目的は「77 の削減と診断可能性」**であり、単発で Exit 全ゲート PASS を約束しない。

---

## 6. AB Exit への影響

Exit Criteria（Approved）は **改訂しない**（本設計の範囲外）。影響は「V2.1 AB を走らせた場合の見込み」。

| Exit ゲート | V2.0 | V2.1 見込み | コメント |
|-------------|------|-------------|----------|
| AB-R1/R2 R_G1≥4/11 | PASS | **境界〜FAIL** | 狭化で救済減リスク |
| AB-H1/H2/H3 Hit | PASS | **維持〜改善** | Hit悪化0の性質は維持しやすい |
| AB-K1/O1 | PASS | **維持** | |
| AB-C1/C2/C3 churn | **FAIL** | **改善するが PASS 未約束** | 主目的の改善軸 |
| AB-I1 Control=216/15/19 | FAIL | **別問題** | ハーネス DB rescue ズレ。Trigger 改訂では直らない |
| AB-I2/I3/I4 | PASS | **PASS 維持** | 匿名・N不変・単独を継続 |

### 6.1 V2.1 AB の位置づけ（設計）

```text
目的1: churn_hit / churn_race を定量的に削れたか（失敗分析の検証）
目的2: R_G1 を 4/11 以上維持できるか（トレードオフ確認）
目的3: Exit 全 PASS は「必須成功条件」ではなく、次の Exit 1.1 議論の入力
```

Control 再現（AB-I1）は Trigger とは独立に、**評価ハーネスを Phase255 CSV にロック**する運用修正が別途必要（本設計の実装スコープ外・設計指摘のみ）。

### 6.2 Stop Criteria との関係

- V2.1 を **正式 AB 1 回**として数える場合、FAIL なら連続 FAIL カウンタ +1（現在 V2.0 で既に 1）。  
- 設計上の推奨: V2.1 初回は **診断 AB（labeled）** とし、Stop 計上ルールを Human が明示してから正式化（契約変更が必要なら Stop/Exit `1.1`）。

---

## 7. 候補比較サマリ（提出要件対応）

### 7.1 Trigger 候補一覧 → §2

### 7.2 期待発火件数 → §3（V2.1: **20〜40**、ターゲット ≤35）

### 7.3 期待改善率 → §4（R_G1: **3〜4 / 11**、維持目標 ≥4/11）

### 7.4 推定 churn → §5（churn_hit **15〜35**、race **0.07〜0.14**）

### 7.5 AB Exit 影響 → §6（churn 改善・R_G1 リスク・I1 は未解決）

---

## 8. 非候補（明示的にやらない）

| 案 | 理由 |
|----|------|
| `after_miss ≠ Hit` をトリガに入れる | **結果列禁止** |
| `first_loss = re_pick` | 結果／分析列依存 |
| `winner_rank ∈ [7,10]` | Winner／結果依存 |
| G1 allowlist | **allowlist 禁止** |
| cand == winner | Winner-Anchored 禁止 |
| displacement max2 / 補正強化 | **補正・max1 変更禁止** |
| Collector / 学習 / 新 Feature | 範囲外 |

---

## 9. 次工程（実装は承認後・本チケット外）

1. 本設計の **Human 承認**  
2. （任意）オフラインで TN-A/C/D の発火集合を CSV から再集計し、レンジを確定  
3. Exit/Stop を据え置きのまま **診断 AB** か、churn 閾値の `1.1` を別審査  
4. 承認後のみ V2.1 実装（Flag 名案: `WIN5_REPICK_V2_1_ENABLED` または V2 Flag + `NARROW_PROFILE=A+C+D`）

---

## 10. 結論

**V2.1 は Actuator を触らず、匿名 Trigger を TN-A∧TN-C∧TN-D で狭め、既 Hit 77 発火を削る設計とする。期待発火 20〜40、R_G1 は 3〜4/11（4 維持が目標）、churn は大幅改善するが Exit churn=0 は未約束。実装は本設計承認後。**

---

## 承認チェックリスト

- [ ] 主因=Trigger Selection に合意  
- [ ] 推奨パッケージ TN-A∧C∧D でよいか  
- [ ] 結果列・Winner・allowlist をトリガに入れないことに合意  
- [ ] 補正量・max1 非変更に合意  
- [ ] Exit 閾値は据え置き（V2.1 で全 PASS を約束しない）に合意  
- [ ] 実装は別承認後  
