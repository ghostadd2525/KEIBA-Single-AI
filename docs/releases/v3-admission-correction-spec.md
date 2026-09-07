# Version 3 — Admission Correction Design Specification

**Date:** 2026-07-24  
**Status:** Specification · **実装なし**  
**Parent:** [`v3-admission-correction-design.md`](./v3-admission-correction-design.md)  
**RCA:** PASS

---

## 1. Scope

| In Scope | Out of Scope |
|----------|--------------|
| Admission 政策設計（新 Candidate A-05） | A-03 ソース変更 |
| promote / 本命保護ゲート | Selection（A-04）変更 |
| Flag / Contract 予約 | Evaluation（A-01/A-02）変更 |
| Lab + Offline 評価仕様 | Representation / Purchase |
| Hard Gate 定義 | 実装・本番配線 |

---

## 2. A-03 設計問題の詳細（Spec）

### 2.1 現行ロジック要約（参照のみ · 変更しない）

`admission_policy_a03.py`（現行）:

1. 全頭 admit  
2. `field_size >= 12` かつ deep 帯存在  
3. deep 内で `coverage_score` 最大を選択  
4. `score >= 100`（≒ style rarity）なら  
   - `model_rank = 1`  
   - `win_prob = max(own, top_wp + 0.08)`  
   - 他頭を 2..n に繰り下げ

### 2.2 失敗モード対応表

| 設計要素 | Lab での見え方 | Offline での実態 | 問題 |
|----------|----------------|------------------|------|
| `PROMOTE_FIELD_MIN=12` | Hit 層 field=8 で不発火 | 86% で開放 | ゲート無効化 |
| style rarity ≥100 | Pool×9 のみ適合 | ~53% 発火 | 過発火 |
| Hard rank rewrite | Pool 加点に見える | 本命 29 破壊 | D1 強制 |
| 本命ゲートなし | 不要に見えた | 必須だった | 欠落 |
| 単一コーパス最適化 | Hit 279 | Hit 42 | 過適合 |

### 2.3 変更方針（A-03 本体）

**A-03 は凍結。バグフィックスとしても書き換えない。**  
理由: Baseline v3・Validation・Offline FAIL の比較可能性を維持するため。  
改善は **A-05 独立候補** で行う。

---

## 3. promote 発火条件の見直し方針

### 3.1 設計原則

| 原則 | 説明 |
|------|------|
| P1 | **本命破壊ゼロ優先**（Offline worsened `winner_rank=1` = 0 を最優先） |
| P2 | promote は例外処理であり、デフォルトは identity 順位を維持 |
| P3 | 単一弱いシグナル（脚質レア）だけでは promote しない |
| P4 | Hard rewrite は最後の手段。可能な限り Soft / Conditional |
| P5 | 発火率は Offline 実測で上限管理する |

### 3.2 A-05 発火条件（設計案 · 実装時に校正）

Promote は **すべて** のゲートを満たした場合のみ。

| Gate ID | 条件（設計） | 意図 |
|---------|--------------|------|
| G-Field | `field_size >= FIELD_MIN`（初期案 12 維持可 · 要 Offline 校正） | 小頭数は触らない |
| G-Deep | promote 候補が deep 帯（`model_rank >= DEEP_RANK_MIN`） | Pool 狙い維持 |
| G-Coverage | Coverage が **複合**（下記 3.3） | style 単独禁止 |
| G-FavSafe | 本命保護ゲート PASS（§4） | Offline 主因封じ |
| G-Margin | promote 候補の相対根拠が top に対し十分 | 誤昇格抑制 |
| G-RateCap |（実験メトリクス）コーパス promote 率 ≤ 目標上限 | 過発火監視 |

### 3.3 Coverage 複合条件（style 単独の廃止）

A-03: `rarity → score≥100` のみ。

A-05 設計:

```text
coverage_ok =
  style_rarity                          # 必要だが十分ではない
  AND deep_band                         # rank >= DEEP_RANK_MIN
  AND (relative_strength_ok)            # 例: hist/wp が deep 内上位かつ閾値
  AND (not_only_rarity)                 # rarity 以外に ≥1 の正シグナル必須
```

**相対強度の設計メモ（実装前の校正対象）:**

