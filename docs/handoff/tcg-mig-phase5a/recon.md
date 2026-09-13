# recon: MIG-05 Phase 5a — TCG 本番投入 + ミラーシート日次書き出し

**注記**: 本ファイルは実装後に記録した後追い recon です（PR #3168 / 2026-08-30）。
PR本文に「recon.md コミット済み」と記載したのは虚偽記載であり、ここで訂正します。

## 関連 ADR

- ADR-090: products アーキテクチャ統一（TCG データ構造の本番定義を規定）
- ADR-083: TCG シリーズ種別マスタ（tcg_type_master 表の定義）

## 現状把握（実装前の調査結果）

### Task 1: 本番 DB 冪等投入

変更前: `tcg_migration/` ディレクトリ自体が存在しなかった。

| 調査対象 | 観察内容 | 引用 |
|---|---|---|
| 冪等投入の方針 | ON CONFLICT DO NOTHING で全 INSERT | `backend/tcg_migration/scripts/ingest_to_prod.py:15` |
| コンフリクトターゲット | `id` 列をデフォルトキーに使用 | `backend/tcg_migration/scripts/ingest_to_prod.py:68` |

### Task 3: TCG ミラーシート Celery 日次タスク

変更前: `backend/app/tasks/tcg_mirror.py` が存在しなかった。`beat_schedule` に tcg_mirror エントリなし。

| 調査対象 | 観察内容 | 引用 |
|---|---|---|
| beat_schedule 登録箇所 | celery_app.py の include と beat_schedule | `backend/app/celery_app.py:35` / `backend/app/celery_app.py:145-149` |
| スプレッドシートID固定 | コード変更なしで書き込み先変更を禁止 | `backend/app/tasks/tcg_mirror.py:30` |
| SA キー未設定時スキップ | TCG_SHEETS_SA_KEY_FILE が空ならスキップ | `backend/app/tasks/tcg_mirror.py:67` |
| シート自動作成禁止 | Drive quota=0 のため作成経路を封じる | `backend/app/tasks/tcg_mirror.py:49` |
| 実行エントリポイント | run_tcg_mirror_write() Celery タスク | `backend/app/tasks/tcg_mirror.py:287` |

## 触るファイル一覧

| ファイル | 種別 | 理由 |
|---|---|---|
| `backend/app/celery_app.py` | M（変更） | beat_schedule に tcg_mirror_daily 追加 |
| `backend/app/tasks/tcg_mirror.py` | A（新規） | MIG-05 Task3 Celery タスク本体 |
| `backend/requirements.txt` | M（変更） | gspread 追加 |
| `backend/tcg_migration/__init__.py` | A（新規） | パッケージ初期化 |
| `backend/tcg_migration/scripts/__init__.py` | A（新規） | パッケージ初期化 |
| `backend/tcg_migration/scripts/ingest_to_prod.py` | A（新規） | MIG-05 Task1 本番投入スクリプト |
| `backend/tcg_migration/scripts/verify_acceptance.py` | A（新規） | MIG-05 Task1 検収スクリプト |
| `backend/tcg_migration/scripts/write_mirror_once.py` | A（新規） | 単発ミラー書き出しスクリプト |
| `backend/tests/test_inventory_parser_llm_real_api.py` | M（変更） | API key 失効・モデル廃止時 skip 追加 |
| `backend/tests/test_tcg_mirror.py` | A（新規） | tcg_mirror タスクのユニットテスト |

削除行のあるファイル: **なし**（全て additive 変更のみ）
