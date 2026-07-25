# Version 5 — Production Rollout Report

**Date:** 2026-07-25  
**Status:** Production Configuration Ready · Verification PASS  
**Scope:** Conversation API · Conversation UI · Knowledge Runtime · Review · Explain · Personal Chat  
**V4 Platform:** Freeze 維持（構造未変更）  
**ADR:** ADR-001〜005 遵守  
**Memory:** 未着手（対象外）

---

## 1. 目的

Version 5（Conversation Platform + Knowledge Runtime + UI Integration）を本番構成へ組み込む。  
Prediction API は Read Only。Security Guard は常時有効。

---

## 2. Feature Flag 一覧

### 2.1 本番推奨値（Canonical）

| Flag | 本番 | コード既定 | 役割 |
|------|------|------------|------|
| `F_V4_CONVERSATION_ENABLED` | **ON** | OFF | Conversation Platform マスタ |
| `F_V4_REVIEW_AGENT` | **ON** | OFF | KAOBA Review |
| `F_V4_PERSONAL_CHAT` | **ON** | OFF | Personal Chat |
| `F_V4_TOOL_LAYER` | **ON** | OFF | Tool Manager Canonical（ADR-002） |
| `F_V4_KNOWLEDGE_LAYER` | **ON** | OFF | Knowledge Tool |
| `F_V5_KNOWLEDGE_RUNTIME` | **ON** | OFF | Knowledge Runtime（RAG / Phase 2） |
| `F_V4_KNOWLEDGE_INTEGRATION` | **OFF** | OFF | 外部 Embedding/Vector 本接続（別 ADR まで OFF） |
| `F_V4_CONVERSATION_OLLAMA` | **OFF** | OFF | LLM polish（必要時のみ ON） |

### 2.2 無効化不可（Flag なし）

| 項目 | 状態 | 根拠 |
|------|------|------|
| Security Guard | **常時 ON** | ADR-001 · `SECURITY_GUARD_ALWAYS_ON=True` |
| Prediction Read Only | **常時** | ADR-003 · `mutated=false` |
| Memory | **未実装** | 本 Rollout 対象外 |

### 2.3 Legacy Flag（残置可）

| Flag | 本番 | 備考 |
|------|------|------|
| `F_V4_TOOL_LAYER=OFF` | 非推奨 | Legacy Connector 直結。Rollback 時のみ一時利用可 |
| `F_V4_KNOWLEDGE_INTEGRATION` | OFF 維持 | Adapter 配線のみ。クラウド Vector 未接続 |

コード既定は ADR-005 どおり **すべて OFF**。本番は EnvironmentFile で ON にする。

---

## 3. Production Configuration

### 3.1 成果物パス

| 成果物 | Path |
|--------|------|
| systemd env 例 | `infra/aws/systemd/conversation.env.example` |
| サービス内 Canonical | `services/win5-ai/config/production/conversation.env` |
| CF production 注記 | `infra/cloudflare/env/production.env.example` |
| 検証スクリプト | `services/win5-ai/tests/ops/verify_conversation_v5_production.py` |
| 検証結果 JSON | `docs/releases/v5-production-rollout-verification.json` |

### 3.2 インストール手順

```bash
# 1) Flag ファイル配置
sudo cp infra/aws/systemd/conversation.env.example /etc/expect-ai/conversation.env
sudo chown expect-ai:expect-ai /etc/expect-ai/conversation.env
sudo chmod 640 /etc/expect-ai/conversation.env

# 2) expect-ai.service に追記（shared/.env の後）
# EnvironmentFile=-/etc/expect-ai/conversation.env

# 3) UI（Pages）は Phase 3 成果物をデプロイ済みであること
#    chat.html?mode=explain|review|chat
#    ExpectApi.Conversation / ExpectConversationUi

# 4) 反映
sudo systemctl daemon-reload
sudo systemctl restart expect-ai
curl -sf http://127.0.0.1:8000/v1/conversation/health
```

### 3.3 本番構成図

```text
[Pages UI]
  Conversation UI (explain / review / chat)
        │  POST /api/conversation/chat
        ▼
[Cloudflare BFF]  （Flag なし · プロキシのみ）
        │  /v1/conversation/chat
        ▼
[expect-ai · EnvironmentFile=conversation.env]
  F_V4_CONVERSATION_ENABLED=ON
  F_V4_TOOL_LAYER=ON
  F_V4_REVIEW_AGENT / PERSONAL_CHAT=ON
  F_V4_KNOWLEDGE_LAYER=ON
  F_V5_KNOWLEDGE_RUNTIME=ON
        │
        ├─ Security Guard（常時）
        ├─ Orchestrator → Review / Explain / Chat
        ├─ Tool Manager → Prediction（Read Only）
        └─ Tool Manager → Knowledge → Runtime（RAG）
```

