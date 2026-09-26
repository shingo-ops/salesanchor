# この文書は何か
添付ファイル配信API（便4）を実装するために調べた、既存コードとDBの状態をまとめたメモ。

## 調査結果

### 配信APIの権限設定
- `backend/app/routers/leads.py:1333` — 既存 attachment-url API が
  `dependencies=[Depends(require_permission("messaging.view"))]` を使うこと。
  新設 `serve_lead_attachment`（line 1273）も同じパターンで実装した。

### StreamingResponse の前例
- `backend/app/routers/meta_inbox.py:1105` — `StreamingResponse` で SSE ストリームを返す前例がある。
  FileResponse の使い方を設計する際に参照した。

### 画面側の attachment_url 利用
- `frontend/src/pages/inbox/InboxMessageThread.tsx` —
  `msg.attachment_url` をそのまま `<img src={...}>` に渡す（逐語一致の変更不要な箇所）。
  画面を変更しなくても自社配信URLが設定されれば表示される。

### lead_attachments テーブルの id 列
- `tenant_006.lead_attachments` の `id` 列は `integer` 型、
  `nextval('tenant_006.lead_attachments_id_seq'::regclass)` で自動採番される
  （手順1実測: `information_schema.columns` より）。

### message_id の UNIQUE 索引
- `idx_la_message_id` が `CREATE UNIQUE INDEX ... USING btree (message_id)` として存在する
  （手順1実測: `pg_indexes` より）。
  `ON CONFLICT (message_id) DO NOTHING` で安全に重複挿入を回避できる。

### テストの権限モック
- `backend/tests/conftest.py:1477` — `bypass_permissions` フィクスチャが
  `autouse=True` で全テストに自動適用され、`load_user_permissions` を
  全権限返しの関数に差し替える。
  テストファイル内で自前 `patch` すると引数数の不一致（`(db, tenant_id, user_id)` vs 旧定義）で
  `TypeError` になるため、自前 `patch` は行わない。