- deep 内順位だけでなく、field 全体での匿名スコア分位  
- `history_score` は Real 平均 0.74 のため、Lab 向け絶対閾値を流用しない  
- 実装 Round で Offline Control 上の promote 率・precision を見て閾値決定

### 3.4 Soft vs Hard Promote

| Mode | 動作 | 採用方針 |
|------|------|----------|
| Soft Admit | deep を場に残すが `model_rank=1` は書き換えない | 本命保護と両立しやすいが、現状 identity/D1 では Hit に届かない可能性 |
| Soft Lift | `win_prob`/`history` を軽く持ち上げ、rank は 2–3 帯まで | D1 が拾うかは A-01 依存 · 実験で検証 |
| Conditional Hard | G-FavSafe 通過時のみ `model_rank=1` rewrite | **Primary 設計**（深掘り回収を維持） |
| Unconditional Hard（A-03） | FavSafe なし | **禁止（A-05 では不採用）** |

**A-05 Primary:** Conditional Hard（FavSafe + 複合 Coverage 通過時のみ hard promote）。

---

## 4. 本命保護（Favorite-Safe）Admission 設計

### 4.1 目標

Offline Gate の悪化 29 件に共通する:

> Control pick = winner ∧ `winner_rank=1` ∧ Treatment が非本命を pick

を **設計上不可能に近づける**（Hard Gate: `worsened_rank1 = 0`）。

### 4.2 保護対象の定義（リークなし）

結果列 `winner_rank` は **入力に使わない**。  
保護は **レース前に観測可能な top-1 / margin** で行う。

| 記号 | 定義 |
|------|------|
| `top` | 現行 `model_rank==1` の馬（Admission 入口） |
| `top_wp` | top の `win_prob` |
| `second_wp` | rank 2 の `win_prob`（または 2 位相当） |
| `margin` | `top_wp - second_wp` |
| `cand` | Coverage が選んだ deep 候補 |

### 4.3 Favorite-Safe Gates（すべて必須）

| Gate | 条件（設計初期値 · 校正対象） | 効果 |
|------|------------------------------|------|
| FS-1 Clear Favorite | `margin >= MARGIN_MIN`（初期案例: 0.05–0.10）なら **promote 禁止** | 明確本命を壊さない |
| FS-2 Top Intact | promote 時も、**禁止モード**では top の rank/wp を下げない | identity 維持 |
| FS-3 No Steal When Strong | `top_wp >= TOP_WP_FLOOR` かつ cand が deep のみ → 禁止 | 強本命帯の保護 |
| FS-4 Promote Precision Bias | cand の複合 coverage が top を「置換する根拠」に達しない限り禁止 | 誤昇格抑制 |

### 4.4 許容される promote（本命非破壊）

次を同時に満たす場合のみ Conditional Hard を許可:

1. FS ゲートすべて PASS（= 明確本命ではない / margin 小さい）  
2. 複合 Coverage PASS  
3. cand が deep  
4. field ゲート PASS  

これにより「曖昧な上位」でのみ深掘りを許可し、明確本命レースでは A-03 型の破壊を防ぐ。

### 4.5 D1 増幅への Admission 側対応

Evaluation（D1）は変更しない。代わりに Admission が:

- 不必要な `model_rank=1` rewrite を行わない  
- rewrite する場合も FavSafe 通過後のみ  

→ 副因（D1 増幅）は **上流で入力を汚染しない**ことで緩和する。

---

## 5. 新 Admission Candidate — A-05

### 5.1 Identity

| 項目 | 値 |
|------|-----|
| Experiment / Accuracy ID | **A-05** |
| Policy ID | `AP-V3-A05-favorite-safe-coverage` |
| Admission ID | `v3-adm-a05-v1` |
| Contract（予約） | `v3-lab-admission/2.2`（A-03 の 2.1 と併存 · 切替） |
| Module（予約・未作成） | `admission_policy_a05.py` |
| Flag | `F_V3_A05_ADM_FAVSAFE_ENABLED`（既定 OFF） |

### 5.2 対 A-03 関係

| 規則 | 内容 |
|------|------|
| ソース | A-03 ファイルを編集しない |
| 同時 ON | Primary / Offline Hard Gate では **禁止** |
| 比較 | A-05 vs A-03 を AB で対比 |
| Baseline v3 | 当面 A-01+A-03+A-04 のまま（置換は A-05 PASS 後の別 Decision） |

