# Version 4 — Conversation AI Architecture Design

**Date:** 2026-07-25  
**Status:** Architecture Inherited · **Minimal Platform Implemented**  
**Inheritance:** Conversation API = **Conversation Orchestrator**（Ollama Wrapper ではない）  
**Agents:** **Intent Router** → **Casual Agent** | **Expert Agent**

---

## 0. 目的と非目的

### 目的

競馬 AI に自然言語で対話できる **Conversation Platform** を追加する。  
Conversation API は Orchestrator として Intent Router を中心に Agent へ委譲する。

### 非目的（Hard Rules）

| 禁止 | 理由 |
|------|------|
| Conversation API を Ollama 直呼びにすること | Orchestrator / Agent 責務分離を壊す |
| Prediction の生成 | Prediction AI（V2 Production）の領域 |
| 本最小構成での Prediction API 実接続 | Expert Tool は Stub |
| Prediction / Accuracy / 購入ロジック変更 | 隣接レイヤーのみ |

### 基本データフロー（継承アーキテクチャ）

```text
Web / BFF
   ↓
Conversation API ＝ Conversation Orchestrator
   ↓
Intent Router
   ├─ Casual Agent  （挨拶・ガイド・予測生成拒否）
   └─ Expert Agent  → Expert Tools（現状 Stub）
                         └─（将来）Prediction API 読取専用
```

**原則:** Conversation は予測を **作らない**。Expert は Tool 経由の事実のみ語る。

---

## 1. Conversation Architecture

### 1.1 Orchestrator + Agents（正本）

```mermaid
flowchart TB
  subgraph API["Conversation API"]
    Orch["Conversation Orchestrator"]
    Router["Intent Router"]
    Casual["Casual Agent"]
    Expert["Expert Agent"]
    Stub["Expert Tools Stub"]
    OllamaOpt["Ollama Client<br/>optional Casual polish"]
  end

  Client["Client / BFF"] --> Orch
  Orch --> Router
  Router -->|casual intents| Casual
  Router -->|expert intents| Expert
  Expert --> Stub
  Casual -.->|Flag ON のみ任意| OllamaOpt
  Stub -.->|将来 Read-only| PredAPI["Prediction API"]
```

### 1.2 責務分離

| コンポーネント | 責務 | 禁止 |
|----------------|------|------|
| Orchestrator | 受付・Flag・ルーティング委譲・応答整形 | メッセージを直接 LLM に投げない |
| Intent Router | Intent 判定と Agent 選択 | Tool 実行・文章生成 |
| Casual Agent | greeting / app_guide / refuse_predict / unknown | Prediction Tool・予想生成 |
| Expert Agent | explain / race_qa / coverage / diagnostics | 予測の新規算出・Ollama での捏造 |
| Expert Tools | 事実取得（現状 Stub） | 本最小構成での Prediction 実接続 |

### 1.3 最小構成（Implemented）

| パス | 役割 |
|------|------|
| `app/conversation/v4/orchestrator.py` | Conversation Orchestrator |
| `app/conversation/v4/intent_router.py` | Intent Router |
| `app/conversation/v4/agents/casual.py` | Casual Agent |
| `app/conversation/v4/agents/expert.py` | Expert Agent |
| `app/conversation/v4/tools/stub.py` | Expert Tool Stub |
| `app/conversation/v4/ollama_client.py` | 任意（Casual polish のみ） |

**Flag:** `F_V4_CONVERSATION_ENABLED=true` で Orchestrator 経路。  
`F_V4_CONVERSATION_OLLAMA` は Casual の任意言い換えのみ（API 本体の条件ではない）。

### 1.4 As-Is / To-Be

| 観点 | 旧（Ollama Wrapper 案） | 継承アーキテクチャ（正） |
|------|-------------------------|-------------------------|
| API | message → Ollama | message → **Orchestrator → Router → Agent** |
| Prediction | 直結想定 | **未接続（Stub）** → 将来 Read-only |
| Ollama | API 本体 | Casual の optional のみ |
---

