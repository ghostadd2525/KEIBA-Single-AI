# Version8.5.1 Final Certification

**Date:** 2026-07-27 (JST)  
**Purpose:** Version8.5.1 を正式 Production Baseline として認証する  
**Scope:** CONDITIONAL 項目のみ（Version9 機能追加なし）  
**Commit Hash:** `0972afb1cb1e0979255a0b48c2ae8c967279ccca`  
**Parent:** [`v851-baseline-certification.md`](./v851-baseline-certification.md) · [`system-regression-audit.md`](./system-regression-audit.md)

---

## Executive Result

| Gate | Result |
|------|--------|
| **Version8.5.1 Certification** | **PASS** |
| **Boundary** | **PASS** |
| **Regression** | **PASS** |
| **Security** | **PASS** |
| **Baseline Integrity** | **PASS** |

**Production Baseline:** **Version8.5.1**（[`docs/baselines/Version8.5.1.md`](../baselines/Version8.5.1.md)）

---

## 1. AbilityScores Exception

| 項目 | 内容 |
|------|------|
| 判定 | **正式採用**（差し戻しなし） |
| ADR | [`docs/adr/ADR-007-abilityscores-overlay.md`](../adr/ADR-007-abilityscores-overlay.md) |
| Registry | `docs/baselines/Version8.5.1.md` Exception 欄 |
| コード | `candidate_evaluation/__init__.py` + `piPredictionMapper.js` |
| PE / Rank / Confidence | **非変更**（透過のみ） |

Hard Lock 例外として登録完了 → Baseline Integrity **PASS**

---

## 2. Security Remediation

### 2.1 stub JWT role escalation — PASS

| 対策 | 実装 |
|------|------|
| role 昇格禁止 | `makeStubToken` は role 非埋込。`verifyStubToken` は role claim 破棄 |
| resolveAuthorization | `session.role` / token.role **不採用**。正本は profile + allowlist |
| 本番利用不可 | `EXPECT_ENV=production\|prod` かつ `ALLOW_STUB_AUTH!=1` で stub → `STUB_AUTH_FORBIDDEN` |
| 共有入口 | `requireAccessSession` |

### 2.2 isAdminUser fail-open → fail-closed — PASS

| 対策 | 実装 |
|------|------|
| 共有 | `functions/_lib/adminAuth.js` |
| 空 allowlist | admin ではない（`return false`）→ 403 |
| 判定不能 | USER / 403 |
| 適用 | dashboard / research-scheduler / result-automation / v71-metrics / conversation / portal / invitations |

静的検査: `if (!ids.length) return true` 残存 **0**

### 2.3 /api/ops/conversation authorization — PASS

| 経路 | 内容 |
|------|------|
| Session | `requireAccessSession`（JWT/stub ポリシー） |
| Role | `resolveAuthorization` |
| Allowlist / profile | `isAdminUser` fail-closed |
| Maintenance | 既存 `_middleware.js`（OPS CLOSED + ADMIN bypass） |

非 ADMIN → **403**

---

## 3. Re-Audit Results

### Boundary Audit — PASS

- Research `production_auto_apply: false` 維持
- PE `v2_pool_entry_v2.py` / research CE **hash SAME vs pre-change HEAD**
- RA / Research Runner ロジック非変更（本フェーズ対象外・未改変）
- AbilityScores は CE overlay 透過 Exception のみ

### Regression Audit — PASS

- Version9 機能追加なし
- 変更は Security + AbilityScores 正本化 + Registry/ADR のみ

### Security Audit — PASS

- SEC-01 / SEC-02 / SEC-03 すべて対策済み（上記）

### Baseline Integrity — PASS

- AbilityScores = ADR-007 Exception
- Hard Lock 本体（PE / scoring）非侵害

---

## 4. Known Limitations（Certified）

1. **署名 JWT 未実装** — 本番 identity は当面 `ALLOW_STUB_AUTH=1` のブレークグラスが必要。role 昇格経路は閉じ済み。  
2. Ops Knowledge/Deploy 週次 JSON 未公開 — No Data（8.5.1 範囲外）  
3. `AUTH_MODE` 非 stub 時の検証器は未実装（`AUTH_MODE_UNSUPPORTED`）— JWT 導入は別リリース

---

## 5. Artifacts

| Artifact | Path |
|----------|------|
| Final Certification | `docs/audit/v851-final-certification.md` |
| Baseline 8.5 | `docs/baselines/Version8.5.md` |
| Baseline 8.5.1 | `docs/baselines/Version8.5.1.md` |
| ADR | `docs/adr/ADR-007-abilityscores-overlay.md` |

---

## 6. Conclusion

Version8.5.1 は正式 **Production / Operations Baseline** として認証する。

*PE / CE scoring / AI / ResultAutomation / Research / Production Logic の新規変更は行っていない。*
