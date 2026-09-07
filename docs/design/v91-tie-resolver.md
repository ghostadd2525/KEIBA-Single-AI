# Version9.1 Design — Tie Resolver（AI Score 非改変）

**Status:** Design only（実装なし / コード変更禁止）  
**Date:** 2026-07-27  
**根拠:** `docs/research/v91-rank-degeneracy-analysis.md`  
**前置:** `docs/research/v9-younghorse-analysis.md`  
**Hard Lock:** PE / CE / AI推論 / Research Runtime / ResultAutomation は変更しない

---

## 1. 問題

2歳新馬（初出走）で PE が複数頭に同一 `model_rank=1` / `mark=honmei` / **同一 `win_prob`** を付ける。

| 現状 | 値 |
|------|-----|
| Strict Hit | 0% |
| Soft Hit | 57% |
| 平均タイ頭数 | 4.43 |

**制約:** AI Score（`win_prob` / モデル出力）は変更しない。  
**解法:** 同点集合の上だけで動く **Tie Resolver**。

---

## 2. 設計原則

1. **Score Immutability** — Resolver は `win_prob` / raw score を書き換えない。  
2. **Activation Gate** — タイが無いレースでは **完全 no-op**（既存 Strict 選定を維持）。  
3. **Set Selection Only** — 入力は「タイ集合 ⊆ runners」、出力は「その集合から 1 頭」。  
4. **Evidence-First** — スコアカードで DATA GAP の候補は、収集が終わるまで本番採用しない。  
5. **Debut-Aware** — ジョッキー継続など初出走で定義不能な特徴はゲートで除外。  
6. **Fail-Open** — Resolver が解けない（残タイ・欠損）場合は現行タイブレーク（馬番等）へフォールバックし、例外で落とさない。  
7. **Observability** — `tie_group_size`, `resolver_fired`, `resolver_signal`, `resolved|unresolved` をメタに残す（Challenge / Audit 用）。

---

## 3. 配置（論理アーキテクチャ）

PE 本体の外側。**後段アダプタ**としてのみ定義する（本ドキュメントは設計。実装は別承認）。

```
Prediction Bundle (immutable scores)
        │
        ▼
┌───────────────────────┐
│ Tie Detect            │  same model_rank (min) and/or equal win_prob
└───────────┬───────────┘
            │ |G| <= 1 → pass-through (existing unique top)
            ▼
┌───────────────────────┐
│ Tie Resolver          │  external evidence on G only
│  (no score mutation)  │
└───────────┬───────────┘
            │ pick ∈ G
            ▼
   Official Top Pick / Marks display policy
```

**非対象:**

- PE 学習・推論グラフ  
- CE / Delete / Purchase 境界の再定義（必要なら別デザイン）  
- ResultAutomation の Hit 定義変更（観測メタ追加は将来チケット）

---

## 4. 活性化条件（Activation）

レース単位で次のいずれかを満たすとき `resolver_fired=true`:

| ID | 条件 | 備考 |
|----|------|------|
| A1 | `count(model_rank == min_rank) >= 2` | 主条件 |
| A2 | `count(mark == honmei) >= 2` | 新馬で A1 とほぼ一致 |
| A3 | タイ群内 `win_prob` のユニーク数 == 1 かつ |G|>=2 | スコア潰し検出 |

推奨: **A1 ∧（クラス ∈ {2歳新馬, 新馬}）** から開始（過発火抑制）。  
将来: 非新馬でも A1 があれば任意発火（現状ほぼ無し）。

**初出走ゲート:** `starts_before == 0` or `race_name` に「新馬」→ 継続騎乗ルールをスキップ。

---

## 5. 入出力契約（Draft）

### Input

```json
{
  "race_id": "2026-07-26-03-05",
  "class": "2歳新馬",
  "runners": [
    {
      "horse_number": 5,
      "model_rank": 1,
      "mark": "honmei",
      "win_prob": 0.1002,
      "evidence": {
        "popularity": null,
        "odds": null,
        "trainer_id": null,
        "jockey_id": "...",
        "frame": null,
        "horse_weight": null,
        "sire_id": null,
        "damsire_id": null,
        "workout": null,
        "training": null
      }
    }
  ]
}
```

`win_prob` / `model_rank` は **参照のみ**。

### Output

```json
{
  "resolver_version": "v91-design/0.1",
  "fired": true,
  "tie_group": [5, 6, 7, 8, 9, 10],
  "status": "resolved | unresolved | skipped",
  "pick_horse_number": 9,
  "signal_chain": ["popularity", "trainer_prior"],
  "score_mutated": false
}
```

不変条件: `score_mutated == false` を常に検証。

---

## 6. 解決アルゴリズム（Draft Policy）

### 6.1 ステージング

| Stage | 内容 | 本番採用条件 |
|-------|------|----------------|
| **S0 Detect** | タイ集合 G を構築 | 設計確定 |
| **S1 Collect** | Evidence スナップショットを予測時刻で保存 | **必須（現 DATA GAP 解消）** |
| **S2 Offline Scorecard** | 候補シグナルの Soft 回収率を週次計測 | n≥30 新馬推奨 |
| **S3 Shadow Resolver** | 本番選定は変えずメタだけ記録 | 承認後 |
| **S4 Soft Launch** | 2歳新馬のみ Resolver 結果を表示/Challenge に反映 | スコアカード合格後 |

