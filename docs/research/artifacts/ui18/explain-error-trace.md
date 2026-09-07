# UI18 — Explain Chat Error Trace

Audit date: 2026-07-30  
Premise: API プローブでは Kaoba ~119ms HTTP200 / Conversation ~29s HTTP200・Ollama 応答あり。  
にもかかわらずユーザー画面に「いま通信が不安定みたい…」が出た原因をトレースする。  
Action Type: Audit Only（実装・デプロイ・設定変更なし）

---

## 1. 文言の発生点（唯一の書き込み）

```350:358:public/chat.html
          dispatchChat(text)
            .catch(function () {
              if (options.strategyReply && strategyCtx) {
                var fallback = buildStrategyReview(strategyCtx);
                addMsg(fallback, "ai", true);
                ...
              } else {
                addMsg("いま通信が不安定みたい。少し待ってからもう一度ね。", "ai");
              }
            })
```

- `catch` 引数の `err` は **未使用**（ログなし・種別なし）。
- Console への `console.error` もこの経路にはない。
- したがって **Network タブ上の失敗理由と UI 文言は 1:1 対応しない**。

---

## 2. dispatchChat の失敗伝播

```264:309:public/chat.html
      function dispatchChat(text) {
        ...
        function viaKaoba() { ... ExpectApi.Kaoba.chat(...).then(addMsg) }

        if (ExpectApi.Conversation.chat) {
          return ExpectApi.Conversation.chat(payload)
            .then(successAddMsg)
            .catch(function () { return viaKaoba(); });  // ← 理由を捨てて Kaoba へ
        }
        return viaKaoba();
      }
```

**Error Catch 経路（Explain）:**

```
send
 └─ dispatchChat
     ├─ Conversation.chat
     │    ├─ fetch /api/conversation/chat
     │    ├─ !res.ok || ok===false → throw          [Catch-1]
     │    ├─ data.__meta = …（data null）→ TypeError [Catch-1]
     │    └─ then(addMsg) throw                     [Catch-1]
     │
     ├─ Catch-1 → viaKaoba（エラーオブジェクト破棄）
     │    └─ Kaoba.chat
     │         ├─ fetch /api/kaoba/chat
     │         ├─ !res.ok || ok===false → throw
     │         └─ .catch → mock? else reject("Kaoba API unavailable")  [Catch-2]
     │
     └─ Catch-2 → dispatchChat reject
          └─ send().catch → 「通信が不安定」   [Catch-3 / UI]
```

**Console:** Catch-1/2/3 いずれも標準では無音。  
**Network:** Conversation 失敗行 + Kaoba 失敗行が並ぶ典型。片方だけ 200 なら UI は Success。

---

## 3. Conversation client の throw 条件

```66:88:public/assets/api/conversation.js
    return fetch("/api/conversation/chat", { ... }).then(function (res) {
      return res.text().then(function (text) {
        var payload = null;
        try { payload = text ? JSON.parse(text) : null; } catch (e) { payload = null; }
        if (!res.ok || (payload && payload.ok === false)) {
          throw err;  // status 付き
        }
        var data = payload && payload.data != null ? payload.data : payload;
        data.__meta = ...;  // data が null/非オブジェクトだとここで死ぬ
        return data;
      });
    });
```

| Network 観測 | Client 判定 |
|--------------|-------------|
| 503 OPS_CLOSED | throw → Catch-1 |
| 502 AI_TIMEOUT / AI_UNAVAILABLE | throw → Catch-1（BFF が Response をそのまま返した場合） |
| 200 + `{ok:true, data:{reply:...}}` | Success |
| 200 + `{ok:false,...}` | throw |
| 200 + 空 body | TypeError → Catch-1 |
| JSON 不正 + HTTP 200 | payload null → data が null なら TypeError |

**timeout / Abort:** このファイルに存在しない。

---

## 4. Kaoba client の throw 条件

```121:130:public/assets/api/kaoba.js
      return apiPost("/api/kaoba/chat", body)
        .then(normalizeResponse)
        .catch(function () {
          if (ExpectMockGate.allowMockFallback()) return mockChat(body);
          return Promise.reject(new Error("Kaoba API unavailable"));
        });
```

- 本番（mock なし）では **あらゆる Kaoba 失敗が同一 reject** に潰される。
- Catch-2 の実エラーも UI / Console に出ない。

---

## 5. 「本当に通信エラーか？」判定

