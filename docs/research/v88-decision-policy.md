# Version88 — World Decision Policy Study

**Date:** 2026-07-28  
**Status:** Investigation / Design ONLY — **実装禁止**  
**Parents:** V87（World Prior は Global に対し統計的優位未証明） / V80–V86（Prediction・Calibration での World 優位は未確立） / V43 Semantic / V75–V77 Readiness  
**Locks:** Prediction 順位 **変更禁止** / Production / PE スコア再計算 を本フェーズで行わない

---

## 問題設定

V87 まで:

| 層 | World の証明状況 |
|---|---|
| Prediction（順位・Score） | 優位性なし（V80 単体 Strategy 失敗、Interaction→Rank 未採用） |
| Calibration（p_base / Prior） | 改善の主因は **Global 再スケール**寄り。World 固有は INCONCLUSIVE（V87） |

未検証:

> World を **Prediction 後の Decision Layer**（買う・見送り・プール・説明）の切替に使う価値はあるか？

本フェーズは **価値仮説の整理**まで。実装・効果の Shadow 実測は別 Decision。

---

## 層分離（必須）

```text
[Prediction Layer]  ※本フェーズで変更しない
  Legacy / fixture rank・score 固定
  World は順位・Score に作用しない

[Decision Layer]    ※本調査の対象（設計のみ）
  CEW World Label（読取）
    → Ticket Strategy
    → Confidence Policy（表示・閾値・見送り。順位非変更）
    → Risk Policy
    → Candidate Pool（表示・候補集合。順位非変更）
    → Explanation
```

| 禁止 | 許容（設計上） |
|---|---|
| Rank の入れ替え | 同一順位のまま「買う/見送り」 |
| Score の再計算で順位変更 | Confidence 帯のラベル付け（表示） |
| PE 本体の World Weight | チケット枚数・券種・サイズの方針 |
| World Prior を p_base に焼き直し（V87 未証明のまま本番化） | 説明文・注意喚起の切替 |

---

## Decision Layer 五軸の定義

| 軸 | 意味 | Prediction 非干渉の条件 |
|---|---|---|
| **Ticket Strategy** | 単勝/複勝/流し/見送り、枚数・フォーメーション方針 | 馬順は入力のまま。券種・サイズのみ |
| **Confidence Policy** | 表示 confidence・閾値・「強い/弱い」ラベル | 順位非変更。数値を変えても **並び替えに使わない** |
| **Risk Policy** | 最大損失・同時購入制限・World 別リスク予算 | 購入ゲートのみ |
| **Candidate Pool** | UI/説明上の注目馬集合（TopK 拡張・縮退） | Pool は表示集合。公式ランキング配列は不変 |
| **Explanation** | なぜこの World か、何を過信しないか | テキストのみ |

---

## World 別 Decision Policy

### `rank7_world`（Ready・n=65）

| 軸 | Policy（設計） |
|---|---|
| **Ticket** | **分散寄り**。本命一本勝ちを前提にしない。単勝厚買い抑制、複勝・相手広めを既定。多頭（field_size 大）ではさらに枚数分散。 |
| **Confidence** | Top1 能力一本の「高確信」表示を **抑制**。history×win_prob 同格の注意ラベル。Global conf は使ってよいが「混戦」タグ必須。 |
| **Risk** | 単レース予算を **中**。連敗時も本命倍プッシュ禁止（混戦前提と矛盾）。 |
| **Candidate Pool** | 公式 Top1 は維持しつつ、**表示 Pool を Top3–5 に拡張**（相手候補の可視化）。順位配列自体は不変。 |
| **Explanation** | 「展開・混戦寄り。能力一本を過信しない」。逃げ/先行言及可（V74）。 |

**Decision 価値仮説:** Prediction を動かさずとも、「買い方・見せ方」で混戦语义を運用に載せられる。

---

### `midhole_world`（Partial・n=24）

