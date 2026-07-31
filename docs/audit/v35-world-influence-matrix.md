# Version35 — World Influence Matrix

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only  
**Date:** 2026-07-28

---

## 評価尺度

| 等級 | 定義 |
|------|------|
| **High** | World 変化が当該モジュールの主出力を日常的に変える実装がある |
| **Medium** | World が分岐・ガード・メタに使われるが、主スコア/順位は不変 |
| **Low** | World を保持・表示するのみ、または稀な補助 |
| **None** | 参照なし、または明示的に破棄 |

---

## ⑤ Influence Matrix

| モジュール | World 影響度 | 根拠（要約） |
|------------|:------------:|--------------|
| **SubWorld** | **High** | `classify_sub_world_type` が World/meta 系と同一パイプラインで生成。ラベルとしては World と連動 |
| **Required** | **Low** | Role/Required は Win5 選択文脈。Core ranking 入力ではなく、World からの直接必須伝播は弱い |
| **Candidate Pool** | **Low〜Medium** | Pool 構築は `win_prob` 主。SubWorld/world meta は後段ガードで **Medium（購入）**、Pool 初期集合自体は **Low** |
| **PE（Prediction ranking / Scorer+Ranker）** | **None** | world 参照なし。Rank は World 前に確定 |
| **CE（CorePipeline + Projector）** | **Low** | World を **生成・添付**するが Rank/Confidence 本体は非ワールド。影響はメタ列のみ → **Low**（Producer だが Consumer ではない） |
| **Prediction（公開 / mapper）** | **None** | `predict_ranking` から欠落、`evaluation.world=None` |
| **Confidence** | **Low** | meta を受けるが、World ラベル自体が win_prob を書き換えない |
| **Win5 Purchase / re_pick / hard guard** | **Medium** | SubWorld/route 意図で除外・再ピック。Hit の model_rank は不変 |
| **WIC Shadow（Research）** | **High（ラベル）/ None（Hit）** | difficulty→World 再分類は動くが PE pick 凍結で Hit 影響 **None** |

### 視覚マトリクス（Prediction 因果に限定）

```
                World変化 → 出力変化?
SubWorld          High（ラベル）
Required          Low
Candidate Pool    Low (集合) / Medium (購入ガード)
PE ranking        None
CE rows           Low（Metaのみ）
Prediction        None
Purchase          Medium（本番 Win5）※V34 Shadow では未接続・凍結
```

---

## 解釈

- **ラベル系（SubWorld）:** World の影響は高い。  
- **予測系（PE / Prediction）:** World の影響は **None**。  
- **購入系:** Medium だが、V34 Shadow AB の Hit/Purchase 指標は PE pick 凍結により **観測上 None**。

この非対称が V34「World 54・Hit 0」と一致する。
