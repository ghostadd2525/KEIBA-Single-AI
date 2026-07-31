# UI19 — エラーメッセージ / 原因マッピング

Design date: 2026-07-30  
Companion: [error-ux-design.md](./error-ux-design.md)  
Action Type: UX Design Only

---

## 1. UX Category 早見

| ID | Category | プライマリ文言（案） | 「通信」 |
|----|----------|----------------------|----------|
| U1 | unavailable | いま AI 会話は利用できない時間帯みたい。メンテが明けてからもう一度ね。 | しない |
| U2 | busy_retry | いま応答に時間がかかってるみたい。少し待ってからもう一度試してみて。 | しない |
| U3 | network | 通信がつながらなかったみたい。接続を確認して、もう一度ね。 | **する** |
| U4 | data_pending | このレースの説明データがまだ準備中みたい。レース詳細で状態を確認してみて。 | しない |
| U5 | client_unexpected | うまく表示できなかったみたい。ページを再読み込みしてもう一度ね。 | しない |
| U6 | generic_retry | いまうまく答えられなかったみたい。少し待ってからもう一度試してみて。 | しない |

**現行 catch-all の置換先:** 原則 **U6**（安易に U3 に落とさない）。

---

## 2. 技術シグナル → UX Category

| 技術シグナル（クライアントが保持すべきもの） | UX | 備考 |
|---------------------------------------------|-----|------|
| `navigator.onLine === false` | U3 | 他シグナルより優先可 |
| `fetch` reject / Failed to fetch / ネットワーク TypeError | U3 | status なし |
| HTTP 503 + `OPS_CLOSED` / メンテ文言 | U1 | Dual 503 の典型 |
| HTTP 503（その他） | U1 | 閉局扱いに寄せる |
| HTTP 502 + `AI_TIMEOUT` / `AI_UNAVAILABLE` | U2 | 「重い・一時不可」 |
| HTTP 504 / 524 相当 | U2 | エッジ待ち切れも U2 |
| HTTP 5xx（上記以外） | U2 または U6 | 迷ったら U6 |
| HTTP 401 / 403 | U1 | 「利用できない」に寄せる（ログイン誘導は任意） |
| HTTP 404（会話/レース） | U4 | データ・経路なし |
| HTTP 400（message required 等） | U5 | 通常 UI では稀 |
| HTTP 200 + `ok: false` + 既知 code | code に従う | |
| 空 body / JSON 不正 → parse・`__meta` 例外 | U5 | |
| `addMsg` / render 例外 | U5 | |
| `Kaoba API unavailable`（詳細なし） | U6 | 現行 kaoba catch の潰れ先 |
| `no kaoba` / ExpectApi 欠落 | U5 | 既存「APIクライアント…」と統合可 |
| 分類不能 | U6 | |

---

## 3. Conversation Fail → Kaoba Fail → 表示文言

凡例: Conv = Conversation、K = Kaoba。最終列がユーザー表示。

### 3.1 Success で終わる（Error 文言なし）— 現行維持

| Conv | Kaoba | 表示 |
|------|-------|------|
| OK | （呼ばない） | Success reply |
| Fail（任意） | OK | Success reply（Kaoba） |
| （未ロード） | OK | Success reply |

### 3.2 Dual-fail / 最終 Fail — 原因別 UX

| Conv 失敗の見え方 | Kaoba 失敗の見え方 | 最終 UX | 表示文言キー |
|-------------------|--------------------|---------|--------------|
| 503 OPS_CLOSED | 503 OPS_CLOSED | **U1** | unavailable |
| 503 OPS_CLOSED | network | **U1** | unavailable（メンテ優先） |
| network | network | **U3** | network |
| network | 503 OPS_CLOSED | **U1** | unavailable |
| 502 timeout | 502 / 5xx | **U2** | busy_retry |
| 502 timeout | network | **U2** | busy_retry（サービス側を優先） |
| 502 timeout | rule/Kaoba まで届かず generic | **U2** | busy_retry |
| 404 / data missing | 404 or generic | **U4** | data_pending |
| parse / client | 任意 Fail | **U5** | client_unexpected※ |
| parse / client | OK | Success（Fail にならない） | — |
| generic / 不明 | generic / 不明 | **U6** | generic_retry |
| generic | network | **U3** | network（接続が明確なら） |
| 未ロード | Fail（network） | **U3** | network |
| 未ロード | Fail（503） | **U1** | unavailable |
| 未ロード | Fail（不明） | **U6** | generic_retry |

※ Conv が parse/client でも Kaoba が Success なら Error にしない（現行どおり）。

### 3.3 優先度（衝突時）

```
U1 (unavailable) > U3 (network) > U4 (data) > U2 (busy) > U5 (client) > U6 (generic)
```

意図: メンテ中に「通信」と言わない。接続断が明確なら「通信」。それ以外は待つ/再試行。

---

## 4. モード別 CTA マッピング

| UX | Explain | Review | Personal Chat |
|----|---------|--------|---------------|
| U1 | レース詳細へ戻る | レース詳細へ戻る | マイページへ戻る |
| U2 | もう一度試す / レース詳細へ戻る | 同左 | もう一度試す / マイページ |
| U3 | もう一度試す / レース詳細へ戻る | 同左 | もう一度試す / マイページ |
| U4 | レース詳細へ戻る（主）/ もう一度試す（副） | 同左 | —（race なしならマイページ） |
| U5 | もう一度試す / 再読み込み案内 / レース詳細へ戻る | 同左 | もう一度試す / マイページ |
| U6 | もう一度試す / レース詳細へ戻る | 同左 | もう一度試す / マイページ |

リンク案（既存ルート踏襲）:

- レース詳細: `race.html?race_id={id}`
- マイページ: `mypage.html`
- 日常会話（二次・任意）: `chat.html?mode=chat`

---

## 5. 現行文言との対照

| 現行 | 問題 | 置換 |
|------|------|------|
| いま通信が不安定みたい。少し待ってからもう一度ね。 | 原因を「通信」に誤帰属 | U6 を既定。信号があれば U1–U5 |
| API クライアントが読み込めていないよ。 | 技術寄りだが実態に近い | U5 に統合可（「表示の準備ができなかった」） |
| うまく答えられなかったみたい。 | Success 時の空 reply | **維持**（Error Category ではない） |

---

## 6. コピー・トーンガイド

- 「失敗」「エラーコード」は避ける
- 「あなたのせい」を示唆しない
- 再試行を促すときは **「少し待って」** を U2/U6 に付ける
- U3 だけ **「通信」「接続」** を許可
- U1 は **時間帯・メンテ明け** を示し、無限再試行を煽らない

---

## 7. Decision メモ

実装時は本表を `mapChatErrorToUx` の仕様正本とする。  
本 Phase では表の確定のみ（コード変更なし）。
