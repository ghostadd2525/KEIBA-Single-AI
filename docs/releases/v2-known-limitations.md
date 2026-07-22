# Version 2 — Known Limitations（Version 3 持ち越し）

**Date:** 2026-07-22  
**Status:** Release Candidate 付帯  
**正本 RC:** [`v2-rc-report.md`](./v2-rc-report.md)  
**Accuracy V3 詳細:** [`v2-accuracy-v3-roadmap.md`](./v2-accuracy-v3-roadmap.md)

本ドキュメントは **Version 2 で解決しない事項**を明示し、Version 3 以降へ引き継ぐ。

---

## 1. Accuracy

| ID | 制限 | V2 結論 | V3 示唆 |
|----|------|---------|--------|
| A-01 | 残 G1 miss（遠位・境界・並べ替え） | PE のみ +2 Hit。RP/CE 不採用 | 新 Trigger / Evaluation 再設計 |
| A-02 | 28 Feature 固定の天井 | Flag 継ぎ足しでは限界 | 新 Feature は **別 Contract + ROI** |
| A-03 | CE 温度較正 | CE-V2-A が Hit 悪化 | 単純温度再 AB 禁止 |
| A-04 | RP-NEAR Rescue | Rescue 0/11 | 旧 RP-V2-A 再利用禁止 |
| A-05 | CE-V2-C / PE-B/C / RO-V2 | 未実施 | V3 候補（必須ではない） |
| A-06 | Delete Boundary | 変更禁止 | V3 でも原則不変 |
| A-07 | Purchase −2（PE 採用副作用） | Hard Gate 外として記録 | 監視継続 |

Control（V3 開始点）: **Hit 218**（PE-V2-A ON）

---

## 2. UI Enhancement

| ID | 制限 | 持ち越し |
|----|------|----------|
| U-01 | Flag OFF 時は v1.1 一覧のまま | 本番 ON は段階ロールアウト |
| U-02 | RaceCardSummary 契約拡張なし | 追加フィールドは V3 で要設計 |
| U-03 | `short_reason` 等 Explain 連携は UI 一覧非スコープ | Explain 側 Flag と別管理 |
| U-04 | お気に入りは localStorage キー既存 | サーバ同期強化は後続 |

---

## 3. Explainability

| ID | 制限 | 持ち越し |
|----|------|----------|
| E-01 | Product stages は journal 経路依存 | journal 無しでは `not_applied` |
| E-02 | Kaoba は `context.v2_explain` 必須 | 未付与クライアントは旧挙動 |
| E-03 | Accuracy 不採用（RP/CE）でも explain 構造は存在しうる | 「採用 Flag」と「説明 Flag」は独立 |
| E-04 | 多言語・Runbook 自動リンク強化 | 後続 |

---

## 4. Operations

| ID | 制限 | 持ち越し |
|----|------|----------|
| O-01 | 本番 Grafana/Loki **未接続** | Promtail example のみ（prepared） |
| O-02 | CF Analytics / Tunnel CF API 自動集約なし | 手動 Dashboard + 後続自動化 |
| O-03 | BFF Incident は永続 jsonl ではなくスナップショット中心 | EC2 `incidents.jsonl` が正 |
| O-04 | SLO Burn / 日次ダイジェスト未実装 | 設計 Phase 4 |
| O-05 | Slack webhook 未設定環境では通知 no-op | Secrets 準備は運用タスク |
| O-06 | PI sample race_id カレンダー連動未固定 | 監視品質の後続改善 |

---

## 5. 横断・製品

| ID | 制限 | 持ち越し |
|----|------|----------|
| X-01 | v2 Flag 多数 · 既定 OFF | 本番 ON 順序は Checklist 参照 |
| X-02 | Accuracy 採用（PE ON）と Web Flag OFF の組み合わせ可 | 「予測品質」と「UI/Explain」切替は独立 |
| X-03 | mock_fallback 監視は v1.1 KI-01 系を継承 | PI 経路では mock 廃止済み · `engine_source=pi` 監視 |

---

## 6. Version 3 に持ち込まないもの（明示）

- RP-V2-A / CE-V2-A のパラメータ再挑戦を「V2 の続き」として実施すること  
- Delete Boundary の緩和を Accuracy 改善手段にすること  
- Prediction / RaceCardSummary / PI 契約の破壊的変更を無設計で入れること  

---

**Version 2 RC は上記制限を既知として出荷候補とする。**
