# Conversation / Race Detail — Production Check (2026-07-25)

## Personal Chat × Ollama

### 結論

| 項目 | 本番状態 |
|------|----------|
| V4 Conversation Platform | **OFF（Legacy ConversationService）** |
| Personal Chat Agent | **未使用** |
| Ollama LLM | **未接続** |
| 観測された応答 | 「対象レースの予想データが見つかりません…」（Legacy のレース必須パス） |

根拠:

1. `POST /api/conversation/chat`（mode=chat）→ Legacy 応答（レース指定を要求）
2. `GET https://ai.expect-keiba.com/v1/conversation/health` → `NOT_FOUND`（EC2 の win5-ai が旧コード、または V4 health 未配備）
3. 本番 Flag ファイルが EC2 に未適用（Pages デプロイだけでは Python Flag は変わらない）

### 必要な EC2 作業

```bash
# 1) 最新 win5-ai（V4/V5 Conversation）を EC2 に配置
# 2) Flag 適用
sudo bash scripts/ops/enable-conversation-v5-prod.sh

# 確認
curl -sS http://127.0.0.1:8000/v1/conversation/health
# → platform v4 / flags F_V4_CONVERSATION_ENABLED=true / OLLAMA=true

curl -sS -X POST http://127.0.0.1:8000/v1/conversation/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"今日の気分は？","mode":"chat"}'
# → agent=chat, llm.ollama_called=true（Ollama 起動時）
```

Flag（`/etc/expect-ai/conversation.env`）:

- `F_V4_CONVERSATION_ENABLED=ON`
- `F_V4_PERSONAL_CHAT=ON`
- `F_V4_CONVERSATION_OLLAMA=ON` ← 自然会話に必須
- Ollama: `http://127.0.0.1:11434` · model `qwen3:8b`

### BFF 暫定ガード（本 Round で反映）

EC2 が Legacy のままの間、`mode=chat` でレース必須エラーが返ってきた場合は BFF が Personal Chat 用の簡易応答に差し替える（レース指定を要求しない）。  
これは **Ollama 接続ではない**。正式には EC2 Flag + Ollama が必要。

---

## レース詳細が取れない件

### 結論

スクショ URL: `race_id=2024-07-25-01-08`

| race_id | 結果 |
|---------|------|
| `2024-07-25-01-08` | **404** `race_not_found` / `race_no_mismatch` |
| `2026-07-25-01-08` | **200**（約 2 秒） |

原因は Prediction 障害ではなく **年が 2024 の誤った race_id**。開催データは 2026-07-25。

### UI 補正（本 Round）

`race.html` で、カレンダー日と月日が一致し年だけ違う場合は `2026-…` へ `location.replace` する。

正しい URL 例: `https://expect-keiba.com/race?race_id=2026-07-25-01-08`
