# Version68 — Logic Form Candidates（構造のみ）

**Date:** 2026-07-28  
**Status:** Design candidates — **未実装・閾値なし・Signal 追加なし・World 変更なし**  
**Notation:** `S↑`/`S↓` = 既存極性（V44）。数値カットオフは書かない。

---

## 共通原則（候補に共通）

1. World Meaning / Polarity は固定。  
2. Must を Aux で埋めない。  
3. `count(MATCH)==0 → unsatisfied`（core DEFAULT 禁止）。  
4. `count(MATCH)≥2 → mixed` 優先（V44 Conflict Resolution）。  
5. first-match 固定優先表より、**MATCH 集合 → 解決**の Decision Tree を推奨。

---

## Candidate A — Spec-Aligned Forms（V44 直写・構造）

### R7 相当（midupper）— difficulty 単独を廃止

```text
# BEFORE (現行)
R7 := difficulty↑

# AFTER (構造候補)
MIDUPPER_MATCH :=
    UPPER_AXIS↑          # 既存概念: upper_ability_band 等
    AND DEV_AXIS↑        # 既存概念の OR: phase / sfp / high_pace 等
    AND APT_AXIS↑        # 既存概念: aptitude 系（供給欠は unsatisfied、Must を埋めない）
AND NOT MIDUPPER_EXCLUDE

# difficulty は AUX のみ
MIDUPPER_AUX := support(difficulty 中〜)
```

**構造変化:** 単一 AND → **3-AND Must** + Exclude。difficulty を Must から外す。

### R1 相当（mixed）— 圧力 OR を Must から外す

```text
# BEFORE (現行)
R1 := sfp↑ AND (phase↑ OR chaos↑ OR difficulty↑)

# AFTER (構造候補)
MIXED_MATCH :=
    ( count(PRIMARY_WORLD_MATCH) >= 2 )     # MULTI_PATH — OR は「勝ち筋」単位
    OR UNEXPLAINED_SINGLE
AND NOT ( exactly_one_clear_path )

MIXED_AUX := support( sfp↑ AND concurrent(phase, chaos, difficulty) )
# Aux は Must を置換しない
```

**構造変化:**  
- OR の対象を「圧力 Signal」→「複数 World MATCH」へ変更。  
- 現行 R1 の圧力 AND/OR は **Aux バンドル**へ降格。  
- Priority=1 の first-match 特権を廃止し、集合解決へ。

### R8 相当（core）— DEFAULT 廃止 → Positive Match

```text
# BEFORE (現行)
R8 := DEFAULT → core

# AFTER (構造候補)
CORE_MATCH :=
    top_gap↑ AND ability_separation↑     # 既存 ranking_concepts（新種 Signal ではない）
    AND NOT CORE_EXCLUDE

# 残余
if no CORE_MATCH and no other MATCH:
    → unsatisfied          # NOT core
```

**構造変化:** DEFAULT 削除。Positive Match AND + Exclude。残余は unsatisfied。

---

## Candidate B — Decision Tree（Priority 表の置換）

現行: 固定順序 R1→…→R8 first-match。

```text
                    evaluate all WORLD_MATCH (positive forms)
                              │
              ┌───────────────┼───────────────┐
         |M| = 0          |M| = 1          |M| ≥ 2
              │               │               │
         unsatisfied      that World        mixed
```

| 現行 Priority | 候補 |
|---|---|
| R1 最優先 | 廃止（mixed は集合サイズで決定） |
| R7 遅い midupper | midupper は独自 MATCH（順序非依存） |
| R8 DEFAULT | 葉ノードは unsatisfied のみ |

---

## Candidate C — 最小構造差分（Still structure-only）

思想完全一致より「禁止形の除去」を最小限にする案。

| Rule | 最小差分 |
|---|---|
| R7 | `difficulty↑` を **Must から外し**、`DEV_AXIS` の **support のみ**に格下げ。MATCH は `UPPER AND DEV AND APT` が揃うまで立てない（揃わなければ unsatisfied） |
| R1 | `sfp AND OR(pressure)` を **MATCH から削除**し Aux 化。mixed MATCH は multi_path のみ |
| R8 | `DEFAULT→core` を削除し、`CORE_MUST AND NOT EXCLUDE` のみ。失敗時 unsatisfied |

Threshold 再調整は **含めない**。

---

## 非候補（本レビューで却下）

| 案 | 却下理由 |
|---|---|
| difficulty 閾値だけ変える | V67: 主因は構造。Threshold 禁止 |
| OR に新 Signal を足す | Signal 追加禁止／思想の OR 対象が違う |
| World 意味の再定義 | World 固定 |
| DEFAULT を残しつつ Aux で補正 | V44 FORBIDDEN_FORM |

---

## 比較表

| 項目 | 現行 | Candidate A/B/C |
|---|---|---|
| R7 | difficulty 単独 | 3-AND Must（difficulty は Aux） |
| R1 OR | 圧力 Signal の OR | 勝ち筋 multi_path の OR／圧力は Aux |
| R8 | DEFAULT→core | Positive Match／残余 unsatisfied |
| Priority | 固定 first-match | MATCH 集合 Decision Tree |
| Threshold | （実装に存在） | **触らない** |
| 新 Signal 種 | — | **追加しない** |
