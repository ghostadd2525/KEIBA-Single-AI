# Version36 — World → PE Integration Design

**Status:** Architecture only — **not implemented**  
**Date:** 2026-07-28  
**Parents:** V32 ADR / V33 WIC / V34 Shadow AB / V35 PE Dependency Audit  
**Scope lock:** Prediction / PE / CE / AI / World / SubWorld / Role / Required / Candidate Pool / Challenge / ResultAutomation / Production — 変更禁止

---

## Purpose

V35 により現行 Production は次であることが証明された:

```text
Feature → Scorer → Ranker → Prediction → WorldClassifier（事後ラベル）
```

本フェーズは、設計思想

> **World は AI 最上流の勝ち筋分類である**

に立ち返り、World が勝ち筋を決定する層になる場合の **正しい接続点** を設計する。実装・改善は行わない。

---

## Proven current vs intended

| | Current (V35) | Intended (design chain) |
|--|---------------|-------------------------|
| Order | Rank → Prediction → World | World → … → PE → Prediction |
| World role | Annotator / label | Win-path decision |
| PE input | Features only | World / policy / constrained set |
| Pool vs PE | Pool is **downstream** of score | Pool is **upstream** of PE |
| Prediction | World dropped (`predict_ranking` / mapper `None`) | World-conditioned outcome |

---

## Document index

| Doc | Content |
|-----|---------|
| `v36-world-pe-integration.md` | 本ファイル（概要・判定） |
| `v36-integration-options.md` | ①② 接続候補と影響分析 |
| `v36-boundary-analysis.md` | ③④ 本来フロー復元 + WIC Consumer 境界 |
| `v36-risk-analysis.md` | ⑤⑥ 移行難易度 + 影響範囲 |
| `v36-recommendation.md` | ⑦ 単一推奨案と理由 |

---

## Final verdict

### **C — World should integrate before PE**

World の勝ち筋決定は、**PE（Scorer/Ranker / Prediction top pick）の入力契約に入る**ことで初めて Prediction に効く。  
Candidate Pool 前への接続だけでは（V35）、現行 PE が全馬スコアする限り Single Prediction は動かない。

詳細根拠: `v36-recommendation.md`。

**Rejected:**

| Verdict | Why |
|---------|-----|
| **A** | 現行はラベル後付けであり設計思想に反する（V35-C） |
| **B alone** | Pool 前接続は Win5 選択には自然だが、PE 非消費のままでは Prediction 不変 |
| **D** | 複合案は移行設計として有用だが、**主接続点は1点に固定**する本フェーズでは C を正とする |

---

## Guardrails

- Architecture Design only. No implementation.
- Does not reopen V34 Signal Service GO/NO-GO; this phase answers **where** World binds to PE, not **whether** to ship Signal Service.
