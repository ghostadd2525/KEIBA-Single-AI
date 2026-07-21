# RePick v2 — Design Review（P0）

**Date:** 2026-07-21  
**Status:** **条件付き承認**（設計）+ **Exit Approved / Stop Active** → 実装チケット **open**  
**Exit Criteria:** [`repick-v2-exit-criteria-contract.md`](./repick-v2-exit-criteria-contract.md)（**Approved**）  
**Stop Criteria:** [`repick-v2-stop-criteria-contract.md`](./repick-v2-stop-criteria-contract.md)（**Active**）  
**Ticket:** [`issues/ISSUE-REPICK-V2-001-implementation.md`](./issues/ISSUE-REPICK-V2-001-implementation.md)  
**Parent:** [`prediction-v1-miss69-theme-roi-review.md`](./prediction-v1-miss69-theme-roi-review.md)（ROI Review **採択**）  
**Series:** Version2 Product（Win5 Optimizer / RePick 段）  
**Priority:** **P0**（Version2 最優先）

---

## 0. 採択ロードマップ（前提）

| 優先 | テーマ | 本レビュー |
|------|--------|------------|
| **P0** | **RePick v2** | **本設計** |
| P1 | Pool + Entry v2 | 後続 |
| P2 | Delete v2（`after_delete` 35） | 後続 |
| P3 | Candidate Evaluation Calibration | 後続 |
| 保留 | Learning / Feature | 着手しない（PV2-F01 Archive 維持） |

### 0.1 硬制約（Must）

| 制約 | 内容 |
|------|------|
| 新規 Feature | **追加しない**（Prediction Core 特徴空間・市場 Feature ともに触らない） |
| Collector | **非変更** |
| V1 Baseline | **非変更**（Phase255 Hit 集合・V1 Core 28 特徴・Flag OFF = 恒等） |
| Feature Flag | **必須**（既定 **OFF**） |
| AB | **必須**（Control = Baseline / Treatment = Flag ON） |
| 実装 | Exit Approved + Stop Active 後 → **ISSUE-REPICK-V2-001**（コード実装はこのチケット範囲） |

### 0.2 境界

| 許可 | 禁止 |
|------|------|
| RePick 段の membership / displacement ルール（Flag 下） | Pool / Entry / Delete / Purchase guard の改変（P1/P2） |
| 既存 survival 順序・N の **読取** | `len(repick)` 常態 N+1 append |
| journal / 監査 CSV | Collector / ETL / FeatureLoader / 学習パイプライン |
| AB・Canary 設計 | Learning・新 Feature Contract |

---

## 1. 問題定義

Version1 残ミス 69 のうち、`first_loss_stage = re_pick` は **18 件**。

共通構造:

```text
winner ∈ Candidate Pool
winner ∉ RePick
→ Purchase / Delete に到達せず Hit 不可
```

**入口は成功、圧縮（top-N survival）で除外**されている。  
RePick v2 の責務は「Pool 内なのに RePick にいない」債務の **構造的支払い**であり、順位再学習や新特徴ではない。

---

## 2. 対象母集団

### 2.1 残 18 件（正本）

正本: `docs/ops/_pv2_f01_roi_validation_detail.csv`（`first_loss_stage=re_pick`）

| セグメント | n | winner_rank | RePick v2 扱い |
|------------|--:|-------------|----------------|
| **rank710** | **11** | 7–10 | **一次対象（Primary）** |
| other_miss | 6 | 11–12 | **本 P0 の一次対象外**（Deep。T-W / FAR / Pool 後続と重複しやすい） |
| rank46 | 1 | 6 | **二次（任意 AB）**。rank6 near-cut。P0 本線は rank710 |

### 2.2 Primary 一覧（rank710 × re_pick = 11）