| 軸 | Policy（設計） |
|---|---|
| **Ticket** | **履歴候補を相手に含める**方針。win_prob Top1 単勝偏重を禁止（V75）。 |
| **Confidence** | win_prob 主導の高確信を **減衰表示**。history 文脈の注記。 |
| **Risk** | 標本 Partial → 予算 **控えめ**。Pilot 前提の自動購入は禁止（設計）。 |
| **Candidate Pool** | Top1 固定のまま、**中位帯・history 上位を Pool に追加表示**（公式順は不変）。 |
| **Explanation** | 「中位帯開放。上位能力一本を相対的に弱く読む」。 |

**Decision 価値仮説:** rank7 との **符号差**（field_size×win_prob 等）は説明・Pool 拡張に使い、順位には使わない。

---

### `unsatisfied`（Ready Residual・n=176）

| 軸 | Policy（設計） |
|---|---|
| **Ticket** | **デフォルト／保守**。特殊券種への誘導なし。市場＋能力ベースライン購入のみ。 |
| **Confidence** | 勝ち筋ラベルを付けない。Global / 汎用 conf 表示。 |
| **Risk** | 標準リスク。World 固有ブーストなし。 |
| **Candidate Pool** | 公式 TopK のまま（拡張しない）。 |
| **Explanation** | 「特定 World 未充足（残余）。独自勝ち筋を主張しない」。 |

**Decision 価値仮説:** 「何もしない」ことの契約化＝誤った勝ち筋 Ticket を防ぐ（負の価値＝過介入防止）。

---

### `core_world`（Blocked / PROVISIONAL・n=8）

| 軸 | Policy（設計） |
|---|---|
| **Ticket** | **仮説のみ**: 能力決着なら単勝寄り可。ただし n 不足で **自動適用禁止**。 |
| **Confidence** | 高確信を主張しない（標本不足）。 |
| **Risk** | **見送り or 最小**を既定。 |
| **Candidate Pool** | 公式のまま。拡張しない。 |
| **Explanation** | 「能力決着仮説だが標本不足。Decision 自動適用外」。 |

---

### `midupper_world` / `mixed_world`（Blocked・n=6）

| 軸 | Policy（設計） |
|---|---|
| **Ticket / Risk** | 自動 Decision **禁止**。Legacy デフォルト。 |
| **Confidence / Pool** | 非カスタム。 |
| **Explanation** | midupper: 上位帯＋展開＋適性（未測多）。mixed: 複数筋・単一方針禁止 — 説明のみ可。 |

---

### `bug_world`（n=0）

| 軸 | Policy |
|---|---|
| 全軸 | **未定義**。出現時は例外フラグ＋見送り（設計）。 |

---

## Decision 価値の評価軸（将来 Shadow・本フェーズ非実施）

Prediction Hit ではなく:

| 指標 | 意味 |
|---|---|
| Policy Compliance | World 別 Forbidden Ticket の回避率 |
| Overconfidence Incidents | 高確信表示後の外れ（表示ポリシー） |
| Pool Coverage | 拡張 Pool 内に勝馬が含まれる率（順位非変更のまま） |
| Explanation Faithfulness | 语义と説明の一致（人手/監査） |
| Risk Drawdown | World 別予算ルール下の損失 |

**Go の考え方（将来）:** Prediction 非劣化 ∧ Decision 指標の改善。本フェーズでは未測定。

---

## 結論（調査）

1. World を Prediction/Calibration の主エンジンにする根拠は V87 まで **不足**。  
2. World の残余価値仮説は **Decision Layer**（Ticket / 表示 Confidence / Risk / Pool / Explanation）に移すのが一貫する。  
3. 最有望は **rank7（分散 Ticket＋Pool 拡張＋過信抑制）** と **unsatisfied（過介入防止）**。  
4. midhole は説明・Pool に有用だが Ready ではないため自動 Decision は条件付き。  
5. **実装はしない。** 次は Decision Shadow（別 Decision）。