| 実態 | UI 文言 | 誤ラベル？ |
|------|---------|------------|
| ネットワーク切断 | 通信が不安定 | 妥当 |
| HTTP 5xx/4xx | 通信が不安定 | 広義の失敗を通信と呼んでいる |
| OPS_CLOSED 503 | 通信が不安定 | **誤ラベル**（メンテ） |
| BFF/エッジ timeout | 通信が不安定 | 部分的に妥当 |
| JSON / `__meta` TypeError | 通信が不安定 | **誤ラベル**（クライアント例外） |
| then(addMsg) 例外 | 通信が不安定 | **誤ラベル** |
| Ollama 失敗だが HTTP 200 + reply | （Success） | この文言は出ない |
| LLM 品質不良 | Success or 別文言 | この文言は出ない |

**結論:** 「通信が不安定」は **通信エラー専用ではない。**  
LLM 生成失敗・クライアント例外・OPS・timeout・fetch 失敗を、**Dual-fail 時にまとめて通信エラー扱い**している。

---

## 6. プローブ 200 なのにユーザー Error — 原因ランキング

前提: バックエンドは応答可能（プローブ証拠）。

| 順位 | 仮説 | 根拠 | 確度 |
|------|------|------|------|
| 1 | **ユーザーセッションが OPS_CLOSED（USER）** → Conversation と Kaoba の両方が 503 → Dual-fail | middleware 503; 文言 catch-all; ADMIN プローブは bypass | 高（Research Week 時） |
| 2 | **ユーザーブラウザだけ中間切断**（長時間リクエスト）→ Conversation fail → Kaoba も何らかで fail | フロント timeout なしだがエッジ/端末は切り得る; プローブ成功と両立 | 中 |
| 3 | Conversation は成功したが **別要因で Kaoba 経路だけ見えている** / スクリプト読込不全 | Conversation 未ロード時は Kaoba のみ; Kaoba fail → 不安定 | 低〜中 |
| 4 | HTTP 200 でも client throw（空 body / ok:false）+ Kaoba fail | コード上存在 | 低（プローブが正常 body なら稀） |
| 5 | 「フロントが 29s で timeout」 | Abort なし | **否定** |

**HTTP 200 + 正常 body の同一リクエストが「不安定」になることは、then 例外 + Kaoba 失敗を除き原則ない。**

---

## 7. Console / Network / Catch の対応表（再現時の見方）

再現時に確認すべきもの（実装せず監査観点のみ）:

| 観測点 | Success 時 | 「不安定」時の典型 |
|--------------------|-------------------|
| Console | 関連エラーなし | 同様に空のことが多い（catch が握りつぶす） |
| Network `POST /api/conversation/chat` | 200 | 非 OK / failed / (cancelled) |
| Network `POST /api/kaoba/chat` | 呼ばれない or 200 | **非 OK / failed**（必須） |
| Response body | `ok: true`, `data.reply` | `OPS_CLOSED` / 502 / 空 |
| Timing | ~数秒〜45s 程度まで伸びうる | Conversation 失敗後に Kaoba 短時間失敗も多い |

**「不安定」直前の必須条件:** `dispatchChat` が reject = **Kaoba 経路も失敗**（Conversation がある場合）。

---

## 8. BFF 補足（Server PASS と Client FAIL の隙間）

`functions/api/conversation/chat.js`:

- Python へ `timeoutMs: 60000`
- Python 不通時は BFF 内 `viaKaoba` / stub で **jsonOk を返しうる** → クライアント Success

つまり **EC2 が死んでいても UI Error にならない設計**がある。  
逆に **middleware が 503 を返すと BFF 本体に到達せず**、クライアントは即 throw → Kaoba も同 middleware → Dual-fail →「不安定」。

これは「バックエンド Ollama は生きているがユーザーは Error」を説明しやすい。

---

## 9. 成果物インデックス

| ファイル | 内容 |
|----------|------|
| [error-condition-table.md](./error-condition-table.md) | エラー条件の全列挙 |
| [explain-state-flow.md](./explain-state-flow.md) | Loading→Success/Error 遷移 |
| [timeout-audit.md](./timeout-audit.md) | フロント無制限 / BFF 60s / Ollama 45s |
| 本ファイル | Catch 経路トレースと原因ランキング |

---

## 10. Decision（Audit）

```
Action Type: Audit Only
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No（追加プローブは任意）
Rollback Required: No
Risk: None（読取のみ）
Expected Next Action:
  - ユーザー再現時に Network で Conversation+Kaoba の status / OPS_CLOSED を確認
  - 文言の誤ラベル修正やエラー種別表示は別 Phase（実装許可後）
```
