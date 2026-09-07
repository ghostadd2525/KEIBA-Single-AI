# Version106 — Contract Gap Report

**Date:** 2026-07-28  
**Status:** Shadow Observation · **実装禁止**  
**Parents:** V106 Single/Win5 · V103 · V105 · ADR-009/010  
**非評価:** Prediction 改善 · Hit · ROI · Decision 最適化 · Evidence 追加 · 新 Semantic/Feature

---

## 総合 Verdict

| 項目 | 判定 |
|---|---|
| **Consumer Readiness** | **PARTIAL_READY** |
| Core Semantic 不足で新意味が必要か | **No** |
| Core Feature 追加が必要か | **No** |
| 主ギャップ種別 | **Wiring** + **Decision Registry / External 入力**（設計どおり Core 外） |

---

## Gap 分類

| Class | 意味 |
|---|---|
| **GAP-WIRE** | V103 PROMOTE の製品 serialize 未承認・未配線 |
| **GAP-REG** | Decision Policy / Expected Strategy レジストリ参照（KEEP_DERIVED） |
| **GAP-EXT** | Market / Race Card / 予算など Core 契約外入力 |
| **GAP-SEM** | Core 意味の欠落 → **本監査では 0 件** |
| **NON-GAP** | 要望はあるが既存 ADR で禁止または価値否定 |

---

## Gap 一覧

| ID | Consumer | 現象 | Class | 是正（許可範囲） | 禁止 |
|---|---|---|---|---|---|
| G106-01 | Both | Affinity/EC/Exclusion/NM Class が製品 payload 未 emit | GAP-WIRE | 別 Decision で V103 serialize のみ | Logic 変更・新意味 |
| G106-02 | Single 説明 | 自然文 why が Core に無い | NON-GAP | Presentation テンプレ（MS-6） | Core に NL 追加 |
| G106-03 | Single 券種/買い目 | 券種定数・stake が Core に無い | GAP-REG / GAP-EXT | Decision Registry + Market | Core に Ticket 載せる |
| G106-04 | Win5 候補数 | candidate_count フィールド無し | GAP-REG | World/NM → V88/V92 Pool 表 | 新 Semantic |
| G106-05 | Win5 保険 | insurance 構造が Core に無い | GAP-REG | Decision Risk/Ticket | Core 保険 Feature |
| G106-06 | Win5 難易度 | race_difficulty 無し | GAP-REG / GAP-EXT | World/NM/EC/field_size 合成 | `difficulty` Semantic 追加 |
| G106-07 | Both | Affinity で自動 Skip/保険したい | NON-GAP | 要件破棄（V97 NO_VALUE） | Affinity Decision 再燃 |
| G106-08 | Both | EC で候補数・Skip 閾値化 | NON-GAP | 説明警告のみ（V101） | 別契約なき閾値化 |
| G106-09 | Both | Expected Strategy 本文欠落 | GAP-REG | V75 レジストリ KEEP_DERIVED | race 固有本文新造 |

---

## Semantic Gap 判定（評価対象 8 項）

| Payload | Semantic Gap? | 注記 |
|---|---|---|
| World | No | 既 first-class |
| Near Miss | No | 定義固定。配線は GAP-WIRE |
| Affinity | No | 説明推奨。Decision 自動は NON-GAP |
| Near Miss Class | No | PROMOTE 定義済 |
| Exclusion Reasons | No | 説明必須。券種不要 |
| Explanation Confidence | No | 説明必須。閾値化禁止 |
| Transition | No | 説明必須/推奨 |
| Must Gaps | No | trace 内。説明必須 |

**GAP-SEM count = 0**

---

## Product vs Core Evidence（V105）

| 混同 | 本監査での扱い |
|---|---|
| Miss Evidence 不足を Consumer Gap と呼ぶ | **禁止**（EV-P ≠ Consumer Contract） |
| Completeness 欠落を Ticket 不足と呼ぶ | **禁止**（EV-S ≠ EV-D） |
| ROI Shadow 不足を Core Payload Gap と呼ぶ | **禁止** |

---

## 結論

1. **Core Contract は固定のままで Consumer 監査上「意味不足」ではない。**  
2. Single/Win5 の PARTIAL は、**Decision Registry・Market・Presentation・配線**による。  
3. 不足に見えても **KEEP_DERIVED / EXT / NON-GAP** に落ち、新 Semantic/Feature は不要。  
4. 次の実装候補（別 Gate）は **V103 PROMOTE serialize のみ**（本票は承認しない）。

---

## Related

- `v106-governance.md`