### 3.4 変更禁止（本 Rollout で触っていないもの）

| 領域 | 状態 |
|------|------|
| Prediction AI / Ranking / Confidence / Purchase | 未変更 |
| ADR 文書 | 未変更 |
| Platform 構造（Orchestrator / Agents / Tools） | 未変更 |
| Knowledge Runtime 実装 | 未変更（Flag ON のみ） |
| Memory | 未着手 |

---

## 4. 確認項目（Verification）

実行:

```bash
cd services/win5-ai
PYTHONPATH=. python tests/ops/verify_conversation_v5_production.py
```

| 項目 | 結果 |
|------|------|
| Feature Flags（本番推奨） | PASS |
| Review | PASS |
| Explain | PASS |
| Personal Chat | PASS |
| Personal Chat · Guard Block | PASS |
| Knowledge Runtime（via Tool Manager） | PASS |
| Prediction Read Only | PASS |
| Client prediction 無視 | PASS |
| Security Guard always_on | PASS |
| History（短期 FIFO · 非 Memory） | PASS |
| Performance budget | PASS |

### Performance（ローカル検証 · テンプレ経路）

| 経路 | p95（参考） | Budget |
|------|-------------|--------|
| Review chat | ≪ 500ms | 500ms |
| Explain chat | ≪ 500ms | 500ms |
| Knowledge search | ≪ 200ms | 200ms |

詳細は `v5-production-rollout-verification.json`。

---

## 5. Rollback 手順

### L1 — Feature Flag OFF（第一選択 · 推奨）

Prediction / Ranking には影響しない。Conversation のみ縮退。

```bash
sudo tee /etc/expect-ai/conversation.env >/dev/null <<'EOF'
F_V4_CONVERSATION_ENABLED=OFF
F_V4_REVIEW_AGENT=OFF
F_V4_PERSONAL_CHAT=OFF
F_V4_TOOL_LAYER=OFF
F_V4_KNOWLEDGE_LAYER=OFF
F_V5_KNOWLEDGE_RUNTIME=OFF
F_V4_KNOWLEDGE_INTEGRATION=OFF
F_V4_CONVERSATION_OLLAMA=OFF
EOF
sudo systemctl restart expect-ai
curl -sf http://127.0.0.1:8000/v1/conversation/health
```

| 期待 | `F_V4_CONVERSATION_ENABLED=OFF` → Legacy ConversationService 互換、または disabled 応答 |
|------|------|
| RTO | 再起動完了まで（通常数秒〜1分） |
| Security Guard | コード常時有効（OFF 不可）。Platform 再開後も維持 |

### L2 — Knowledge のみ切り戻し

Review / Explain / Chat は維持し、Knowledge だけ止める場合:

```text
F_V4_KNOWLEDGE_LAYER=OFF
F_V5_KNOWLEDGE_RUNTIME=OFF
# 他は本番推奨のまま
```

### L3 — UI 切り戻し（Pages）

| 手順 | 内容 |
|------|------|
| 1 | Pages を V5 UI Integration 前のリリースへ |
| 2 | BFF `/api/conversation/chat` は残してよい（後方互換） |
| 3 | L1 Flag OFF と併用推奨 |

### L4 — デプロイ戻し

| 手順 | 内容 |
|------|------|
| 1 | `expect-ai` を前リリースへ `ln -sfn` / 再デプロイ |
| 2 | L1 Flag OFF を維持確認 |
| 3 | `/v1/conversation/health` · Review/Explain smoke |

### Abort トリガー（目安）

| 条件 | レベル |
|------|--------|
| Conversation 5xx / タイムアウト急増 | L1 |
| `prediction_meta.mutated !== false` の検知 | L1 即時 + 調査 |
| Knowledge 異常のみ | L2 |
| UI 導線破損 | L3 |
| Platform 自体の破損疑い | L4 |

---

## 6. ADR 遵守

| ADR | 本番での扱い |
|-----|--------------|
| ADR-001 | Guard 常時。`F_V4_PERSONAL_CHAT` は Agent 有効化のみ。Guard OFF なし |
| ADR-002 | `F_V4_TOOL_LAYER=ON` Canonical。Legacy OFF は Rollback 用に残置 |
| ADR-003 | Prediction Read Only。UI/クライアント prediction は Official にしない |
| ADR-004 | Review/Explain は ReviewContext のみ |
| ADR-005 | コード既定 OFF · 本番 env で ON。Layer 契約維持 |

---

## 7. 停止条件

| 条件 | 状態 |
|------|------|
| V5 が本番構成（Flag + Config）で動作確認 | ✅ Verification PASS |
| Rollback 手順を文書化 | ✅ 本節 §5 |
| Memory 未着手 | ✅ |

**Version 5 Production Rollout（構成・検証・Rollback）完了。ここで停止する。**
