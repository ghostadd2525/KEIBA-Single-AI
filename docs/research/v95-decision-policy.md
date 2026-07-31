# Version95 — Residual Decision Policy

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parents:** V95 Taxonomy · V88 Decision Policy · V91/V92 Decision Shadow（構造参考） · ADR-008  
**Locks:** Prediction / World / Trigger — **変更禁止** · Ticket は **保守帯のみ**（勝ち筋化禁止）

---

## スコープ

CEW=`unsatisfied` のとき、Decision Layer は **Taxonomy Metadata** を読み、次を切替える。

| 軸 | Near Miss | Pure Residual |
|---|---|---|
| **Ticket** | 保守（特殊券種誘導なし） | 保守（同一） |
| **Risk** | `near_world` に応じた **抑制プロファイル** | 標準保守 |
| **Candidate Pool** | `near_world` に応じた **表示注記付き TopK**（順位不変） | 公式 TopK のまま |
| **Explanation** | 近接 World ＋ Exclusion 明示 | 残余明示・勝ち筋主張なし |
| **Confidence 表示** | 勝ち筋高確信禁止。近接注意ラベル可 | 汎用のみ |

**共通 MUST:** Rank 配列・Score 配列は mutate しない（ADR-008 DL-C1）。  
**共通 MUST NOT:** unsatisfied を Positive 勝ち筋 Ticket 化しない（DL-C6）。

---

## A. Near Miss Policy

### A0. 共通（全 `near_world`）

| 軸 | Policy |
|---|---|
| **Ticket** | Legacy / ベースライン購入のみ。`near_world` の Ready Strategy（rank7 分散券など）を **コピー禁止**。 |
| **Risk** | 「MATCH していない」前提 → **予算・同時購入は near_world 本採用時より一段抑制**。自動強気禁止。 |
| **Pool** | 公式順位は不変。表示上「近接仮説の注意馬」を **注記**できても、Pool 拡張は **本採用 World 未満**。 |
| **Explanation** | 必須テンプレ: `near_miss:{near_world}` — 「{near_world} 仮説に近いが Exclusion により未 MATCH。勝ち筋確定ではない」。 |

### A1. `near_world = core_world`（n≈81）

| 軸 | Policy（設計） |
|---|---|
| **Risk** | **高抑制**。能力決着に見えても CEW 未充足 → 単勝厚買い・予算上振れ禁止。見送り閾値を標準より厳しくしてよい（設計）。 |
| **Pool** | Top1 公式維持。能力候補の過信表示をしない。「能力近接・未確定」タグのみ。拡張 Pool **禁止**（core 本採用ですら PROVISIONAL）。 |
| **Explanation** | 「能力決着に近いが Exclusion。標本・契約未充足のため本採用しない」。 |

**意図:** core は Blocked/PROVISIONAL（n=8）。Near Miss 81 を core Ticket に流用すると誤適用が拡大する。

### A2. `near_world = midupper_world`（n≈9）

| 軸 | Policy（設計） |
|---|---|
| **Risk** | **高抑制**（PROVISIONAL）。適性・上位帯の自動ブースト禁止。 |
| **Pool** | 公式 TopK のみ。適性根拠の追加候補表示は **説明文まで**（Pool 拡張しない）。 |
| **Explanation** | 「上位帯＋適性に近いが Exclusion。Decision 自動適用外」。 |

### A3. `near_world = midhole_world`（n≈13）

| 軸 | Policy（設計） |
|---|---|
| **Risk** | **中抑制**。midhole Ready 本採用の予算より低く。history 偏重 Ticket は禁止（本採用 Strategy のコピー禁止）。 |
| **Pool** | 公式 TopK 維持。history 上位の **注記のみ**可（表示集合の本格拡張は midhole CEW 時のみ）。 |
| **Explanation** | 「中位帯開放に近いが Exclusion。history 一本勝ちを主張しない」。 |

### A4. `near_world = rank7_world`（n≈1）

| 軸 | Policy（設計） |
|---|---|
| **Risk** | **中抑制**。rank7 本採用の分散 Ticket を **起動しない**（Near Miss ≠ rank7 CEW）。 |
| **Pool** | TopK 公式のまま。混戦注記のみ。Pool7 拡張は **rank7 CEW 専用**（V92）— Near Miss では適用しない。 |
| **Explanation** | 「混戦仮説に近いが Exclusion。rank7 Decision は適用しない」。 |

### A5. `near_world` 欠落・不明

`NEAR_MISS` なのに primary が取れない場合 → **Pure Residual と同じ保守 Policy** にフォールバック。

---

## B. Pure Residual Policy（`residual_class = PURE_RESIDUAL`）

V88 `unsatisfied` 保守 Policy を **明示的に継承・強化**する。

| 軸 | Policy（設計） |
|---|---|
| **Ticket** | デフォルト／保守。特殊券種・World 固有フォーメーションなし。市場＋能力ベースラインのみ。 |
| **Risk** | **標準保守**。World 固有リスクブーストなし。連敗時の攻撃的リカバリ禁止。 |
| **Candidate Pool** | 公式 TopK のまま。拡張しない。縮退もしない（予測配列尊重）。 |
| **Explanation** | テンプレ `pure_residual` — 「特定 World 未充足（真の残余）。近接勝ち筋も主張しない」。 |
| **Confidence 表示** | 汎用 / Global のみ。World タグ禁止。 |

**Decision 価値:** 過介入防止（負の価値の契約化）。V94 Must全失敗 72 件を「未証明の新 World」にしない。

---

## C. 対照表（運用一目）

| Metadata | Ticket | Risk | Pool | Explanation |
|---|---|---|---|---|
| NEAR_MISS / core | 保守 | 高抑制 | TopK＋能力未確定注記 | near_miss:core |
| NEAR_MISS / midupper | 保守 | 高抑制 | TopK のみ | near_miss:midupper |
| NEAR_MISS / midhole | 保守 | 中抑制 | TopK＋history 注記可 | near_miss:midhole |
| NEAR_MISS / rank7 | 保守 | 中抑制 | TopK＋混戦注記（拡張なし） | near_miss:rank7 |
| PURE_RESIDUAL | 保守 | 標準保守 | TopK のみ | pure_residual |

---

## D. ADR-008 との関係（設計解釈）

| 既存 | V95 解釈 |
|---|---|
| DL-C6 unsatisfied 勝ち筋 Ticket 化禁止 | **維持**。Near Miss も Ticket 勝ち筋化しない |
| world_id 切替 | **維持**。切替は Metadata 内。CEW は常に unsatisfied |
| Risk / Pool / Explain | Near Miss で **差分可**（本 Policy）。Ticket 差分は保守帯に閉じる |

将来 Shadow 実装時（別 Decision）の受け入れ条件案:

1. Prediction fingerprint 不変  
2. CEW 分布不変  
3. Ticket ROI/Buy が Near Miss で「本採用 World と同一」にならないこと（コピー検知）

---

## 関連

- `v95-residual-taxonomy.md`
- `v95-governance.md`
- `v88-decision-policy.md`（unsatisfied 保守の祖先）
- `v94-unsatisfied-residual-clustering.md`
