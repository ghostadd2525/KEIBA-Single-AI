# UI18 — Timeout Audit（Explain Chat）

Audit date: 2026-07-30  
Question: Conversation API が約 29 秒で返るとき、フロントは何秒待つか？  
Action Type: Audit Only

---

## 結論（フロント）

| 項目 | 値 |
|------|-----|
| Conversation client timeout | **なし（無制限）** |
| Kaoba client timeout | **なし（無制限）** |
| AbortController（ブラウザ） | **未使用** |
| Promise.race（ブラウザ） | **未使用** |
| 送信前 delay | **180 ms**（UX のみ。打ち切りではない） |

**29 秒応答はフロント設計上、待ち切れない理由にならない。**  
フロントは `fetch` が settle するまで待つ。29s で 200 が届けば Success 経路。

---

## レイヤ別タイムアウト表

| レイヤ | ファイル | timeout | Abort | 超過時の挙動 |
|--------|----------|---------|-------|----------------|
| UI delay | `chat.html` | 180ms | — | typing 表示開始を遅らせるだけ |
| Conversation fetch | `conversation.js` | **なし** | なし | ブラウザ/NW が切るまで待機 |
| Kaoba fetch | `kaoba.js` | **なし** | なし | 同上 |
| BFF → Python Conversation | `functions/api/conversation/chat.js` | **60000 ms** | `aiProxy` AbortController | abort → `AI_TIMEOUT` 502 Response。続けて BFF が Kaoba/stub へフォールバックし **jsonOk になり得る** |
| aiProxy デフォルト | `functions/_lib/aiProxy.js` | **12000 ms** | あり | Conversation は上書きで 60s |
| BFF → Python Kaoba | `kaobaAdapter.js` aiFetch | **12000 ms**（デフォルト） | あり | 失敗時 rule 生成へ |
| Python Ollama | `CONVERSATION_OLLAMA_TIMEOUT_MS` | **45000 ms**（prod） | プロセス内 | 多くは fallback reply + HTTP 200 |

---

## 29 秒ケースのタイムライン（正常系）

```
t=0.00s  User send → Loading
t=0.18s  typingRow + Conversation fetch 開始
t≈29s    EC2 Conversation HTTP 200（Ollama 含む）
         BFF jsonOk → ブラウザ res.ok
         → addMsg(reply) → Success
```

フロント側に「25s で切る」等の設計はない。

---

## 29 秒でも画面が Error になりうる外部要因（フロント timeout 以外）

フロントに timeout がなくても、**途中の装置が切断**すると Dual-fail →「不安定」になり得る。

| 要因 | 典型 | フロントから見えるもの |
|------|------|------------------------|
| Cloudflare / 中間プロキシ制限 | 長時間 Worker / 524 | fetch fail / 非 OK |
| ユーザー端末スリープ・タブ破棄 | connection reset | fetch reject |
| OPS_CLOSED | 503（即） | Dual 503 → 不安定（遅延無関係） |
| BFF 60s abort | Conversation が 60s 超 | BFF が stub/Kaoba 成功なら UI Success；両方ダメなら Error |

**プローブで Conversation 29s・HTTP 200 が取れた事実は、「フロント 29s timeout」仮説を否定する。**

---

## AbortController 使用箇所（Explain 経路外の参考）

Explain Chat では使わないが、同リポジトリ他 API では Abort あり:

- `single-detail.js`, `race-history.js`, `race-board.js`, `user.js`, `supply.js` 等

→ Explain だけ意図的に「長時間 LLM 待ち」を許容している設計と読める（BFF も 60s）。

---

## Promise.race

| 場所 | Explain Chat への影響 |
|------|----------------------|
| `opsMonitor.js` / `health.js` 等 | Explain 送信経路に含まれない |
| chat / conversation / kaoba client | **なし** |

---

## 監査判定

| 仮説 | 判定 |
|------|------|
| フロントが ~25–30s で Abort して「不安定」 | **否定**（Abort なし） |
| 29s 応答そのものが Error 条件 | **否定**（200+ok なら Success） |
| 「不安定」＝タイムアウト専用メッセージ | **否定**（catch-all） |
| 真因は Dual API failure（種別不問） | **支持** |
