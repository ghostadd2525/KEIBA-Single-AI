# Baseline Registry — Version8.5

| Field | Value |
|-------|-------|
| **Baseline ID** | aseline-version-8.5 |
| **Version** | 8.5 |
| **Status** | LOCKED（Operations Baseline） / **superseded for Production by 8.5.1** |
| **Effective** | 2026-07-26 |
| **Commit Hash** | 155e6c7e2190d875a99f802de9e9e31e8ed80b99（main tip at lock declaration era; tag無し） |
| **Certification** | Operations Mode declared in docs/ops/v8-operations-baseline.md |
| **Boundary Audit** | Research → Production 自動適用禁止（production_auto_apply: false） |
| **Regression Audit** | docs/audit/system-regression-audit.md（8.5.1 直前） |
| **Security Audit** | CONDITIONAL 項目あり → 8.5.1 で解消 |
| **ADR** | （AbilityScores Exception は **未登録** — 8.5.1 で ADR-007） |
| **Exception** | なし（厳格 Hard Lock） |
| **Feature Flags** | 8_production_canary=false · 8_canary_*=false · 11_auto_maintenance=true |
| **Known Limitations** | stub AUTH_MODE · isAdminUser fail-open · conversation 無認可 · AbilityScores 未正本化 |

---

## Boundary

| 土日 Production | 月〜金 Research |
|-----------------|-----------------|
| ResultAutomation → results → Miss → Archive | Analyzer → … → 285R → Decision → Knowledge → Report |
| PE / CE / AI 変更 **禁止** | Production DB / Core Hot Patch **禁止** |

## Successor

正式 Production Baseline は **[Version8.5.1](./Version8.5.1.md)**。
