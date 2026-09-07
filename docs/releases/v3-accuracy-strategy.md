# Version 3 — Accuracy Strategy

**Date:** 2026-07-22（Accuracy Phase 1 Close: 2026-07-24）  
**Status:** Design + Lab Phase 1 **CLOSED**（実装の新規 Accuracy は別承認）  
**Vision:** [`v3-vision.md`](./v3-vision.md)  
**Architecture:** [`v3-architecture-proposal.md`](./v3-architecture-proposal.md)  
**Phase 1 Final:** [`v3-accuracy-phase1-final-report.md`](./v3-accuracy-phase1-final-report.md)  
**Control:** V2 Final = PE-V2-A ON · Hit **218** · churn 基準 0  
**Lab Primary:** A-01 Hit **246** · **Lab Secondary:** A-02 Hit **242**

---

## 1. 戦略の一文

> **残 miss を層別に分解し、表現（Feature/学習）で遠位を、Admission で場の不足を、Selection で並べ替え副作用を解く。  
> V2 の RP Rescue / CE 温度は戦略から除外する。**

---

## 2. Control と目標

| 項目 | 値 |
|------|----|
| Corpus | 285R（labeled_test） |
| Control | Phase255 + PE-V2-A |
| Control Hit | **218** |
| Hard Gate | **Hit > 218** かつ **churn_hit = 0** |
| Secondary | Purchase p95 ≤ Control×1.10、WIP 率 非悪化 |

---

## 3. 残 miss の戦略マップ（V2 引き継ぎ）

V2 Final 後の構造（概略）:

| 層 | 現象 | n の目安（G1/残） | V3 主レバー |
|----|------|------------------|------------|
| L-Eval | 遠位（surv≪N+2） | 少数だが重い | **Ranking Model / Feature** |
| L-Boundary | surv≈N+2 | 境界群 | Admission 可変枠 or Margin Selection |
| L-Reorder | surv≤N なのに枠外 | compress 副作用 | **Reorder-only Selection** |
| L-Pool | まだ Pool 外 | PE 後も残存 | Admission Policy 拡張 |
| L-Delete | after_delete | ≈34–35 | **触らない** |

```text
優先度（戦略）:
  1) Representation / Ranking   … 天井を上げる
  2) Pool Admission 次世代      … 場のカバレッジ
  3) Reorder Selection          … 副作用の除去
  4) （禁止）RP-NEAR Rescue / CE 温度
```

---

## 4. Accuracy 改善戦略（柱）

### 柱 I — Representation First（特徴量・学習）

**仮説:** 遠位 miss は「選ばなかった」のではなく「表現が区別できない」。

| ステップ | 内容 |
|----------|------|
| I-1 | 残 miss 再分類を V2 Final 基準で凍結（オフライン表） |
| I-2 | Feature Contract v3 草案（候補 §5） |
| I-3 | ROI Validation（情報利得・リーク検査・安定性） |
| I-4 | Ranking Model D1/D2 のオフライン AB |
| I-5 | 単独 Flag で 285R Hard Gate |

**成功条件:** Hit>218 ∧ churn=0。失敗時は Feature を捨て、Admission へ（継ぎ足し禁止）。

### 柱 II — Next-Gen Pool（Candidate Pool + Entry）

**仮説:** PE-V2-A の +1 Deep は正しい方向だが、容量が文脈非依存で不足/過剰がある。

| ポリシー | 狙い |
|----------|------|
| Banded Deep Admit | 大フィールド・薄マージン時に枠を増やす |
| Coverage Admit | 世界/脚質ギャップを埋める |
| Margin Gate | 不要 Deep を削り Purchase を守る |

**成功条件:** WIP 率↑ または境界 miss↓、かつ Hit Hard Gate。  
**失敗パターン:** Pool だけ増え Hit 不変 → Selection/Eval 不足と診断し柱 I/III へ。

### 柱 III — Selection as Reorder（RePick 再定義）

**仮説:** 一部 miss は「強さ不足」ではなく「枠配分・compress の副作用」。

| 方針 | 内容 |
|------|------|
| やる | Pool 内 swap / role slot 再配分 |
| やらない | Pool 外 Rescue、NEAR 系、勝者探索 Trigger |
| 順序 | 柱 I または II で Hit が動いてから。単独では期待値低 |

### 柱 IV — 明示的非戦略（V2 からの学び）

| 非戦略 | 理由 |
|--------|------|
| RP-V2-A 再 AB | Rescue 0/11 · Trigger 不足 |
| CE-V2-A 温度 | Hit 悪化 · churn |
| Delete 緩和 | 境界破壊・製品方針違反 |
| 複数 Flag 同時 ON | 帰属不能 |

---

## 5. 特徴量追加候補（Design のみ）

> いずれも **候補**。Contract / ROI 前に実装しない。結果・着順・払戻は入力禁止。

### 5.1 レース文脈

