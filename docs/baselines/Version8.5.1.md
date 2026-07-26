# Baseline Registry — Version8.5.1

| Field | Value |
|-------|-------|
| **Baseline ID** | aseline-version-8.5.1 |
| **Version** | 8.5.1 |
| **Status** | **PRODUCTION BASELINE（Certified）** |
| **Effective** | 2026-07-27 |
| **Commit Hash** | PENDING_RELEASE_COMMIT |
| **Parent Baseline** | [Version8.5](./Version8.5.md) |
| **Certification** | [v851-final-certification.md](../audit/v851-final-certification.md) → **PASS** |
| **Boundary Audit** | **PASS** — Research production_auto_apply: false 維持。PE/RA/Research ロジック非変更 |
| **Regression Audit** | **PASS** — CONDITIONAL 項目のみ解消。Version9 機能追加なし |
| **Security Audit** | **PASS** — stub role 昇格禁止 · 本番 stub 原則禁止 · fail-closed admin · conversation ADMIN |
| **ADR** | [ADR-007](../adr/ADR-007-abilityscores-overlay.md) |
| **Exception** | **AbilityScores CE Overlay Passthrough**（Hard Lock Exception） |
| **Feature Flags** | 8_production_canary=false · 8_canary_*=false · 11_auto_maintenance=true · 8_research_enabled=true |
| **Known Limitations** | 署名 JWT 未実装のため本番は当面 ALLOW_STUB_AUTH=1 ブレークグラスが必要（identity のみ。role claim 無効）。Signed JWT は別リリース |

---

## What Version8.5.1 is

運用 Baseline のセキュリティ締めと AbilityScores Exception の正式登録。**Version9 機能追加は含まない。**

## Included changes

1. Security P0（stub / fail-closed / conversation ADMIN）
2. AbilityScores Exception（ADR-007 + git 正本）
3. Baseline Registry

## Hard Lock

| 領域 | 8.5.1 |
|------|-------|
| PE | 変更なし |
| CE scoring / Rank / Confidence | 変更なし |
| CE AbilityScores passthrough | **Exception 採用** |
| AI / ResultAutomation / Research | 変更なし |

## Certification Gate

| Gate | Result |
|------|--------|
| Version8.5.1 Certification | PASS |
| Boundary | PASS |
| Regression | PASS |
| Security | PASS |
| Baseline Integrity | PASS |
