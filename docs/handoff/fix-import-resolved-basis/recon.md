# recon: 解決/未解決カウントを created_count ベースに変更

## 調査日
2026-09-21

## 対象ADR
- ADR-027: UI国際化（i18n強制）
- ADR-067: デザイントークン強制
- ADR-144: UIガバナンス

## ADR検索結果
- `docs/adr/` grep: ADR-027, ADR-067, ADR-144 確認済み
- TCGパイプライン関連 ADR-100 / ADR-138 参照済み（今回のスコープ外）

## 既存コード調査

### バックエンド: tcg_line_import_svc.py
- `backend/app/services/tcg_line_import_svc.py:611` — `message_count = len(messages)`: 窓フィルタ後のファイル全体メッセージ数
- `backend/app/services/tcg_line_import_svc.py:669` — INSERT import_jobs に `unresolved_count=0` がハードコード（4b自動登録により常に0）
- `backend/app/services/tcg_line_import_svc.py:417-453` — `_link_message`: `relation_kind='created'` または `'reused'` でリンク

### バックエンド: import_job_messages テーブル
- `relation_kind = 'created'`: 新規作成メッセージ（新規INSERTされた source_messages）
- `relation_kind = 'reused'`: 既存の exact-match メッセージ（再利用・スキップ）
- `created_count` は `import_job_messages WHERE relation_kind = 'created'` の件数

### フロントエンド: AnalysisDashboardPanel.tsx
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:118-126` — `ImportRecord` interface: `message_count`, `unresolved_count`, `created_count` すべて `number` 型
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:483` — 問題箇所: `resolved_count = item.message_count - (item.unresolved_count ?? 0)` → `message_count`（全体）ベース

## 問題の確認
- `message_count`: ファイル全体（窓フィルタ後）の全メッセージ数（reused + created）
- `created_count`: 新規取り込みメッセージのみ（reused除く）
- 「解決」「未解決」の判定は新規取り込みメッセージに対してのみ意味がある
- 現行の `resolved_count = message_count - unresolved_count` は reused メッセージを誤って解決済みに含める

## 触れないファイル
- migrations/ — DB変更なし
- deploy.yml — 不要
- backend/ — APIレスポンス形式は変更不要（`created_count` は既にレスポンスに含まれている）
