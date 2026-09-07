# Version30 — Contract Gap Audit

**Date:** 2026-07-27  
**比較:** 設計契約 → 実装契約  
**実装変更なし**

## Design contract（intended）

出典: `feature_dependency_map.md` / `demo_pace_model_v2` / World Trigger docs（V24–V29）

```text
[Design]
history features
  → demo_pace_model_v2.build_pace_features
       includes add_win5_leg_difficulty_features
  → merge market → runners_pace_market_features.csv
  → FeatureLoader.load (daily preferred)
  → FeatureGenerator / enrich (既存列尊重)
  → detect_race_meta → meta.race_leg_difficulty
  → classify_world_line_type(nz(meta.race_leg_difficulty))
```

設計上の意図:

1. **難易度は pace_model 式で生成**される  
2. **FeatureLoader 入力 CSV に列として載る**  
3. World Trigger は meta の `race_leg_difficulty` を読む  
4. FeatureGenerator は「境界アダプタ」であり、**式の再実装先ではない**（probability 委任）

「設計どおり FeatureGenerator から呼ばれる契約だったか？」  
→ **ドキュメント上の主契約は “pace_model → CSV → Loader”**。  
「FG が add_win5 を呼ぶ」は設計主契約としては **確認できない**（FG は式を導入しないと明記）。

---

## Implementation contract（current Production）

```text
[Implementation — 2026-07-25+]
pi / daily feature build (≈72–74 cols; no race_leg_difficulty)
  → FeatureLoader daily CSV
  → FeatureGenerator.enrich_stable_features
       STABLE_FEATURE_DEFAULTS['race_leg_difficulty'] = 0.5
  → detect_race_meta → meta = 0.5
  → classify_world_line_type → difficulty = 0.5
  → (optional) Research Snapshot copy
```

並行して残存する設計式:

```text
[Offline / non-Core]
demo_pace_model_v2.add_win5_leg_difficulty_features
  → still callable in win5-ai root scripts
  → NOT on EC2 platform tree
  → NOT invoked by FeatureGenerator
```

---

## DEFAULT=0.5 classification

| Question | Answer | Evidence |
|----------|--------|----------|
| 暫定仕様か？ | **フォールバック定数**として定義 | `enrich_stable_features` docstring: 旧CSV/列不足でも落ちない補完 |
| Trigger 専用の暫定世界割当か？ | **No** | World/Trigger 専用コメントなし。全安定特徴の辞書エントリ |
| Production Core 適用か？ | **Yes** | V29 live: loader 欠列 → FG 後 0.5 → CE meta 0.5 |
| Research-only か？ | **No** | Research は同一 meta をコピー |

結論: DEFAULT=0.5 は「設計式の代替として意図的に Trigger を固定する仕様」ではなく、**列欠落時の安定化デフォルト**。  
欠列が常態化した結果、**実質的に恒常 0.5 契約**になっている。

---

## Gap matrix

| # | Design | Implementation | Gap type |
|---|--------|----------------|----------|
| G1 | pace_model が `race_leg_difficulty` を生成 | daily CSV に列なし（07-25+） | **Data contract break** |
| G2 | Loader が設計列を運ぶ | daily 優先で欠列 frame | **Loader input schema drift** |
| G3 | enrich は既存値を尊重 | 欠列のため常に 0.5 fill | **Fallback domination** |
| G4 | Trigger は可変 difficulty を前提（閾値 0.38/0.50/0.62 等） | 常時 0.5 | **Semantic saturation**（V27/V28） |
| G5 | FG は feature logic を導入しない | FG に式を「戻す」案は設計主契約とズレ | **Restoration-target mismatch** |
| G6 | `pace_collapse_risk` / `style_entropy` が式入力 | daily は欠 / `*_v2` のみ | **Component rename / drop** |
| G7 | 設計式モジュールが実行可能 | EC2 platform に `.py` 不在 | **Deploy surface gap** |

---

## Explicit answers (audit items ③)

1. **設計どおり FeatureGenerator から呼ばれる契約だったか？**  
   **No（主契約としては否定）**。設計は pace バッチ生成 → CSV。FG は probability 境界のみ。

2. **現在の DEFAULT=0.5 は暫定仕様か？**  
   **列欠落フォールバック**。暫定の「Trigger 固定ポリシー」ではないが、欠列常態下では **恒常値として振る舞う**。

3. **設計との差分（要約）**  
   - 生成ロケーション: pace_model ≠ Core FG  
   - 搬送: 116 列 legacy daily → 72–74 列 slim daily  
   - 値: 可変 difficulty → 定数 0.5  
   - モジュール: ローカル/スクリプト残存、Production platform 不在  

---

## Guardrails

- 契約差分の記録のみ。契約変更・実装なし。
