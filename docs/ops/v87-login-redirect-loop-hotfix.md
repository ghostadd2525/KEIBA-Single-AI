# Version8.7 hotfix — /login ERR_TOO_MANY_REDIRECTS

## 症状
`/login` で `ERR_TOO_MANY_REDIRECTS`（Guest でも到達不可）

## 往復（本番トレース）
```
GET /login      → 308 Location: /login
GET /login      → 308 Location: /login   （自己ループ）
GET /login.html → 308 Location: /login → 308 /login → …
```

`/maintenance` `/terms` `/setup` は 200（ループなし）

## 原因
`public/_redirects` の
```
/login /login.html 200
```
が Cloudflare Pages の pretty URL（`login.html` → `/login` の 308）と衝突。

`/ops` で発生した同系統障害。Maintenance 実装後に `_redirects` が残っていたことが直接原因。

JS の requireAuth / auto-maintenance はループの主因ではない（308 は HTML 到達前）。

## 修正
1. `_redirects` から `/login` rewrite を削除（Pages 自動解決に任せる）
2. `login.html` に `data-skip-auto-maintenance`
3. `auth.js` — login/terms/setup/maintenance を認証ゲート対象外、遷移先を `/login` `/terms`
4. `auto-maintenance.js` v12.4 — LOGIN_HREF=`/login`、既 login なら再遷移しない

## 非変更
PE / CE / AI / ResultAutomation / Research