本ドキュメント時点で許可されるのは **S0–S2 の設計**まで（実装禁止期間）。

### 6.2 シグナルチェーン（仮説順序）

AI Score を使わない。欠損はスキップ。残タイなら次へ。

```
G0 = tie group
G1 = argmin popularity within G0          # P0 市場
G2 = argmin odds within G1                # P0 市場（人気と同値なら）
G3 = apply trainer_prior within G2        # P0 厩舎事前（要定義）
G4 = apply sire/damsire_prior within G3   # P1 血統
G5 = apply workout/training/horse_weight  # P1 調教系
G6 = argmin frame within G5               # P2 弱
G7 = fallback horse_number                # 現行互換
```

**明示的に除外（初出走）:**

- ジョッキー継続騎乗 / 乗り替わり（定義不能）

**明示的に非推奨（現状 Evidence）:**

- タイ内 `win_prob` 最大化 — 全同一のため情報量ゼロ（分析で確認済み）

### 6.3 厩舎・血統 Prior（定義プレースホルダ）

実装前にオフラインで固定する（例）:

- `trainer_prior`: 直近 N 週の「新馬・勝率」or「新馬・連対率」（リーク防止: 当該レースより前のみ）  
- `sire_prior` / `damsire_prior`: 同条件の産駒新馬成績  

これらは **PE 特徴に入れない**（Resolver 専用テーブル）。学習パイプラインと分離し Hard Lock を守る。

---

## 7. Evidence 収集要件（PE 非変更）

parse 層には既に `_trainer` がある。**CSV/DB へ露出するだけ**の収集は PE 推論ロジック変更ではないが、実装は別チケット・承認が必要。

| Evidence | 取得源（案） | 予測時点で必要な理由 |
|----------|--------------|----------------------|
| popularity / odds | shutuba / odds API | 市場 Tie Break の P0 |
| trainer | shutuba `_trainer` 露出 | 騎手×厩舎・厩舎 prior |
| frame | shutuba（品質担保） | P2 |
| horse_weight | 当日パドック/成績表 | 新馬の身体情報 |
| workout / 調教 | 調教タイムページ | 初出走の数少ないシグナル |
| sire / damsire | horse DB pedigree | 血統 prior |

**スナップショット規則:** Resolver 用 Evidence は `prediction_created_at` 以前の値のみ。確定後人気の事後リーク禁止。

---

## 8. 成功指標（Research Gate）

対象: 2歳新馬、タイ発火レース。

| KPI | ゲート案 |
|-----|----------|
| Soft Recovery Rate | Soft∧¬Strict のうち Resolver 正答 ≥ **50%**（まず Shadow） |
| Strict Hit（新馬全体） | 0% → **≥ 30%**（Soft 天井 57% の半分超を初期目標） |
| Non-degraded regression | 非新馬 Strict を悪化させない（発火率 ≈0 を維持） |
| Unresolved rate | 発火レースの未解決 < 30%（データ充足後） |
| `score_mutated` | 常に false |

不合格なら S4 に進まない。

---

## 9. リスク

| リスク | 緩和 |
|--------|------|
| 人気追随で市場コピーになる | Challenge 公式は単勝 Benchmark と分離して監視；Resolver は表示/研究フラグで段階導入 |
| リーク（結果後オッズ） | 予測時刻スナップショット必須 |
| 小サンプル過適合 | n≥30 新馬でから Shadow→Launch |
| Soft 外 Miss | Resolver 対象外と明記；別 Research |
| Hard Lock 違反 | PE 配下にコードを置かない；後段アダプタのみ |

---

## 10. 非ゴール（再掲）

- PE の損失関数・ランキングヘッド変更  
- タイ解消のために `win_prob` を再正規化して書き戻すこと  
- 全クラス一括の強制 Tie Break  
- 本ドキュメント時点での本番コード変更  

---

## 11. 次アクション（実装チケット分割案）

1. **Collect-Trainer-Export** — `_trainer` を runners 永続化（推論非変更）  
2. **Collect-Odds-Popularity-Snapshot** — 予測作成時に人気・オッズをバンドル付帯 or 別表  
3. **Collect-Pedigree-Workout** — 父・母父・追切・馬体重  
4. **Research-Scorecard-V91** — 上記収集後に Soft 回収率を再計測  
5. **Shadow-Tie-Resolver** — 選定非反映でメタのみ  
6. **Launch-Tie-Resolver-Shinba** — ゲート合格後

---

## 12. 参照

- `docs/research/v91-rank-degeneracy-analysis.md`  
- `docs/research/v9-younghorse-analysis.md`  
- `docs/design/v9-benchmark-layer.md`（Challenge 正本は単勝。Resolver は選定層）  
- shutuba parse: `services/pi-keibanet-api/pi_keibanet/netkeiba/parse.py`（`_trainer` 既存）