| race_id | rank | pool | repick N | 備考 |
|---------|-----:|-----:|---------:|------|
| 2024-01-21-京都-11 | 7 | 12 | 7 | |
| 2026-04-12-阪神-10 | 7 | 9 | 7 | 旧 T-R7N allowlist |
| 2026-04-25-京都-10 | 7 | 9 | 7 | |
| 2026-06-28-小倉-11 | 7 | 8 | 5 | 旧 T-R7N allowlist（core_under） |
| 2024-07-14-函館-10 | 8 | 9 | 7 | 旧 T-R7N allowlist |
| 2025-12-14-中京-11 | 8 | 9 | 7 | |
| 2026-04-19-中山-10 | 8 | 9 | 7 | |
| 2025-12-13-中山-10 | 9 | 9 | 7 | |
| 2026-01-18-中山-10 | 9 | 12 | 7 | 旧 T-R7N allowlist |
| 2024-02-18-京都-11 | 10 | 12 | 7 | |
| 2026-03-15-中山-11 | 10 | 10 | 7 | |

**rank710 全体 15 件との関係:** `re_pick` 11 / `candidate_pool` 3 / `purchase` 1。  
→ Pool 外 3・purchase 1 は **RePick v2 では救えない**（P1 / 別段）。

### 2.3 改善母集団（定義）

| 名称 | 定義 | n | 用途 |
|------|------|--:|------|
| **G0 観測母集団** | `first_loss=re_pick` | **18** | パイプライン負債の全体像 |
| **G1 改善母集団（Primary）** | G0 ∩ `v1_bucket=rank710` ∩ `in_pool=1` ∩ `in_repick=0` ∩ `winner_rank∈[7,10]` | **11** | **RePick v2 の ROI / AB 主指標** |
| **G2 二次** | G0 ∩ `v1_bucket=rank46`（rank=6） | **1** | 任意拡張（RP-1 系）。本線ゲートに必須としない |
| **G3 除外（P0）** | G0 ∩ `other_miss`（rank≥11） | **6** | Deep。RePick v2 P0 の期待改善に **加算しない** |

**本番ルール用の匿名候補集合（G1′）**（勝者名指し禁止）:

```text
horse ∈ candidate_pool
∧ horse ∉ current_repick
∧ model_rank(horse) ∈ [7, 10]
∧ cut_by_topN_survival(horse)   # survival 順で N 枠外、または N 枠内だが後段で脱落
```

評価時の上限（Winner-Anchored ceiling）は G1 と一致しうるが、**実装トリガは G1′（匿名）**とする。  
旧 T-R7N の「winner のみ」は研究上限の参照とし、本番契約にはしない。

---

## 3. 期待改善数

尺度は **G1（11）を分母**とする（18 全件や 69 全件で割らない）。

| シナリオ | 期待 Hit 回収（G1） | 対 G0(18) | 備考 |
|----------|-------------------:|----------:|------|
| **Conservative** | **+4 〜 +6** | +4〜+6 | NEAR/境界・max1・被害者制約厳格 |
| **Base（設計目標）** | **+6 〜 +8** | +6〜+8 | テーマ ROI Review の RePick レンジ下限〜中央 |
| **Optimistic** | **+8 〜 +9** | +8〜+9 | 下流 Purchase/Delete で落ちない前提が強い場合 |
| G2 加算（任意） | +0 〜 +1 | — | rank46×1。本線ゲート外 |
| G3 | **+0（P0）** | — | Deep は期待に入れない |

**設計目標（Go 候補の目安）:**

- G1 回収率 **≥ 6/11（≈55%）** または絶対 **+6** 以上  
- Baseline Hit **非減少**（既得 Hit 損失 = 0）  
- off-target（意図外レースでの破壊的置換）を AB で監視  

旧 T-R7N（allowlist 4）の期待 +1〜+3 は **部分集合の上限参照**。RePick v2 は G1=11 へ構造規則を一般化するが、最初の AB は **発火キャップ**で安全側に寄せる（§6）。

---

## 4. 失敗モード（構造）

既存 `build_world_aware_repick_pool` 系の圧縮:

