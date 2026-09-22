# recon: 完売ルール・日付ルール管理画面 認証不具合

## 現象
`/super-admin/analysis-rules` で「権限がありません。」と表示される。

## 原因調査

### API呼び出しの認証方式
- `frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx:73-148` — 全7関数が生の `fetch()` + `credentials: "include"` を使用
- `frontend/src/pages/super-admin/components/DateRulesPanel.tsx:69-143` — 全7関数が同様
- `frontend/src/lib/api.ts:46-62` — `api.get()`/`api.post()` は Firebase IDトークンを `Authorization: Bearer` ヘッダーで自動付与

### バックエンド認証
- `backend/app/auth/dependencies.py:453-481` — `require_super_admin` は `Authorization: Bearer` ヘッダーからJWTを読み取り `is_super_admin` を確認
- `backend/app/auth/dependencies.py:167-169` — `get_current_user` は `public.users` テーブルを参照

### DB確認（本番）
- `public.users` で `shingo@treasureislandjp.com` (id=3) は `is_super_admin=true`
- 認証ロジック上は通過するはずだが、フロントからトークンが送信されていないため401

### 根本原因
SoldOutRulesPanel/DateRulesPanel の API ヘルパー関数が `api.get()`/`api.post()` ではなく生の `fetch()` を使っているため、Firebase IDトークンが送信されない。
