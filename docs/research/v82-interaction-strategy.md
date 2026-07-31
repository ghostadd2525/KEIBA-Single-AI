# Version82 — Interaction Strategy Design

**Date:** 2026-07-28  
**Status:** Design Specification ONLY — **実装禁止 / PE・Production・Trigger・Blueprint 変更禁止**  
**Parents:** V81 Feature Interaction Discovery / V80 Attribution（単体 Weight Strategy = Hit−133） / V75 Strategy（参照・単体優先は本版で廃止）  
**Corpus:** 285R CEW  
**対象 World:** `rank7_world` / `midhole_world` / `unsatisfied` / `core_world`

---

## 設計原則（V82）

1. **基本単位は Interaction**（2-way / 3-way）。単体 Feature Weight 表は Strategy として **廃止**（V80 根拠）。
2. World は **Interaction Selector** である。同一ペアでも World 間で Must / Forbidden が異なり得る（V74 符号差・V81 順位差）。
3. 原子特徴（history / win_prob / …）は Interaction の **構成要素**に限り言及する。単独ランキング・単独加点を定義しない。
4. 3-way は 2-way Must の **強化・文脈化**であり、2-way と競合したら Priority 表に従う。
5. n\<20（`core_world`）は **PROVISIONAL**。Ready / Pilot 主張に使わない。
6. Hit / Purchase / PE 写像は本フェーズの非目的。適合判定は Contract 遵守のみ。

---

## 単体 Weight 廃止宣言

| 旧（V75/V80 Shadow） | V82 |
|---|---|
| 優先特徴 1位=`history_z` 等の単体順位 | **禁止** |
| 単体係数の線形合成を Strategy 本体とする | **禁止** |
| Interaction を「補助文脈」として後付け | **逆転**: Interaction が本体、単体は構成要素のみ |

V80: ΔStrategy Hit = −133（単体 Weight 寄り Shadow）。→ Strategy 再設計の単位を Interaction に移す。

---

## World Strategy 一文

| World | n | Status | Strategy 一文 |
|---|---:|---|---|
| `rank7_world` | 65 | ACTIVE | **history×win_prob** 同格バンドを Must とし、**history×odds×win_prob** で三重強化。能力一本・単体 Weight 禁止。 |
| `midhole_world` | 24 | ACTIVE（Partial 標本） | **win_prob×field_size** を主ゲートとし、**history×pace** / **history×field_size** で履歴文脈を読む。rank7 同格バンドのコピー禁止。 |
| `unsatisfied` | 176 | ACTIVE（Residual） | **history×win_prob** を汎用ベースライン Interaction とし、勝ち筋 World 主張はしない。 |
| `core_world` | 8 | PROVISIONAL | **win_prob×odds** を仮 Must。n 不足のため確定 Strategy にしない。 |

---

## Interaction 優先整理（World 別）

### `rank7_world`

| Pri | Type | Interaction | Role | V81 根拠（要約） |
|---:|---|---|---|---|
| P0 | 2-way | `history × win_prob` | **Must** | Champion / Lift 1.29 / SHAP-proxy 相対高 |
| P1 | 3-way | `history × odds × win_prob` | **Must**（強化） | Lift 1.84・横断トップ級 |
| P2 | 2-way | `odds × ability_sep` | Aux | MI 高・Lift 1.29 |
| P3 | 2-way | `history × odds` | Aux | Lift 1.23 |
| P4 | 2-way | `win_prob × odds` | Aux | SHAP-proxy 高・Lift 1.23 |
| P5 | 2-way | `odds × upper_band` | Aux | Lift 1.29 |
| P6 | 3-way | `history × upper_band × odds` | Aux | Lift 1.41 |
| — | 2-way | `win_prob × field_size` | **Forbidden as Must** | Lift 0.80（弱）・V74 多頭減衰は別契約で扱うが midhole 主軸の転用禁止 |

### `midhole_world`

| Pri | Type | Interaction | Role | V81 根拠（要約） |
|---:|---|---|---|---|
| P0 | 2-way | `win_prob × field_size` | **Must** | Champion / MI 0.036 最大級 |
| P1 | 2-way | `history × pace` | **Must** | Lift 1.33 |
| P2 | 2-way | `history × field_size` | Aux→準 Must | Lift 1.33 |
| P3 | 3-way | `win_prob × field_size × pace` | Aux（強化） | Lift 1.50 |
| P4 | 3-way | `history × field_size × top_gap` | Aux | IG 相対高 |
| P5 | 3-way | `history × odds × win_prob` | Aux | Lift 1.66（汎用三重・World 固有 Must にはしない） |
| — | 2-way | `history × win_prob`（rank7 同格主張） | **Forbidden as Must** | Lift≈1.0・Champion ではない |
| — | 2-way | `win_prob × upper_band` 強化 | **Forbidden** | Lift 0.33・V74 符号は減衰側 |

### `unsatisfied`

| Pri | Type | Interaction | Role | V81 根拠（要約） |
|---:|---|---|---|---|
| P0 | 2-way | `history × win_prob` | **Must**（Baseline） | Champion / Lift 1.43 |
| P1 | 2-way | `win_prob × odds` | Aux | Lift 1.34 |
| P2 | 2-way | `history × odds` | Aux | Lift 1.25 |
| P3 | 2-way | `win_prob × field_size` | Aux | Lift 1.27 |
| P4 | 3-way | `history × win_prob × odds` | Aux（強化） | Lift 1.95 |
| P5 | 3-way | `win_prob × field_size × pace` | Aux | Lift 1.61 |
| — | — | rank7/midhole 固有 Must の転用 | **Forbidden** | Residual は勝ち筋主張なし（V44/V75） |

### `core_world`（PROVISIONAL）

| Pri | Type | Interaction | Role | V81 根拠（要約） |
|---:|---|---|---|---|
| P0 | 2-way | `win_prob × odds` | **Must（仮）** | Champion / Lift 1.47 |
| P1 | 2-way | `history × win_prob` | Aux（仮） | Lift 1.96・標本小 |
| P2 | 3-way | `history × odds × win_prob` | Aux（仮） | Lift 2.44・不安定 |
| P3 | 3-way | `win_prob × field_size × top_gap` | Aux（仮） | Gap 文脈仮説 |
| — | — | PE Ready / Pilot Must | **Forbidden** | n=8 |

---

## World 間 Separation（Interaction 軸）

| 対比 | Interaction 差 |
|---|---|
| rank7 vs midhole | rank7 Must = `history×win_prob`。midhole Must = `win_prob×field_size` + `history×pace`。同格バンドの相互コピー禁止。 |
| rank7 vs unsatisfied | 形は似る（`history×win_prob`）が、unsatisfied は **Baseline**、rank7 は **勝ち筋 Selector**。意味契約が異なる。 |
| midhole vs unsatisfied | midhole は field_size / pace ゲート必須。unsatisfied は市場×能力×履歴の汎用三重を Aux に留める。 |
| core vs 他 | `win_prob×odds` 仮 Must。他 World への確定転用禁止。 |

---

## 関連成果物

- `v82-interaction-contract.md` — Must / Aux / Forbidden
- `v82-interaction-priority.md` — Priority / Conflict / Fallback
- `v82-governance.md`
- 根拠: `v81-world-interaction-report.md` / `v81-top-interaction-ranking.md`
