# Contract fixtures

正式契約に準拠したサンプル JSON。テスト・スナップショット・ドキュメントの共通入力。

| パス | 契約 |
|---|---|
| `prediction-bundle/valid-hanshin-11.json` | `single-prediction-bundle/2.0` |
| `analysis/valid-hanshin-11.json` | `expect-analysis/1.0` |
| `auth/login-response.json` 他 | `expect-auth/1.0` |
| `kaoba/chat-*.json` | `expect-kaoba/1.0` |

モック UI 用（`public/data/mocks/`）と内容を揃える。契約変更時は fixtures を先に更新し、テストを通す。