## 2. Conversation Specification

### 2.1 対応ユースケース（In Scope）

| ID | 種別 | 例 | 入力コンテキスト |
|----|------|----|------------------|
| C-01 | 説明（explain） | 「なぜこの馬が軸？」 | Prediction bundle + explain 投影（既存） |
| C-02 | 質問応答（qa） | 「このレースの信頼度は？」 | Prediction / race meta（読取） |
| C-03 | ガイド（guide） | 「画面の見方は？」「次に何を見る？」 | アプリ案内テンプレ + 任意 race_id |
| C-04 | 拒否/誘導 | 「明日の本命を新しく出して」 | 予測生成要求 → 拒否テンプレ + Prediction 画面誘導 |

### 2.2 Out of Scope（Conversation が断る）

- 新規 Prediction の算出・再ランキング
- 購入指示の自動実行
- 未取得レースの断定的予想
- オッズ・結果の捏造

### 2.3 Intent モデル（V4）

```text
intent ∈ {
  explain_pick,      # 選定理由の説明
  explain_confidence,# 信頼度・根拠の説明
  race_qa,           # レース事実・表示データの質問
  app_guide,         # 使い方・導線
  refuse_predict,    # 予測生成要求の拒否
  chitchat_safe,     # 軽い挨拶（過度な長文禁止）
  unknown            # 明確化を促す
}
```

**削除/凍結（Conversation 側）:** LLM による `generate_prediction` / `invent_pick` 相当。  
既存 As-Is の `predict_race` は **「既存 Prediction の提示・要約」** に再定義し、LLM に再予測させない（実装 Round で整理。本 Round は仕様のみ）。

### 2.4 品質要件

| 項目 | 要件 |
|------|------|
| 事実根拠 | Prediction / Race API から得た JSON のみを「事実」として扱う |
| 幻覚抑制 | コンテキストに無い馬名・オッズ・着順を断定しない |
| 言語 | `locale`（ja/en）を Prompt に反映（将来） |
| レイテンシ目標（設計値） | p95 ≤ 8s（8B） / ≤ 15s（12B）※実測は Phase 2 |
| 可用性 | Ollama 障害時も HTTP 200 + fail-open 文言（UI 非破壊） |

---

## 3. Prompt Design

### 3.1 System Prompt（骨格）

```text
あなたは Expect ～ KEIBA AI ～ の対話アシスタント「KAOBA」です。
役割は次の3つのみです: (1) 説明 (2) 質問応答 (3) ガイド。

絶対禁止:
- 新しい予測・本命・買い目・順位を自分で作ること
- Prediction API が返していない数値・馬を断定すること
- 購入を促す断定的助言（「必ず買って」等）

必須:
- 提供された CONTEXT_JSON のみを事実ソースとする
- 予測が無い場合は「予測データがまだありません」と案内し、Prediction 画面へ誘導する
- ユーザーが予測生成を求めた場合は丁寧に拒否し、既存の AI 予測結果の見方を案内する
- 回答は簡潔（目安 80〜180 日本語文字）。箇条書きは最大 5 点
```

### 3.2 Prompt Template（組み立て順）

```text
[SYSTEM]
  {system_prompt}

[DEVELOPER / POLICY]
  model_id={model_id}
  intent={intent}
  locale={locale}
  anti_predict=true

[CONTEXT_JSON]
  {
    "race": { ... read-only race meta ... },
    "prediction": { ... Prediction API 投影（要約）... },
    "explain": { ... explain_pick 投影（任意）... },
    "ui_hints": { ... ガイド用 ... }
  }

[HISTORY]
  直近 N ターン（user/assistant）※システム秘密を含めない

[USER]
  {message}
```

### 3.3 Prediction 投影（LLM に渡す最小形）

Prediction API 生レスポンスをそのまま投げず、**投影（Projection）** する。