1. `determine_repick_pool_size` → **N ∈ [5,7]**（多くは 7、小倉-11 は 5）  
2. `_world_survival_score` 降順で top-N  
3. 後段 quota / `WORLD_REPICK_MAX_POOL` 等で再構成しうる  

| モード | 説明 | G1 での典型 |
|--------|------|-------------|
| **NEAR cut** | survival 順位が N+1〜N+2 で枠外 | rank 境界の押し出し |
| **SLOT 欠落** | survival 上は N 内だが後段 membership で欠落 | 旧 R7N-B 型 |
| **軸不一致** | pool_priority では残るが survival では落ちる | rank710 全般 |

**非原因（本 18 では一次ではない）:** Collector 欠落、新 Feature 不足、CE の Top1 ミス単独（Pool 入場済み）。

---

## 5. 設計方針（RePick v2）

### 5.1 一文化した責務

> **Flag ON 時のみ**、Candidate Pool 内の **model_rank 7–10** が top-N survival 圧縮で落ちる場合に、**N 不変・max1 displacement** で RePick membership を支払い得る。

### 5.2 コンポーネント（論理）

```text
                    Flag OFF ──────────────────────────────► 恒等（V1）
                         │
Candidate Pool ──► world_aware top-N ──► [RePick v2 sidecar] ──► selected'
                         │                      │
                         │              displace max1 (N固定)
                         │                      │
                         └──────── journal ──────┘
```

| 部品 | 役割 |
|------|------|
| Trigger | G1′ 条件（§2.3）+ 距離 facet（NEAR / 任意 SLOT） |
| Actuator | `len(selected)` 不変。victim = 無保護テール（prefer `model_rank≥11`） |
| Cap | レースあたり **max1**。会議/日次 fire_cap は AB で設定 |
| Journal | race_id / candidate / victim / facet / N / surv_pos / flag |

### 5.3 距離 facet（設計）

| facet | 条件（案） | 意図 |
|-------|------------|------|
| **RV2-A NEAR** | `N < surv_pos ≤ N+2` かつ cut | 境界誤除外（最優先） |
| **RV2-B SLOT** | `surv_pos ≤ N` かつ ∉repick（後段脱落） | 旧 R7N-B。AB 第2段で解禁可 |

**初回 AB 推奨:** RV2-A のみ（安全）。RV2-B は別 Flag または同一 Flag の sub-mode。

### 5.4 Victim / 保護

| 規則 | 内容 |
|------|------|
| N 不変 | append 禁止（真空なら発火記録のみ・成功扱いにしない） |
| Victim 優先 | `model_rank≥11` → 無保護の survival 最下位 |
| 保護 | core（rank≤3 相当）・既存 RP 保護・Alpha-paid 等は victim にしない（既存契約を読取尊重） |
| 匿名 | **勝者名指し禁止**（本番）。評価レポートのみ Winner-Anchored 上限を併記可 |

### 5.5 既存設計との関係

| 既存 | 関係 |
|------|------|
| Phase248 RP-2 | 思想の祖先（rank710 in-pool compress protect）。RePick v2 はこれを Version2 Flag+AB 契約に昇格 |
| Phase283 T-R7N | allowlist 4・Winner-Anchored。**上限・事例参照**。本番トリガには採用しない |
| T-W / T-E / ACT-C2 / P-1A | **非改変**。帯域拡張で流用しない（独立 sidecar） |
| Delete / Pool / Entry | 触らない（P1/P2） |

---

## 6. Feature Flag / AB

### 6.1 Flag

| 項目 | 値 |
|------|-----|
| 名（案） | `WIN5_REPICK_V2_ENABLED` |
| 既定 | **`false`（OFF）** |
| OFF 時 | RePick 経路は **V1 とビット一致**（恒等） |
| ON 時 | §5 sidecar のみ差分 |

任意サブ（第2 AB）:

| Flag | 既定 | 意味 |
|------|------|------|
| `WIN5_REPICK_V2_SLOT` | false | RV2-B SLOT 解禁 |
| `WIN5_REPICK_V2_RANK6` | false | G2（rank6）二次 |

