# Stable Baseline — v1.0.0-stable

**Status:** **CLOSED / FROZEN**  
**Phase:** Version 1.0 正式クローズ → **運用継続**（新機能は 1.1 / research）  
**Date:** 2026-07-21  
**Freeze:** [`v1.0-freeze-declaration.md`](./v1.0-freeze-declaration.md)

---

## Baseline

| 項目 | 値 |
|------|-----|
| Git tag | `v1.0.0-stable`（**変更禁止**） |
| Commit | `08c7986904103d34b4570e013d628f7d3270d96c`（短縮 `08c7986`） |
| Branch | `main`（tip は docs 等で進みうる。本番は本 tag） |
| Release GO | 2026-07-21（本番スモーク後） |
| Completion | [`v1.0-completion-report.md`](./v1.0-completion-report.md) |
| Architecture | [`v1.0-architecture-snapshot.md`](./v1.0-architecture-snapshot.md) |

## Scope（本番採用）

- Collector RC-1（コード同梱、**Real KeibaNet 本接続は HOLD**）
- GUI（Invitation Beta）
- 一時IDログイン
- 運用機能（Result Automation / OPS Monitor / Miss Evidence 等）

## Explicitly out of baseline behavior

| 項目 | 状態 |
|------|------|
| RePick V2 | コードは `research/repick-v2/` に保持。**Flag OFF**。本番経路未配線 |
| Collector Real KeibaNet | **HOLD**（接続検証未完） |
| Prediction V2 market features (F01) | Archived（製品既定に含めない） |

## Canonical docs（運用）

| 文書 | パス |
|------|------|
| Completion Report | [`v1.0-completion-report.md`](./v1.0-completion-report.md) |
| Architecture Snapshot | [`v1.0-architecture-snapshot.md`](./v1.0-architecture-snapshot.md) |
| Freeze 宣言 | [`v1.0-freeze-declaration.md`](./v1.0-freeze-declaration.md) |
| 運用 Runbook | [`operations-runbook.md`](./operations-runbook.md) |
| 運用監視設計（v1.0） | [`v1.0-ops-monitoring-design.md`](./v1.0-ops-monitoring-design.md) |
| 月次レポートテンプレ | [`monthly-ops-report-template.md`](./monthly-ops-report-template.md) |
| Known Issues | [`known-issues-v1.0.0-stable.md`](./known-issues-v1.0.0-stable.md) |
| Version 1.1 Backlog | [`backlog-v1.1.md`](./backlog-v1.1.md) |
| Version 1.1 Implementation Plan | [`v1.1-implementation-plan.md`](./v1.1-implementation-plan.md) |
| Release notes | [`release-notes-2026-07-21-stable.md`](./release-notes-2026-07-21-stable.md) |
| リリース前チェック | [`release-checklist.md`](./release-checklist.md) |

## Change policy（Freeze）

1. **`v1.0.0-stable` は変更禁止**（詳細は Freeze 宣言）
2. 新機能は **Version 1.1** または **`research/*`** のみ
3. 本番デプロイ・rollback は本 tag（Hotfix は `v1.0.x-stable` 新タグ）
4. 予想ロジック / Feature Flag 既定 ON は 1.1 以降の明示リリースのみ
5. Real KeibaNet HOLD / RePick OFF を維持
