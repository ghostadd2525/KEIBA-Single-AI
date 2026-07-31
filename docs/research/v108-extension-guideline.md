# Version108 — Extension Guideline

**Date:** 2026-07-28  
**Status:** Guideline · Shadow Validation · **実装禁止（本票）**  
**Parents:** ADR-011 · V103 · V105 · V106 · Core Platform Version1  
**目的:** 将来の拡張が ADR-011 境界を壊さない手順を固定する。  
**非目的:** 今すぐ Semantic / Feature / Decision / ROI を追加すること（本検証では禁止）。

---

## 一文

**拡張は「層を選んでから版を上げる」。Core Version1 の意味を黙って伸ばさない。**

---

## 1. 拡張種と正規経路

| 拡張種 | 正規層 | 手順（要約） | Core v1 への影響 |
|---|---|---|---|
| **新しい World** | Trigger 契約（別 ADR/Gate）→ Registry 行 | 1) World 意味契約 2) CEW ラベル 3) V88/V95 Policy 行 4) Consumer は `world_id` 追加値を許容 | 既存 world 意味 **不変**。列挙拡張は文書化 |
| **新しい Semantic** | ADR → V103 分類 | PROMOTE / KEEP_DERIVED / DO_NOT_EXPORT を先に決める。PROMOTE のみ Core minor 候補 | 意味新造を Version1 に黙入 ❌ |
| **新しい Decision** | Consumer / ADR-008 | Ticket/Pool/Risk/Explain モジュール内。Flag 新設可 | Core Payload に出力を載せない |
| **新しい Evidence** | V105 クラス内 | EV-P/S/D のどれかを明示。混在ストア禁止 | Core 契約非変更 |

---

## 2. チェックリスト（MUST）

拡張提案ごとに全て Yes であること:

| # | 問い |
|---|---|
| 1 | Core Version1 の既存フィールド意味を変えていないか |
| 2 | Consumer → Core 逆流が無いか |
| 3 | Ticket/難易度/NL を Core に載せていないか |
| 4 | Affinity/EC の禁止用途を解禁していないか |
| 5 | Evidence クラスを誤って跨いでいないか |
| 6 | 版空間（Core/Consumer/Evidence）のどれを上げるか明示したか |
| 7 | ADR-011 層図のどの箱に属するか一文で言えるか |

1 つでも No → **却下または別 ADR**。

---

## 3. 前方互換の既定

| 変更 | Consumer 期待動作 |
|---|---|
| Core に optional フィールド追加（承認後 minor） | 未知フィールド無視 |
| Registry に新 policy_id | 未知は Legacy/保守フォールバック |
| Consumer に新 DTO フィールド | 旧クライアント無視 |

---

## 4. 明示的に禁止する拡張パターン

| パターン | 理由 |
|---|---|
| Product 要望で Core に `difficulty` / `insurance` 追加 | V106 GAP-SEM=0; PCS-7 |
| 新 World を PE 重みに直結 | ADR-008/009 |
| Miss Evidence を新 Semantic の根拠に昇格 | V105 |
| 「小さな」意味変更を patch 版で隠す | CV1-1 |

---

## 5. Version1 期間の特別規則

本 Platform Readiness 採択期間:

- **Semantic 追加・Feature 追加・Decision 改善・ROI 改善は検証スコープ外かつ実行禁止**  
- 拡張ガイドラインは **将来 Gate 用の構造証明**であり、実行許可ではない  

---

## Related

- `v108-platform-readiness-report.md`
- `v108-versioning-policy.md`
- `v103-export-matrix.md`
- ADR-011