### 5.3 処理フロー（設計）

```text
Input runners (Representation 出力)
    ↓
Full admit（容量ポリシーは A-03 と同様に全頭可 · 変更は promote のみ）
    ↓
If NOT (G-Field ∧ G-Deep):
    return identity ranks
    ↓
Select cand = argmax composite_coverage(deep)
    ↓
If NOT (G-Coverage ∧ G-FavSafe ∧ G-Margin):
    return identity ranks   # ← A-03 との最大差
    ↓
Conditional Hard Promote(cand)
    journal: promote=true, favsafe_passed=true, policy=A-05
```

### 5.4 Journal 必須フィールド（設計）

実装時に Offline 診断可能とするため:

- `promote`, `promoted_id`
- `favsafe_blocked` / `favsafe_reason`
- `coverage_components`（rarity, relative_strength, …）
- `top_margin`, `field_size`
- `leak_inputs: false`

### 5.5 明示的にやらないこと

- A-04 / A-01 ロジック改変  
- 結果・払戻・確定着順の入力利用  
- Flag 既定 ON  
- Production 配線  

---

## 6. パラメータ（設計プレースホルダ）

実装 Round で Offline により校正。ここは **予約値**。

| パラメータ | A-03 | A-05 初期案 | 校正原則 |
|------------|------|-------------|----------|
| `PROMOTE_FIELD_MIN` | 12 | 12（維持候補） | Real 発火率を見て引き上げ可 |
| `DEEP_RANK_MIN` | 7 | 7（維持候補） | Pool 定義と整合 |
| Style rarity 単独 | 十分条件 | **必要条件のみ** | 単独 promote 禁止 |
| `MARGIN_MIN`（FS-1） | なし | TBD（例 0.05+） | worsened_rank1→0 優先 |
| Soft/Hard | Hard のみ | Conditional Hard | FavSafe 必須 |
| Promote rate target | 制御なし | Offline 上限（例 ≤15% 仮） | 改善 precision とトレードオフ |

---

## 7. Hard Gate（仕様）

詳細成功条件は Success Criteria 文書。Spec 上の必須ゲート:

### 7.1 Offline Gate（必須 · 本番相当）

| Gate | 条件 |
|------|------|
| OG-1 | n = 285（同一コーパス） |
| OG-2 | Treatment Hit **>** Control Hit |
| OG-3 | `worsened_winner_rank1 = 0` |
| OG-4 | churn_hit は OG-3 と整合（本命破壊 churn 禁止） |
| OG-5 | A-03 同時 ON なし |
| OG-6 | Leak 検査 PASS |

### 7.2 Lab Gate（回帰 · 必須だが Offline より優先度は下）

| Gate | 条件 |
|------|------|
| LG-1 | Flag OFF で Control 再現 |
| LG-2 | A-05 solo または指定スタックで **churn による Hit 層破壊が設計許容内** |
| LG-3 | Pool 層の回復がゼロでないこと（完全放棄は FAIL 候補） |

※ Lab Hit 279 の再現は **必須としない**（A-03 置換により Pool 加点の形が変わり得る）。  
必須は Offline 改善と本命非破壊。

### 7.3 Isolation Gate

| Gate | 条件 |
|------|------|
| IG-1 | Selection / Evaluation / Representation / Purchase コード差分なし（Admission + Flag のみ） |
| IG-2 | A-03 ソース SHA 不変 |
| IG-3 | 既定 Flag すべて OFF のまま |

---

## 8. リスクと緩和

| リスク | 緩和 |
|--------|------|
| FavSafe が強すぎて深掘り +12 も消える | Margin 閾値を段階的に緩め、improved を監視 |
| Lab Pool×9 が落ちる | 許容し Offline を優先。必要なら Lab Real-like 層を追加 |
| パラメータ過適合 | Dual-Gate · 閾値は少数 · 事前登録 |
| A-03 との混乱 | Flag 相互排他 · 文書で Baseline v3 を明示 |

---

## 9. Stop

本 Spec は設計まで。`admission_policy_a05.py` の作成・Flag 追加・実験実行は行わない。