| ID | 候補 | 仮説 | リスク |
|----|------|------|--------|
| F-V3-01 | フィールドサイズ正規化強度 | 大フィールドで Deep 必要度↑ | 既存 proxy と冗長 |
| F-V3-02 | コース×距離の歴史的ペース型 | 展開世界の事前分布 | データドリフト |
| F-V3-03 | 馬場・天候の離散状態 | 適性ミスマッチ検出 | 欠測多い日 |

### 5.2 馬・相対

| ID | 候補 | 仮説 | リスク |
|----|------|------|--------|
| F-V3-10 | 近走パフォーマンスの減衰付き平均 | 遠位の過小評価是正 | リーク（確定着順の扱い要設計） |
| F-V3-11 | 相手関係の相対ランク安定性 | 境界の入れ替わり抑制 | 計算コスト |
| F-V3-12 | 脚質クラスタ距離（場内） | Coverage Admit の入力 | クラスタ定義依存 |

### 5.3 市場代理（リーク無し）

| ID | 候補 | 仮説 | リスク |
|----|------|------|--------|
| F-V3-20 | 単勝オッズ対数の残差（モデル対比） | 市場が捉える情報の差分 | 過剰適合・公開時刻 |
| F-V3-21 | 人気帯の混雑度 | 境界レース検出 | 市場操作 |

### 5.4 採用プロセス

```text
候補列挙 → リーク検査 → 単変量 ROI → 多変量安定性 → Contract 凍結 → モデル接続 AB
```

**F01 Archive は再開しない**（V2 方針継承）。新規は **F-V3-*** 名前空間。

---

## 6. モデル責務の整理

| モデル / モジュール | 責務 | 非責務 |
|--------------------|------|--------|
| **Encoder / Feature Store** | 表現ベクトル・拡張表の生成 | 選定・購入 |
| **Ranking / Survival Model** | win/survival/rank の推定 | Pool 容量・Rescue |
| **Admission Policy** | 誰を Pool に入れるか | 最終 N 頭の最適化 |
| **Selection Policy** | Pool 内並べ替え・枠 | 表現学習・Pool 外追加 |
| **Purchase Mapper** | チケット化・Delete 適用 | Hit の直接最大化 |
| **Explain Journal** | 決定の記録 | 精度の変更 |

### 6.1 学習目標の分離（設計）

| ヘッド | 損失の意図 | 主に効く miss |
|--------|------------|---------------|
| win_prob | 勝者尤度 | 遠位・評価不足 |
| survival / in-N | 「枠内に残る」 | 境界 |
| listwise rank | 相対順序 | 並べ替え副作用の前提品質 |

V2 の単一 Softmax 温度は、この分離を欠いていた。

---

## 7. Entry 判定 — 改善案の評価軸

各 Admission 案は次で採点する（実装前の設計ゲート）:

| 軸 | 質問 |
|----|------|
| 匿名性 | 結果列なしで定義できるか |
| 容量 | 上限 K が明示か |
| 帰属 | Flag OFF で identity か |
| Purchase | 膨張シナリオを机上で示せるか |
| PE との関係 | V2 PE を内包/置換のどちらが明確か |

**推奨初期案（設計上）:** AP-V3-A（Banded Deep）を柱 II の第一候補。  
AP-V3-B/C は A の FAIL 分析後。

---

## 8. Candidate Evaluation — 再設計サマリ

| V2 CE | V3 Evaluation |
|-------|----------------|
| Softmax 温度 Flag | **廃棄** |
| 既存スコアの見た目調整 | **校正・再ランク・分離ヘッド** |
| churn 許容の余地 | **Hard Gate で 0 強制** |
| Feature 不変前提 | **Feature Contract とセットで天井突破** |

最小実験（Feature 不変）は **D1 Recalibrator** まで。効かなければ表現不足と結論し柱 I 本丸へ。

---

## 9. RePick — 位置付け（最終）

```text
V2 RePick (RP-V2-A)     = Rescue 装置     → 戦略から除外
V3 Selection Policy     = Reorder / Slot  → 補助レバー（後段）
```

文書・実験 ID に `RP-V2` / `WIN5_REPICK_V2` を再利用しない。  
新規は `SEL-V3-*` / `WIN5_V3_SELECTION_*` を用いる（実装時）。

---

## 10. 実験との接続

本 Strategy の柱は Experiment Roadmap に直列化する。

| 柱 | Roadmap Phase |
|----|---------------|
| I Representation | V3-P1 / P2 |
| II Pool Admission | V3-P3 |
| III Selection | V3-P4 |
| Hard Gate AB | 各 Phase 末尾 |

詳細: [`v3-experiment-roadmap.md`](./v3-experiment-roadmap.md)

---

## 11. 参照

| 文書 | パス |
|------|------|
| V2 Final | `docs/releases/v2-accuracy-final-report.md` |
| G1 層分類 | `compare/v2_accuracy_g1_layer_classification.csv` |
| RP G1 観測 | `docs/ops/v2-rp-v2-a-g1-fail-observation.md` |
| 旧薄い V3 メモ | `docs/releases/v2-accuracy-v3-roadmap.md`（本 Strategy が上位） |
