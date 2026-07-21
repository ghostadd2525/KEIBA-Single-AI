# Stable Baseline — v1.0.0-stable

**Status:** CONFIRMED  
**Phase:** 開発フェーズ終了 → **運用フェーズ**  
**Date:** 2026-07-21

---

## Baseline

| 項目 | 値 |
|------|-----|
| Git tag | `v1.0.0-stable` |
| Commit | `08c7986904103d34b4570e013d628f7d3270d96c`（短縮 `08c7986`） |
| Branch | `main` |
| Release GO | 2026-07-21（本番スモーク後） |

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
| 運用 Runbook | [`operations-runbook.md`](./operations-runbook.md) |
| 運用監視設計（v1.0） | [`v1.0-ops-monitoring-design.md`](./v1.0-ops-monitoring-design.md) |
| 月次レポートテンプレ | [`monthly-ops-report-template.md`](./monthly-ops-report-template.md) |
| Known Issues | [`known-issues-v1.0.0-stable.md`](./known-issues-v1.0.0-stable.md) |
| Version 1.1 Backlog | [`backlog-v1.1.md`](./backlog-v1.1.md) |
| Release notes | [`release-notes-2026-07-21-stable.md`](./release-notes-2026-07-21-stable.md) |
| リリース前チェック | [`release-checklist.md`](./release-checklist.md) |

## Change policy（運用フェーズ）

1. 本番は **tag `v1.0.0-stable`（= `08c7986`）** を基準にデプロイ・rollback する
2. 予想ロジック / Feature Flag の既定 ON は **Version 1.1 以降の明示リリース**でのみ
3. Hotfix は最小差分 + 新タグ（例: `v1.0.1-stable`）を切る
4. 研究・実験は `research/` および docs に留め、本番 Flag を上げない
