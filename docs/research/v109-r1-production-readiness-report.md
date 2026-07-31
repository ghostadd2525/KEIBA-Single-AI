# Phase R1 — Production Readiness Report

**Date:** 2026-07-29

---

## Readiness matrix

| Area | Status | Notes |
|---|---|---|
| Race List Cache lock | **PASS** | 非変更 · 一覧 Single なし |
| Detail wiring deployed | **PASS** | Flag OFF 既定 |
| Ops metrics/alerts code | **PASS** | ALT-SD* · `/api/ops/single-detail` |
| Live Flag ON rehearse | **PASS** | ADMIN · fallback 正常 |
| Flag default OFF restored | **PASS** | |
| Platform health overall | **PARTIAL** | BFF degraded（RA / 他 probe） |
| On-call sign-off | **PENDING** | 人間承認 |
| Permanent Cutover Flag ON | **NOT READY** | 下記 Recommendation |

## Safe vs Cutover

| Mode | Ready? |
|---|---|
| **Release code with Flag OFF** | **Yes — done** |
| **Cutover = Flag ON for all users** | **No**（Research Week・platform degraded・明示承認なし） |

## Monitoring checklist（R1）

| Item | Observed |
|---|---|
| Health | degraded（allow_stub_auth ok） |
| Monitoring | `/api/ops/monitor` includes `single_detail_ops` |
| Alert | SD alerts deferred at 0 traffic（expected） |
| Metrics | endpoint live · isolate caveat |
| Dashboard | single_detail block present |
