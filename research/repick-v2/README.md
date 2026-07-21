# RePick V2 — research snapshot (Feature Flag OFF)

本番経路には **接続しない**。Hit率改善トラックは一時停止。

| 項目 | 値 |
|------|-----|
| `WIN5_REPICK_V2_ENABLED` | **False**（既定） |
| 本番 env | 設定しない / 絶対に `1` にしない |
| Optimizer hook | 本ディレクトリ外の研究ツリーのみ。Pages/AI 製品パス未配線 |

ファイル:

- `v2_repick_v2.py` — sidecar（identity when OFF）
- `test_repick_v2.py` — unit tests

設計・AB・Failure: `docs/ops/repick-v2-*.md`