```json
{
  "race_id": "2026-07-25-01-06",
  "prediction_available": true,
  "engine_source": "v2_production",
  "summary": { "honmei": "...", "confidence": 0.72 },
  "top_runners": [ { "umaban": 3, "name": "...", "score": 0.41 } ],
  "explain_summary": "..."
}
```

**禁止:** 学習用特徴量フルセット、内部スコア行列の生ダンプ（必要最小限のみ）。

### 3.4 Output Guard（ポストプロセス仕様）

1. **Anti-Predict スキャナ:** 「本命は◯番で確定」「私が予想すると」等の生成パターンを検知 → 拒否テンプレへ置換  
2. **Citation 必須（explain）:** `citations[]` に `race_id` / `engine_source` を付与  
3. **長さ制限:** 超過時は末尾カット + 「詳細はレース画面へ」  
4. **JSON 応答モード（任意）:** `{ "reply": "...", "intent": "...", "citations": [] }` を優先パース。失敗時は plain text

---

## 4. API Design

### 4.1 公開 API（BFF）

既存経路を維持しつつ契約を明確化。

#### `POST /api/conversation/chat`

**Request**

```json
{
  "message": "なぜこの馬が軸なの？",
  "session_id": "optional-uuid",
  "race_id": "2026-07-25-01-06",
  "locale": "ja",
  "context": {
    "type": "race_detail",
    "v2_explain": true
  },
  "model": null
}
```

| フィールド | 必須 | 説明 |
|------------|------|------|
| `message` | Yes | ユーザー発話 |
| `session_id` | No | 省略時サーバ発行 |
| `race_id` | No | 明示レース。無ければ履歴/解決 |
| `locale` | No | 既定 `ja` |
| `context` | No | UI 文脈（画面種別・フラグ） |
| `model` | No | 許可リスト内のモデル ID。無権限は無視 |

**Response 200**

```json
{
  "ok": true,
  "data": {
    "session_id": "…",
    "intent": { "name": "explain_pick", "confidence": 0.81, "race_id": "…" },
    "reply": "…",
    "citations": [ { "type": "prediction", "race_id": "…", "engine_source": "v2_production" } ],
    "actions": [ { "type": "open_race", "race_id": "…" } ],
    "prediction_meta": {
      "used": true,
      "prediction_available": true,
      "engine_source": "v2_production"
    },
    "model": { "id": "qwen3:8b", "provider": "ollama" },
    "fallback": null
  },
  "meta": { "service": "ConversationService", "provider": "ollama" }
}
```

**Fail-open Response（Ollama 不通時も 200）**

```json
{
  "ok": true,
  "data": {
    "session_id": "…",
    "intent": { "name": "app_guide", "confidence": 0.0 },
    "reply": "いま対話エンジンに接続できないよ。レース画面の AI 予測はそのまま見られるから、先にそちらを確認してみてね。",
    "citations": [],
    "actions": [ { "type": "open_race", "race_id": "…" } ],
    "model": null,
    "fallback": "fail_open_static"
  },
  "meta": { "service": "ConversationService", "provider": "fail_open", "fallback": "static" }
}
```

### 4.2 Conversation Service 内部 API（Python）

| Method | Path | 説明 |
|--------|------|------|
| POST | `/v1/conversation/chat` | 本体 |
| GET | `/v1/conversation/health` | Ollama + 自プロセス健全性 |
| GET | `/v1/conversation/models` | 利用可能モデル一覧（運用） |
| POST | `/v1/conversation/admin/model` | 既定モデル切替（ADMIN のみ・将来） |

### 4.3 Prediction API との接続方式（Read-Only）

```mermaid
sequenceDiagram
  participant C as Conversation Service
  participant P as Prediction API
  Note over C,P: 接続は GET のみ。POST/再計算トリガ禁止

  C->>P: GET /v1/predictions/{race_id}
  alt prediction_available=true
    P-->>C: bundle（契約不変）
    C->>C: Project → CONTEXT_JSON
  else unavailable / error
    P-->>C: available=false / 5xx
    C->>C: CONTEXT に prediction=null<br/>ガイド or データ待ち文言
  end
```