### 6.2 AB 設計（必須）

| 項目 | Control | Treatment |
|------|---------|-------------|
| 定義 | Phase255 / V1 Baseline（Flag OFF） | 同一コーパス + Flag ON |
| コーパス | 285R（または承認済み固定セット） | 同左 |
| 主メトリクス | G1 のうち `in_repick=1` へ転換した件数、最終 Hit 差分 | |
| ガード | 既得 Hit 損失 = 0、組み合わせ数爆発なし、off-target 監視 | |
| 単体性 | **RePick v2 単独**（Pool/Delete/CE/Learning/Feature を同時に載せない） | |

**Go / No-Go（設計案・実装前に確定）:**

| ゲート | 条件 |
|--------|------|
| G-Hit | Treatment Hit ≥ Control Hit |
| G-G1 | G1 回収 **≥ +4**（Conservative 下限）かつ目標として **+6** をレビュー |
| G-Ident | Flag OFF で Control と出力恒等 |
| G-Scope | G3（Deep）を「成功」に数えない／Pool 外を救ったことにしない |

FAIL 時: Flag 維持 OFF、原因分析のみ。Production 既定 ON は別承認。

---

## 7. 非対象・非目標（明示）

| ID | 内容 |
|----|------|
| NR-1 | 新規 Prediction Feature / PV2-F01 再開 |
| NR-2 | Collector / ETL / FeatureLoader 変更 |
| NR-3 | V1 Core 28 特徴・学習の変更 |
| NR-4 | Deep rank≥11 の RePick 救済（G3） |
| NR-5 | Pool 外 3 件の rank710（P1） |
| NR-6 | `after_delete` 35（P2 Delete v2） |
| NR-7 | Purchase guard max 変更・Delete Phase195 解除 |
| NR-8 | N+1 常態 append |

---

## 8. リスクと緩和

| リスク | 影響 | 緩和 |
|--------|------|------|
| 無関係 deep を押し出し Hit 損失 | Baseline 破壊 | victim 優先 rank≥11、Hit 損失ゲート |
| 組合せ数・購入集合の歪み | 運用コスト | N 不変、max1、fire_cap |
| Winner-Anchored と匿名のギャップ | 評価楽観 | レポートに ceiling vs 本番発火を分離 |
| SLOT まで広げすぎ | ノイズ増 | 初回 AB は NEAR のみ |
| Formal vs Legacy 経路差 | 実装場所ミス | 実装前に正式経路の hook 点を別紙で固定（本レビューは論理のみ） |

---

## 9. 成果物・次工程

1. Exit Criteria — **Approved**  
2. Stop Criteria — **Active**  
3. 実装チケット — **ISSUE-REPICK-V2-001 open**（Flag + sidecar + journal + AB）  
4. 実装完了後: 正式 AB → Exit/Stop 判定 →（PASS 時のみ）Canary

---

## 10. 結論

**RePick v2（P0）は条件付き承認。G1=11 を改善母集団とし、匿名トリガ・Flag OFF 恒等・単独 AB を維持する。合否・Rollback・Canary・採用は Exit Criteria Contract に従う。コード実装および実装チケットは Exit Criteria 承認後のみ。**

---

## 承認チェックリスト（レビュー用）

- [x] G0=18 / G1=11 / G3=6 の母集団定義に合意（条件付き承認）  
- [x] 期待改善の分母が G1 であること  
- [x] 匿名トリガ（勝者名指し禁止）に合意 — 詳細は Exit §7  
- [x] Flag OFF 恒等・AB 単独に合意  
- [x] 新 Feature / Collector / V1 Baseline 非変更に合意  
- [x] Deep・Delete・Pool を P0 に混ぜないことに合意  
- [x] Exit Criteria Contract 承認  
- [x] Stop Criteria Contract Active  
- [x] 実装チケット化（ISSUE-REPICK-V2-001）  
