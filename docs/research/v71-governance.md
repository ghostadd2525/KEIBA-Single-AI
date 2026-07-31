# Version71 — Governance（Intent Ground Truth Audit）

**Date:** 2026-07-28  
**Verdict:** **C（Intent GT 非妥当 — Blueprint 非難不可）**  
**Type:** Research / Audit only  
**Locks:** Trigger / 実装 / Production — **変更なし**

---

## 判定理由

1. Intent GT（V65）は V43 Semantic / V44 Trigger Spec / V69 Blueprint と **同一定義ではない**。  
2. 主軸が **winner_model_rank 帯**であり、World=勝ち筋（V43 G1）および Positive Match（V44 T0）から乖離。  
3. V70 Intent Accuracy 低下（22.1%→8.8%）は、V65 時点の Shadow↔Intent **8.8%** と同型であり、**GT と Positive Match の固定ギャップの再測定**。  
4. 構造 KPI（DEFAULT 除去・difficulty 単独除去・rank7 Recall↑）は Blueprint 整合のまま。

---

【Decision】

| Item | Value |
|---|---|
| Action Type | Intent GT Audit（文書のみ） |
| Implementation Required | **No** |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No |
| Risk | None（読取のみ） |
| Expected Next Action | Intent GT 再定義の **Design Decision**（別フェーズ）／V70 Soft 禁止維持 |

---

## PASS / HOLD

| 項目 | 状態 |
|---|---|
| Trigger 非変更 | PASS |
| 実装非実施 | PASS |
| 4 者比較完了 | PASS |
| Intent GT を V43/V44/V69 と同一とみなす | **FAIL（監査結論）** |
| V70 Soft/Cutover 解除 | **HOLD**（GT 前提欠陥が残る） |

---

## 成果物

| Doc | Path |
|---|---|
| Intent GT Audit | `docs/research/v71-intent-gt-audit.md` |
| Intent Mapping | `docs/research/v71-intent-mapping.md` |
| Blueprint Consistency | `docs/research/v71-blueprint-consistency.md` |
| Governance | `docs/research/v71-governance.md` |

---

## 明示しないこと

- 新 GT の具体アルゴリズム実装  
- Trigger / V69 コード修正  
- Production Decision 変更  