**接続ルール**

1. Conversation → Prediction は **HTTP GET（または既存 BFF 経由の同等読取）のみ**  
2. Conversation は Prediction の **再計算・キャッシュ破棄・フラグ変更** を行わない  
3. Prediction タイムアウト時は会話を止めず、`prediction_meta.used=false` でガイド継続（fail-open）  
4. Prediction API のパス・スキーマ・ステータス意味は **変更しない**

### 4.4 エラーコード（Conversation 固有）

| code | HTTP | 意味 |
|------|------|------|
| `UNAUTHORIZED` | 401 | 未ログイン |
| `RATE_LIMITED` | 429 | 過負荷保護 |
| `MESSAGE_TOO_LONG` | 400 | 入力長超過 |
| `MODEL_NOT_ALLOWED` | 400 | 許可外モデル指定 |
| （Ollama 障害） | **200 + fallback** | UI 破壊防止（fail-open） |

---

## 5. 会話履歴管理

### 5.1 データモデル（論理）

| フィールド | 型 | 説明 |
|------------|-----|------|
| `session_id` | string | 会話セッション |
| `user_id` | string | 認証ユーザー |
| `turn` | int | ターン番号 |
| `role` | `user` \| `assistant` \| `system` | |
| `content` | string | 本文（PII 最小化） |
| `race_id` | string? | 紐づきレース |
| `intent` | string? | 判定 intent |
| `model_id` | string? | 使用モデル |
| `provider` | string? | ollama / fail_open / … |
| `created_at` | ISO8601 | |

### 5.2 保持ポリシー

| 項目 | 設計値 |
|------|--------|
| Prompt に載せる履歴 | 直近 **8 ターン**（user+assistant） |
| 永続保持 | セッションあたり最大 **50 ターン**（超過は古いものから削除） |
| TTL | 例: **30 日**（運用設定） |
| 削除 | ユーザーログアウト時のクライアント側クリア + サーバ TTL |

### 5.3 セキュリティ上の扱い

- History にパスワード・トークン・一時IDを保存しない（入力サニタイズ）  
- 管理ログとユーザー向け履歴を分離（§8）

---

## 6. モデル切替設計

### 6.1 初期候補

| model_id | 用途想定 |
|----------|----------|
| `qwen3:8b` | 既定（低レイテンシ） |
| `gemma3:12b` | 高品質説明（負荷高） |

### 6.2 切替レイヤ

```text
config.default_model
   ↑ 運用設定（ファイル/環境変数）
request.model（任意・許可リスト内のみ）
   ↑ Feature Flag でユーザー指定を許可するか制御
```

| 優先度 | ソース |
|--------|--------|
| 1 | リクエスト `model`（Flag ON かつ allowlist） |
| 2 | ユーザー設定（将来） |
| 3 | `CONVERSATION_DEFAULT_MODEL` |
| 4 | ハードコード既定 `qwen3:8b` |

### 6.3 Allowlist

```yaml
models:
  allowlist:
    - qwen3:8b
    - gemma3:12b
  default: qwen3:8b
```

許可外は無視して default を使用（または `MODEL_NOT_ALLOWED` — Flag で選択）。

---

## 7. Configuration Design

### 7.1 設定ファイル（論理パス）

```text
config/conversation/
  conversation.yaml          # メイン
  prompts/
    system_ja.txt
    system_en.txt
    refuse_predict_ja.txt
  models.yaml                # allowlist / defaults
```

### 7.2 `conversation.yaml`（スキーマ案）

