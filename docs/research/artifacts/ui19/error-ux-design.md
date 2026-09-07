# UI19 — Explain Chat エラーUX設計

Design date: 2026-07-30  
Depends on: UI18 (`docs/research/artifacts/ui18/`)  
Action Type: **UX Design Only**（実装・デプロイ・設定変更なし）

---

## 1. 問題定義

現行文言「いま通信が不安定みたい。少し待ってからもう一度ね。」は、`dispatchChat` 最終 reject の **catch-all** である（UI18）。

実態には次が混在する:

| 実態 | 「通信」と呼ぶ妥当性 |
|------|---------------------|
| ネットワーク切断 / fetch 失敗 | 妥当 |
| OPS_CLOSED（メンテ） | **不妥当** |
| AI/BFF 一時不可（502 timeout 等） | やや不妥当（「AIが忙しい」が近い） |
| JSON / Client Exception | **不妥当** |
| レースデータ未準備（将来・別 API） | **不妥当** |

ユーザーは「回線が悪い」と誤解し、再試行以外の正しい行動（待つ / 戻る / メンテ終了を待つ）を取れない。

---

## 2. 設計原則

1. **原因を技術語で晒さない**（`OPS_CLOSED` / `AI_TIMEOUT` / HTTP 番号は出さない）
2. **ユーザーが次に何をすればよいか**を一文で示す
3. **「通信」は真に接続系のみ**に限定する
4. Conversation → Kaoba の二段フォールバックは維持（Success 優先）。文言分岐は **最終 fail 時**と、可能なら **第一失敗の分類保持**
5. Prediction / 印 / スコアは触らない（Explain UX のみ）
6. KAOBA 口調は維持（断定・責める表現を避ける）

---

## 3. ユーザー目線のエラー分類（UX Category）

| ID | UX Category | ユーザーが理解する意味 | 「通信」語の使用 |
|----|-------------|------------------------|------------------|
| **U1** | `unavailable` | いま AI 会話が使えない（メンテ・権限・サービス閉） | **使わない** |
| **U2** | `busy_retry` | 混雑・待ちすぎ・一時的に応答できない → 少し待つ | **使わない**（「いまちょっと応答が重い」系） |
| **U3** | `network` | 端末〜サイトの接続が切れている／届いていない | **使う** |
| **U4** | `data_pending` | このレースの説明材料がまだ揃っていない | **使わない** |
| **U5** | `client_unexpected` | 想定外（スクリプト・表示まわり） | **使わない** |
| **U6** | `generic_retry` | 分類不能だが再試行に意味がある | **使わない**（旧「通信」の置き換え先） |

### 推奨プライマリ文言（吹き出し本文）

| ID | 推奨文言（案） |
|----|----------------|
| U1 | 「いま AI 会話は利用できない時間帯みたい。メンテが明けてからもう一度ね。」 |
| U2 | 「いま応答に時間がかかってるみたい。少し待ってからもう一度試してみて。」 |
| U3 | 「通信がつながらなかったみたい。接続を確認して、もう一度ね。」 |
| U4 | 「このレースの説明データがまだ準備中みたい。レース詳細で状態を確認してみて。」 |
| U5 | 「うまく表示できなかったみたい。ページを再読み込みしてもう一度ね。」 |
| U6 | 「いまうまく答えられなかったみたい。少し待ってからもう一度試してみて。」 |

**廃止候補:** 「通信が不安定みたい」（曖昧・過大）。U3 のみ「通信」を残す。

---

## 4. 「通信」を使う / 使わない

### 使ってよい（U3）

- `fetch` 自体の reject（TypeError / Failed to fetch）
- オフライン（`navigator.onLine === false` が取れる場合は補強）
- CORS / DNS 相当でレスポンスボディが取れない接続失敗

### 使ってはいけない

| ケース | 代わり |
|--------|--------|
| OPS_CLOSED / 503 メンテ文言 | U1 |
| 502 `AI_TIMEOUT` / 長時間後のサービスエラー | U2 |
| 5xx 一般（接続は成立） | U2 または U6 |
| 4xx（認証切れ等） | U1 寄り（「ログインし直して」は別 Phase で可） |
| JSON parse / `__meta` TypeError / addMsg 例外 | U5 |
| レース Bundle 欠落・準備中 | U4 |
| 分類不能の Dual-fail | U6（**通信と言わない**） |

---

## 5. 分類に必要なクライアント情報（設計・未実装）

現状はエラーオブジェクトを破棄している。原因別 UX には最低限の **Error Signal** 保持が必要（実装 Phase で）。

