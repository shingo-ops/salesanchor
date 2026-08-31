# 設計: MIG-05 Phase 5a — TCG 本番投入 + ミラーシート日次書き出し

**注記**: 本ファイルは実装後に記録した後追い設計書です（PR #3168 / 2026-08-30）。

- recon: docs/handoff/tcg-mig-phase5a/recon.md
- 対象ADR: ADR-090

## 目的

MIG-05 の2本柱:
1. **Task 1**: ローカル TCG DB のデータを本番 DB に冪等投入する
2. **Task 3**: 本番 DB のデータを TCG ミラーシートに Celery 日次書き出しする

## 実装方針

### Task 1（ingest_to_prod.py）

- 全 INSERT は `ON CONFLICT (id) DO NOTHING` で冪等性を保証
- `--dry-run` / `--preview` モードで本番書き込みを防ぐ
- `source_messages.superseded_by`（自己参照 FK）は 2-pass で処理
- 環境変数 `TCG_DB_LOCAL_URL` / `TCG_DB_PROD_URL` で接続先を指定

### Task 3（tcg_mirror.py + celery_app.py）

- 書き込み先 SpreadsheetID をコード定数で固定（変更不可）
- `TCG_SHEETS_SA_KEY_FILE` 未設定時はタスクをスキップ（本番以外の環境で安全）
- シート自動作成を禁止（Drive quota=0 が実測で確認済み）
- スケジュール: AM 02:30 JST（`crontab(hour=2, minute=30)`）

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| ingest_to_prod.py が同一スクリプトを2回実行しても重複しない | `--dry-run` 後に実行し、2回目は inserted_count=0 であることを確認 |
| TCG_SHEETS_SA_KEY_FILE 未設定時に Celery タスクが例外を上げずにスキップする | ローカルで `TCG_SHEETS_SA_KEY_FILE=` で run_tcg_mirror_write() を呼び、WARNING ログで終了することを確認 |
| test_tcg_mirror.py が pytest で PASS する | CI Backend Tests の pytest-run-internal が success（実績: CI run #33340265381, 1959 passed） |

## 外部・過去事例の参照と我々への応用

- **gspread + Service Account パターン**: Google Sheets API への書き込みは SA キーファイルを使う標準パターン。SA のスコープを `spreadsheets` と `drive.readonly` に限定して最小権限で運用（`backend/app/tasks/tcg_mirror.py:32-35`）。
- **ON CONFLICT DO NOTHING 冪等投入**: PostgreSQL の標準的な冪等 INSERT 手法。移行スクリプトをべき等にすることで再実行可能にし、障害復旧を容易にする。

## 維持の仕組み

守り手: .github/workflows/test.yml（Backend Tests / pytest-run-internal が毎 PR で test_tcg_mirror.py を実行）