```yaml
conversation:
  enabled: false                 # Feature Flag と連動（既定 OFF）
  provider: ollama
  ollama:
    base_url: http://127.0.0.1:11434
    timeout_ms: 12000
    keep_alive: 5m
  prediction:
    mode: read_only
    base_url: ${PREDICTION_API_BASE_URL}
    timeout_ms: 3000
    # 再計算・書き込みエンドポイントは設定自体に持たない
  history:
    prompt_turns: 8
    max_turns: 50
    ttl_days: 30
  limits:
    max_message_chars: 2000
    max_reply_chars: 1200
    rate_per_user_per_min: 20
  fail_open:
    enabled: true
    static_reply_key: conversation.fail_open.ja
  security:
    anti_predict_guard: true
    redact_secrets: true
```

### 7.3 環境変数（運用）

| Env | 説明 | 既定 |
|-----|------|------|
| `F_V4_CONVERSATION_ENABLED` | 機能全体 | `false` |
| `F_V4_CONVERSATION_OLLAMA` | Ollama 経路 | `false` |
| `CONVERSATION_OLLAMA_BASE_URL` | Ollama URL | `http://127.0.0.1:11434` |
| `CONVERSATION_DEFAULT_MODEL` | 既定モデル | `qwen3:8b` |
| `PREDICTION_API_BASE_URL` | 読取先 | 既存 Pred URL |
| `CONVERSATION_FAIL_OPEN` | 障害時静的応答 | `true` |

---

## 8. Feature Flag Design

**原則（V3 継承）:** コード/設定の既定はすべて **OFF**。本番配線は Flag ON 時のみ。

| Flag | Env | 既定 | 説明 |
|------|-----|------|------|
| `F_V4_CONVERSATION_ENABLED` | 同左 | **OFF** | Conversation API 本番応答（OFF 時は既存 stub/Kaoba または 503 方針を別紙で固定） |
| `F_V4_CONVERSATION_OLLAMA` | 同左 | **OFF** | Ollama 呼び出し。OFF なら LLM 未使用の静的/既存経路 |
| `F_V4_CONVERSATION_HISTORY` | 同左 | **OFF** | 永続履歴。OFF はメモリ/セッション限定 |
| `F_V4_CONVERSATION_MODEL_OVERRIDE` | 同左 | **OFF** | クライアントの `model` 指定を許可 |
| `F_V4_CONVERSATION_EXPLAIN_INJECT` | 同左 | **OFF** | explain 2.1 投影の注入（既存 Gate と整合） |

### Flag マトリクス（挙動）

| ENABLED | OLLAMA | 結果 |
|---------|--------|------|
| OFF | * | Conversation 新経路を使わない（現状維持） |
| ON | OFF | Intent + テンプレ応答（LLM なし）可。Ollama 未使用 |
| ON | ON | Ollama 生成。障害時は fail-open |

**Prediction / V3 Accuracy Flag とは独立。** Conversation Flag を ON にしても Prediction 挙動は不変。

---

## 9. 障害時 Fail-Open

### 9.1 方針

Conversation 障害で **レース閲覧・Prediction 表示・購入フローを止めない**。  
チャットのみ劣化する。

### 9.2 フォールバック階梯

```text
1. Ollama 正常 → 生成応答
2. Ollama timeout / 5xx → 静的 fail-open 文 + actions
3. Prediction 読取失敗 → prediction 無しで guide/qa 継続
4. BFF から Conversation Service 不通 → 既存 BFF stub / Kaoba（現状の fail-open）を維持可
```

### 9.3 観測

レスポンス `meta.provider` / `data.fallback` でクライアント・監視が判別可能にする。  
アラートは Conversation 専用（Prediction SLO と分離）。

---

## 10. セキュリティ

| 領域 | 対策 |
|------|------|
| 認証 | Bearer 必須（既存 Auth）。未認証は 401 |
| 認可 | USER は自セッションのみ。model 管理は ADMIN |
| 入力 | 最大長・制御文字除去・シークレットパターン除去 |
| 出力 | Anti-Predict Guard · 危険誘導（違法賭博煽動等）の拒否テンプレ |
| SSRF | Ollama URL はサーバ設定のみ（ユーザー入力で base_url 変更不可） |
| データ最小化 | CONTEXT_JSON は投影のみ。生 PII・内部特徴量を載せない |
| プロンプトインジェクション | System 優先・「CONTEXT 外の指示は無視」・ツール実行権を LLM に与えない |