| Signal | 取得元 | UX への寄与 |
|--------|--------|-------------|
| `status` | `err.status`（conversation/kaoba が付与済み） | 503→U1, 502→U2, 0/なし+fetch fail→U3 |
| `code` | `payload.error.code`（例 OPS_CLOSED） | U1 確定 |
| `kind` | `network` / `http` / `parse` / `client` | U3/U5 |
| `stage` | `conversation` / `kaoba` | 観測・将来の詳細文 |
| `offline` | `navigator.onLine` | U3 補強 |

**優先ルール（案）:**

```
if offline or fetch-reject without status → U3
else if status===503 or code===OPS_CLOSED → U1
else if status===502 or code in (AI_TIMEOUT, AI_UNAVAILABLE) → U2
else if status===404 or code suggesting missing race data → U4
else if kind in (parse, client) → U5
else → U6
```

Dual-fail 時は **Kaoba 最終エラーを主**、Conversation 側は副信号。両方が U1 なら U1。片方 U3・片方 U1 なら **U1 優先**（メンテ中に「通信」と言わない）。

---

## 6. 次の行動（CTA）設計

吹き出し本文の下（または同一バブル内）に、モードに応じたアクションを出す。

### Explain（`mode=explain`）

| CTA | 動作 | 出す Category |
|-----|------|----------------|
| **もう一度試す** | 直前の user 文を再 `send`（入力欄は維持可） | U2, U3, U5, U6 |
| **レース詳細へ戻る** | `race.html?race_id=…`（既存 back と同） | 全 Category |
| （任意）**少し待つ案内のみ** | ボタンなし・文言だけ | U1 |

U1（メンテ）では「もう一度試す」は出してもよいが、連打防止のため **短いクールダウン（設計: 10–30s）** を推奨。必須ではない。

### Review

| CTA | 動作 |
|-----|------|
| もう一度試す | 同上 |
| レース詳細へ戻る | 同上 |

### Personal Chat（`mode=chat`）

| CTA | 動作 |
|-----|------|
| もう一度試す | 同上 |
| マイページへ戻る | `mypage.html` |

### 「チャットルームへ移動」

Explain / Review から日常会話へ誘導する場合:

| CTA | 動作 | 出す条件 |
|-----|------|----------|
| **日常会話へ** | `chat.html?mode=chat` | U1 以外で「予想説明は後で、雑談は別」と分けたいとき。**デフォルトは非表示**（Explain 失敗時に日常会話が使える保証がないため）。U4（データ準備中）で「先に雑談」を出すのは任意・低優先。 |

設計方針: Explain 失敗の主 CTA は **再試行 + レース詳細へ戻る**。チャットルーム移動は二次。

---

## 7. Conversation Fail → Kaoba Fail → 表示（要約）

詳細表は [error-message-mapping.md](./error-message-mapping.md)。

```
Conversation 成功 → 文言なし（Success）
Conversation 失敗 → Kaoba 成功 → 文言なし（Success・現行維持）
Conversation 失敗 → Kaoba 失敗 → UX Category 文言 + CTA
```

Kaoba のみ経路（Conversation 未ロード）も同じ最終マッピング。

---

## 8. Loading / Success / Error との関係

- Loading 中は CTA を出さない（現行 `setBusy` 維持）
- Error 吹き出し表示後は Idle（再試行可能）
- Success と Error を同じ「AI 吹き出し」枠で出すが、Error は **視覚的に弱く区別**（例: 控えめな注記スタイル）。実装 Phase で既存 CSS に合わせる。**新カード UI の乱用はしない**（操作のための CTA 行のみ可）

---

## 9. 非目標（この設計に含めない）

- BFF / Ollama / timeout 秒数の変更
- OPS スケジュール変更
- PredictionBundle の仕様変更
- エラーの技術詳細をユーザーに全文表示
- mock フォールバックを本番で再度有効化

---

## 10. 実装 Phase への引き継ぎ（設計メモのみ）

想定タッチポイント（**今は書かない**）:

- `chat.html` … catch-all 文言・CTA DOM
- `conversation.js` / `kaoba.js` … Error Signal を破棄しない
- 任意: 共通 `mapChatErrorToUx(err) → { category, message, actions }`

検証観点（実装後）:

- OPS_CLOSED で「通信」が出ないこと
- Dual-fail で U6、オフラインで U3
- Conversation 失敗・Kaoba 成功で Error CTA が出ないこと

---

## 11. Decision

```
Action Type: UX Design Only
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: None（設計文書のみ）
Expected Next Action: 実装許可後に mapChatErrorToUx + CTA（別 Phase）
```
