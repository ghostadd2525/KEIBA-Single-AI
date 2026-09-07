# UI8 — Home「今日の本命」

**Date:** 2026-07-30

## 方針

- **既存** `.ai-card--predict` を流用（新規カードなし）
- 一覧と同じ UI8 自信度（ラベル + score → ★/文言）を使う

## 選出

1. 当日 Prediction bundles を取得  
2. 各レースの表示 band を算出  
3. 候補: **★★★★☆（rather_high）以上**（`high` / `rather_high`）  
4. 候補の中で **confidence score 最大** の 1 件  
5. 候補ゼロ → 空状態（`races.html` へ誘導、文言「本日 ★★★★☆ 以上の候補がありません」）

## カード表示内容

| 要素 | 配置 |
|---|---|
| 競馬場・レース番号・レース名 | `.ai-desc`（例: `新潟 2R · 2歳新馬`） |
| ★ | `.ai-gauge-num`（既存ゲージ枠） |
| 文言（高い / やや高い …） | `.ai-gauge-label` |
| 「本命を見る ›」 | 既存 `.ai-pill` |
| リンク | `race.html?race_id=…`（空時は `races.html`） |

## 実装

- `pickHomeTodaysHonmei(bundles)`（`prediction-bind.js`）
- `index.html` `paintHonmeiFromBundles` がこれを呼ぶ
- キャッシュキー: `expect_home_honmei_v2`（band/stars を保持）

## 非変更

- カード DOM 構造の新設なし
- Core / Prediction / Race List Cache / 新規 API なし
