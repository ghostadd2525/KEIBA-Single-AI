# Version108 — Versioning Policy

**Date:** 2026-07-28  
**Status:** Policy（Shadow Validation）· **実装禁止**  
**Parents:** ADR-011 · V107 · V105 · Core Platform Version1 Freeze

---

## 一文

**Core / Consumer / Evidence は三つの版空間である。単一の「Platform 版」に畳み込まない。**

---

## 1. 版空間の定義

| Space | 識別子例 | Owner | 凍結（Version1 期間） |
|---|---|---|---|
| **Core** | `core-semantic-payload/v1` | Core Platform | **意味・Contract 凍結**。フィールド追加は別 Gate |
| **Consumer** | `consumer-api/single/v1` · `consumer-api/win5/v1` | Product | Core と独立に上げてよい |
| **Evidence** | `evidence/prediction/*` · `evidence/semantic/*` · `evidence/decision/*` | V105 Owners | クラス横断の単一版禁止 |
| **Registry** | `v75-expected-strategy` 等 | Decision/Contract | 参照キー。Core schema と非同期可 |

---

## 2. Core Version1 規則（MUST）

| ID | 規則 |
|---|---|
| CV1-0 | Platform Readiness 上の Core は **v1 固定** |
| CV1-1 | Prediction / World / NM / Affinity / EC の **定義変更は major 相当かつ本期間禁止** |
| CV1-2 | 導出 serialize の追加公開は **minor 候補**（別 Gate）。既存フィールド意味不変 |
| CV1-3 | 削除・型破壊は **major**。Consumer 移行完了まで v1 併存 |
| CV1-4 | 内部実装改善（再計算最適化等）は schema 非露出なら **版上げ不要**（契約非破壊） |

---

## 3. Consumer Version 規則（MUST）

| ID | 規則 |
|---|---|
| CN-0 | Single と Win5 は **別 schema 版** |
| CN-1 | Core フィールドをコピーして意味を変えない（別名なら Documentation） |
| CN-2 | Ticket/Coverage 等の追加は Consumer minor |
| CN-3 | Core major 採用時のみ Consumer が追随必須。Core minor は無視可能を既定（前方互換） |
| CN-4 | `core_ref.schema` + `payload_fingerprint` をレスポンスに保持（V107 CA-4） |

---

## 4. Evidence Version 規則（MUST）

| ID | 規則 |
|---|---|
| EV-0 | EV-P / EV-S / EV-D を同一 schema 版にしない |
| EV-1 | Core v1 上げと Evidence 版上げを自動連動させない |
| EV-2 | Consumer が Evidence を返す場合は **クラスラベル必須**（V105） |

---

## 5. 互換マトリクス（版）

| Core | Consumer | 許容 |
|---|---|---|
| v1 | single/v1, win5/v1 | ✅ 正規 |
| v1 | single/v1+minor | ✅ |
| v1.1 minor（将来・承認後） | v1 Consumer（新フィールド無視） | ✅ 前方互換 |
| v2 major | v1 Consumer | ❌ 併存期間のみ。移行後切断 |

---

## 6. 禁止

- 「Platform v2」一括ラベルで Core+Consumer+Evidence を同時破壊的更新  
- Consumer 版上げを理由に Core 意味変更  
- Evidence Miss 版を Core Completeness 版と同一視  

---

## Related

- `v108-compatibility-matrix.md`
- `v108-extension-guideline.md`
- ADR-011 §6
