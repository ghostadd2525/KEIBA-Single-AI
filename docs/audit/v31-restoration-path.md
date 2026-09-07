# Version31 — Restoration Path Map (Audit Only)

**Date:** 2026-07-27  
**注意:** 経路の **地図**のみ。実装・CSV 修正・FG/Loader/Trigger/World 変更は禁止。

---

## Break point (from this audit)

```text
pace_model 出力 ──┐
                  ├─(legacy)→ 116 CSV ─(旧 daily)─┐
market merge ─────┘                               │
                                                  X  ← 断絶: daily writer 置換
pi build_features ──────────────→ 72/74 daily ────┤
                                                  ▼
                                         FeatureLoader (daily first)
                                                  ▼
                                              World / Ranker defaults
```

断絶は Loader でも Trigger でもなく、**daily CSV 生成器が pace_model を呼ばない点**。

---

## Hypothetical restoration paths（未実施）

| ID | Path | Touches | Restores design cols? | Notes (audit) |
|----|------|---------|:---------------------:|---------------|
| P1 | 再配線: daily writer が legacy `build_pace_features` + merge を呼ぶ | race_refresh / ops | Yes（フル） | 設計グラフに最も忠実 |
| P2 | `build_features` に pace_model 相当を追加 | pi features | Yes if complete | docstring/契約の再定義が必要 |
| P3 | FeatureGenerator で `add_win5_*` 再計算 | Core FG | Partial→Full | V30: 設計主契約とズレ；入力欠列リスク |
| P4 | Loader を global 116 優先に変更 | Loader | Only if race in global | 日付カバレッジ・鮮度問題 |
| P5 | daily 72 を手で 116 にパッチ | CSV | Ad-hoc | 本フェーズ禁止；再現性なし |

**本ドキュメントは P1–P5 を推奨しない。** 断絶位置の明示のみ。

---

## What must be true for design-equivalent CSV

Upstream of Loader, daily frame needs at least:

- `race_leg_difficulty`（設計式由来）
- `pace_collapse_risk`（または明示契約された別名ブリッジ — 現状なし）
- `style_entropy`
- `horse_count`（または契約された `field_size` エイリアス — 現状なし）
- Ranker 28 の他 leg_* / `front_count` 等（JSON 準拠）

現状 72/74 は上記を満たさない。

---

## Non-paths（誤解の排除）

| Misconception | Fact |
|---------------|------|
| 「Slim 関数を戻せば直る」 | Slim 関数は無い |
| 「07-25 unblock が列を削った」 | bak 時点で既に 72；unblock は行マージ |
| 「Loader が列を落としている」 | Loader は CSV 列を透過読込 |
| 「global 116 が日常の正本」 | Loader は daily 優先 |

---

## Relation to V30 readiness

V30 = **B Further Investigation Required**  
V31 が閉じた調査項目:

| V30 open item | V31 result |
|---------------|------------|
| F1 07-25 72 列化の意図 | 生成器置換（PI history port）。列 Slim 文書なし。運用正本は PI daily |
| F2 復元ロケーション | 断絶点は **daily writer / build_features**（P1/P2 がグラフ上の直接点）。FG は二次 |
| F3 `*_v2` 関係 | 別名併存；設計 `pace_collapse_risk` とは未接続 |

未解決のまま（実装ゲート外）: どの Path を採用するかの **意思決定**。

---

## Deliverables index

| Doc | Role |
|-----|------|
| `v31-csv-contract.md` | 断絶点・パイプライン |
| `v31-column-removal.md` | 欠落列・理由 |
| `v31-schema-diff.md` | 07-25 前後差分 |
| `v31-contract-owner.md` | 116 vs 72 正本証明 |
| `v31-restoration-path.md` | 本ファイル（経路地図のみ） |

---

## Guardrails

- Audit 完了。復元実装なし。CSV / FG / Loader / Trigger / World 未変更。
