# UI18 — Explain Chat エラー条件一覧

Audit date: 2026-07-30  
Scope: `public/chat.html` + `public/assets/api/conversation.js` + `public/assets/api/kaoba.js` + BFF  
Action Type: **Audit Only**（実装なし）

---

## ユーザー文言の発生点（唯一）

| 文言 | 発生箇所 | 条件 |
|------|----------|------|
| **「いま通信が不安定みたい。少し待ってからもう一度ね。」** | `chat.html` `send()` → `dispatchChat(text).catch` | `dispatchChat` の Promise が **最終 reject** したとき（かつ `strategyReply` ローカルフォールバックなし） |

**重要:** この文言は HTTP ステータス・タイムアウト種別・OPS コードを区別しない。**catch-all**。

別文言（通信エラーではない）:

| 文言 | 条件 |
|------|------|
| `API クライアントが読み込めていないよ。` | `ExpectApi` 未ロード、または Conversation/Kaoba 両方なし |
| `うまく答えられなかったみたい。…` | API **成功**だが `reply` 空（Success 扱い） |
| （オフライン）mock 文 | `?mock=1` 時のみ Kaoba catch → mock |

---

## ① エラー表示条件の完全列挙

### A. 「通信が不安定」に到達する条件（最終 reject）

Explain では通常 `ExpectApi.Conversation.chat` が存在する。流れ:

```
Conversation.chat → (fail) → viaKaoba / Kaoba.chat → (fail) → dispatchChat reject
→ 「通信が不安定」
```

| # | 条件カテゴリ | どこで reject | 「不安定」になるか |
|---|--------------|---------------|-------------------|
| A1 | HTTP 非 OK（4xx/5xx） | `conversation.js` `!res.ok` throw | Conversation 失敗後、Kaoba も失敗すれば **Yes** |
| A2 | 本文 `ok: false`（HTTP は 200 もあり得る） | 同上 `payload.ok === false` | 同上 |
| A3 | OPS_CLOSED（503） | middleware → クライアント throw | Conversation+Kaoba 両方 503 なら **Yes**（文言はメンテではなく「不安定」） |
| A4 | ネットワーク切断 / DNS / CORS / fetch 失敗 | `fetch` reject | 同上 |
| A5 | JSON parse 失敗 + 空/不正本文 | parse は握りつぶし → `payload=null`。`res.ok` なら先へ。**空 body + ok** は `data.__meta` 代入で TypeError → Conversation catch | Kaoba も失敗すれば **Yes** |
| A6 | Kaoba HTTP 非 OK / `ok:false` | `kaoba.js` throw → catch で mock 不可時 `Kaoba API unavailable` | Conversation 既失敗 or 未使用時 **Yes** |
| A7 | Kaoba `message` 空 | `Promise.reject("message required")` | 通常 UI では起きない |
| A8 | Kaoba API 未ロード | `viaKaoba` → `reject("no kaoba")` | Conversation 失敗後 **Yes** |
| A9 | Conversation `.then` 内例外（`addMsg` 等） | Conversation catch → viaKaoba | Kaoba も失敗すれば **Yes** |
| A10 | BFF/エッジがクライアントへエラー応答（502 AI_TIMEOUT 等） | `!res.ok` | 同上 |
| A11 | ブラウザ/プロキシが接続を切る（CF 524 等） | fetch fail / 非 OK | 同上 |

### B. 「通信が不安定」にならない失敗・劣化

| # | 条件 | 画面上の結果 |
|---|------|--------------|
| B1 | Conversation HTTP 200 + 正常 `data.reply` | Success（AI 吹き出し） |
| B2 | Conversation 失敗 → Kaoba HTTP 200 | Success（Kaoba 応答）。ユーザーは「不安定」を見ない |
| B3 | Ollama timeout（Python 側）だが HTTP 200 + rule/fallback reply | Success（品質劣化のみ） |
| B4 | LLM 生成文が薄い / 定型 | Success（文言は「不安定」ではない） |
| B5 | BFF が Conversation 不通時に stub/`viaKaoba` で **jsonOk** | クライアントは成功扱い |
| B6 | `?mock=1` で Kaoba 失敗 | mock 文 Success |

### C. レイヤ別タイムアウト（クライアント文言との関係）

| レイヤ | timeout | AbortController | 「不安定」との関係 |
|--------|---------|-----------------|-------------------|
| **ブラウザ Conversation client** | **なし** | **なし** | 自ら abort しない。切れれば A4/A11 |
| **ブラウザ Kaoba client** | **なし** | **なし** | 同上 |
| chat.html `setTimeout(..., 180)` | 送信開始遅延のみ | — | エラー条件ではない |
| BFF Conversation `aiFetch` | **60000 ms** | あり（aiProxy） | abort → 502 AI_TIMEOUT → クライアント A1。ただし BFF はその後 Kaoba/stub に落ちる経路あり → **必ずしもクライアント Error ではない** |
| BFF Kaoba `aiFetch` | デフォルト **12000 ms** | あり | Python 失敗時 rule へ。通常 jsonOk |
| Python Ollama | **45000 ms**（prod `CONVERSATION_OLLAMA_TIMEOUT_MS`） | プロセス内 | timeout でも多くの経路で HTTP 200 + fallback → **Success** |

### D. Promise.race

Explain Chat フロント経路に **`Promise.race` によるタイムアウトはない**。

---

## HTTP 200 でも Error（「不安定」）になる経路

| 経路 | 説明 |
|------|------|
| H1 | HTTP 200 + `payload.ok === false` → throw → Kaoba 失敗 |
| H2 | HTTP 200 + 空 body → `data` null → `data.__meta = …` TypeError → Kaoba 失敗 |
| H3 | HTTP 200 + 正常 data だが `.then` で例外 → Kaoba 失敗 |
| H4 | Conversation は 200 Success だが、**別リクエスト**でユーザーが Error を見た（セッション/認証差）。プローブ 200 と画面 Error は両立しうる |

**ないこと:** 「LLM の回答内容が悪い」だけで「不安定」になる経路は **ない**（reply 空なら別文言で Success）。

---

## 結論（条件の要約）

「通信が不安定」＝ **通信エラー専用ではなく、Conversation（あれば）と Kaoba の両方が最終的に失敗したときの汎用メッセージ**。

含まれうる実態:

- 真のネットワーク障害
- OPS_CLOSED 503
- BFF/エッジ timeout・切断
- JSON/クライアント例外
- Kaoba mock 無効時の二次失敗

含まれない（この文言では出ない）:

- Ollama 失敗だが HTTP 200 で reply がある場合
- Conversation だけ失敗して Kaoba が成功した場合
