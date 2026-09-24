# recon: import-history-redesign

## 現状（file:line で引用）

- `backend/app/routers/tcg_line_import.py:265-274` — 履歴SQLがimport_jobsのみ参照、JOINなし
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:619-661` — テーブル列: ファイル名/メッセージ数/仕入元数/未解決数/アップロード者/ステータス/確認状態/日時
- `frontend/src/locales/ja.json:3637` — colUnresolved既存キー

## import_job → source_message → extraction_job の結合経路

- `import_job_messages` 中間テーブル（relation_kind: 'created'/'reused'）
- `extraction_jobs.source_message_id` FK → `source_messages.id`
- extraction_jobs ステータス遷移: pending → running → done/empty/error

## 既存ADR検索結果

該当ADRなし（UI表示の列変更のため設計判断不要）

## 外部事例

該当なし（内部管理画面のUI改善）
