# design: TCG LINE import 確認工程

## KGI / KPI

| 基準 | 検証方法 |
|------|----------|
| 未解決仕入元があるときは source_messages が1件も書かれない | テスト `test_import_unresolved_does_not_write_source_messages` PASS |
| 未解決0件のときは従来どおり抽出エンキューまで自動で進む | テスト `test_import_zero_unresolved_writes_source_messages` PASS |
| commit は全名解決後のみ成功する（未解決残 → 409） | `commit_pending_job` の still_unresolved チェック + 手動 API テスト |
| 窓は JST 基準 24h（旧実装の 33h を是正） | テスト `test_compute_window_jst_basis` PASS |
| 保留ジョブは 24h 超で自動破棄される | テスト `test_discard_stale_pending_jobs_calls_update` PASS |

## 設計方針

### tcg_suppliers.name の定義
- `tcg_suppliers.name` は「現在の LINE 表示名」と定義する
- 人が手入力した名前ではなく、トーク履歴から抽出した文字列を採用する
- 別名テーブル（aliases）は作らない: 確認工程で解決するため不要

### 未解決0件 → 確認画面を挟まず自動で抽出へ進む
- GAS の既存フローと同等。新しいフローは未解決があった場合のみ

### 保留は 24 時間で破棄
- pending_messages（JSONB）を NULL にして行は残す（監査）
- Celery Beat で 1 時間ごとに実行

### ADR-154 との関係
- GAS に確認工程は無い → 本 PR は GAS に存在しない新規機能
- 照合ロジック（`tcg_analyzer_svc.py` / `gemini_extraction_svc.py`）は変更しない

### JST 窓計算（DIST-R3 是正）
- 旧実装: `datetime.now(timezone.utc) - timedelta(hours=24)` → JST タイムスタンプと比較し実質 33h
- 新実装: `datetime.now(JST_TZ) - timedelta(hours=24)` → JST 基準で正確に 24h
- `JST_TZ = ZoneInfo("Asia/Tokyo")` を本ファイルで定義
  （#3305 未マージのため独立定義。マージ後は共通定数に統一予定）

## 変更ファイル一覧

| ファイル | 種別 | 内容 |
|----------|------|------|
| `migrations/20260905_140000_import_jobs_review_stage_t004.sql` | 新規 | import_jobs に 5 列追加 |
| `scripts/run_all_migrations.sh` | 追記 | run_sql 1 行追加 |
| `backend/app/services/tcg_line_import_svc.py` | 変更 | 分岐ロジック・JST 窓・`_write_source_messages` 分離 |
| `backend/app/routers/tcg_line_import.py` | 変更 | 新エンドポイント 4 本追加 |
| `backend/app/tasks/tcg_import_discard.py` | 新規 | 破棄タスク |
| `backend/app/celery_app.py` | 追記 | beat_schedule 1 エントリ追加 |
| `backend/tests/test_tcg_line_import.py` | 変更 | 新テスト 9 件追加（合計 45 件・全 GREEN） |
| `docs/handoff/tcg-import-review-stage/recon.md` | 新規 | 本ファイル |
| `docs/handoff/tcg-import-review-stage/design.md` | 新規 | 本ファイル |

## 新エンドポイント一覧

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/v1/tcg/line-import/pending` | pending_review ジョブ一覧 |
| GET | `/api/v1/tcg/line-import/{job_id}` | ジョブ詳細（pending_messages 本文は返さない） |
| POST | `/api/v1/tcg/line-import/{job_id}/resolve` | 仕入元登録・差し替え |
| POST | `/api/v1/tcg/line-import/{job_id}/commit` | 全解決済みのとき書き込みを確定 |

## 外部事例欄
- LINE グループメッセージを介した仕入れ確認フローはアナログ運用が多く、
  「未知の送信者を一時保留して後から名前解決する」パターンは
  AWS Kinesis / Kafka の Dead Letter Queue（処理できないメッセージを別キューに退避）と同等の設計
- 保留→確認→再コミットは GitHub の Draft PR → Ready for Review と同じ「確認ゲート」パターン

## 守り手（このロジックが壊れたときに検知できるテスト）
- `backend/tests/test_tcg_line_import.py::test_import_unresolved_does_not_write_source_messages`
- `backend/tests/test_tcg_line_import.py::test_import_zero_unresolved_writes_source_messages`
- `backend/tests/test_tcg_line_import.py::test_import_partial_unresolved_also_blocks`
- `backend/tests/test_tcg_line_import.py::test_import_unresolved_stores_pending_messages`
- `backend/tests/test_tcg_line_import.py::test_compute_window_jst_basis`
- `backend/tests/test_tcg_line_import.py::test_discard_stale_pending_jobs_calls_update`