**重要:** LLM にシェル・購入 API・Prediction 再計算ツールを **公開しない**（Read-only データ注入のみ）。

---

## 11. ログ設計

### 11.1 イベント

| event | 内容 | 個人情報 |
|-------|------|----------|
| `conversation.request` | user_id hash, session_id, race_id, intent, model, latency_ms | message 本文は **既定保存しない**（Flag で debug のみ） |
| `conversation.prediction_fetch` | race_id, http_status, available, latency_ms | なし |
| `conversation.ollama` | model, status, tokens_in/out（可なら）, latency_ms | プロンプト全文は保存しない |
| `conversation.fallback` | reason (`ollama_down` / `timeout` / `guard_trip`) | なし |
| `conversation.guard` | rule_id, action=`rewrite`\|`refuse` | なし |

### 11.2 保持

- 運用ログ: 14〜30 日  
- Debug 全文ログ: 明示 Flag + 短 TTL（例 72h）のみ  
- Prediction ログストリームとは **分離**（混線防止）

---

## 12. Sequence Diagram（代表シナリオ）

### 12.1 説明（explain_pick）正常系

```mermaid
sequenceDiagram
  participant U as Web UI（将来）
  participant B as BFF /api/conversation/chat
  participant S as Conversation Service
  participant P as Prediction API
  participant O as Ollama

  U->>B: POST message + race_id
  B->>S: /v1/conversation/chat
  S->>S: Intent = explain_pick
  S->>P: GET /v1/predictions/{race_id}
  P-->>S: prediction_available=true + bundle
  S->>S: Project CONTEXT_JSON + Prompt
  S->>O: chat(model=qwen3:8b)
  O-->>S: draft reply
  S->>S: Output Guard (anti-predict)
  S-->>B: reply + citations + model
  B-->>U: 200 ok
```

### 12.2 予測生成要求の拒否

```mermaid
sequenceDiagram
  participant U as Web UI
  participant B as BFF
  participant S as Conversation Service

  U->>B: 「今から新しい本命を作って」
  B->>S: chat
  S->>S: Intent = refuse_predict
  Note over S: Ollama 省略可（テンプレ優先）
  S-->>U: 拒否 + 既存 Prediction の見方ガイド<br/>actions: open_race
```

### 12.3 Ollama 障害時 fail-open

```mermaid
sequenceDiagram
  participant U as Web UI
  participant B as BFF
  participant S as Conversation Service
  participant O as Ollama
  participant P as Prediction API

  U->>B: POST message
  B->>S: chat
  S->>P: GET prediction (optional)
  P-->>S: ok / skip
  S->>O: chat
  O--xS: timeout
  S->>S: fail_open static reply
  S-->>B: 200 + fallback=fail_open_static
  B-->>U: チャット劣化するが画面は継続
  Note over U: Prediction 表示は別 API のため影響なし
```

---

## 13. 提出物チェックリスト

| 提出物 | 本ドキュメント節 |
|--------|------------------|
| Conversation Architecture | §1 |
| Conversation Specification | §2 |
| Prompt Design | §3 |
| API Design | §4 |
| Configuration Design | §7 |
| Feature Flag Design | §8 |
| Sequence Diagram | §12 |
| （付帯）履歴 · モデル切替 · セキュリティ · ログ · fail-open | §5–6, §9–11 |

---

## 14. 次 Round でやらないこと（再掲）

- コード実装  
- Ollama インストール・モデル pull  
- Web UI 実装  
- Phase 2  
- Prediction AI / API / Accuracy / 購入の変更  

---

## 15. Stop

**Version 4 Conversation AI Architecture Design はここまでで完了とする。**  
実装・導入・UI には着手しない。
