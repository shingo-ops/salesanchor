# recon — tcg-import-fk-order-fix (supersede FK 順序修正)

## 調査対象

`backend/app/services/tcg_line_import_svc.py` の `import_line_export` において、
`UPDATE source_messages SET superseded_by = :new_id` が `INSERT INTO source_messages` より
先に実行されており、本番でアップロードが「データベースエラー」で失敗している。

## 根本原因の特定

### DDL の FK 制約（DEFERRABLE 未指定）

`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:230-231`:

```sql
superseded_by       UUID
                        REFERENCES %I.source_messages (id),
```

`DEFERRABLE` および `ON DEFERRABLE` 句なし。
PostgreSQL のデフォルト = `NOT DEFERRABLE INITIALLY IMMEDIATE`。
各 SQL 文の実行直後に FK チェックが行われる。

### 修正前コードの実行順序（`backend/app/services/tcg_line_import_svc.py:380〜421` の修正前）

```
Step 1: new_sm_id = uuid.uuid4()           ← まだ DB にない
Step 2: UPDATE source_messages
            SET superseded_by = new_sm_id  ← FK: source_messages(id) を参照
          WHERE id = old_id               ← FK チェック実行 → new_sm_id 不在 → 失敗
Step 3: INSERT INTO source_messages (id=new_sm_id, ...)
```

Step 2 の UPDATE 直後に FK チェックが走り、`new_sm_id` がまだ存在しないため
`ForeignKeyViolation` が発生し「データベースエラー」となる。

### 発生条件

対象 `supplier_channel_id` に `is_active = TRUE` の `source_messages` レコードが既存の場合のみ。
既存レコードがない場合は UPDATE ループが 0 回で通過するため発生しない。

`backend/tcg_migration/scripts/ingest_to_prod.py` および `backend/tcg_migration/scripts/write_mirror_once.py` による
移行データが本番の `tenant_004.source_messages` に存在する場合、初回アップロードで発火する。

### backend ログが取れなかった理由

IMP-24 で `docker compose logs --tail=150 backend` を実行したが出力 0 行。
同タイミングで `celery-worker` が 00:18:50 → 00:25:20 に再起動していた。
backend コンテナも同時期に再起動し、ログが消えた可能性が高い（2コマンド制限内での確定不可）。

## 追加発見: commit 前エンキュー問題

### 現象（修正前）

`backend/app/services/tcg_line_import_svc.py:439`（修正前行番号）:

```python
# for old_rec ループ内
_enqueue_extraction(str(new_sm_id))  # ← db.commit() より前に呼ばれていた
```

`await db.commit()` は `:465`（修正前）にあり、`_enqueue_extraction` の呼び出しよりも後。
Celery タスクが発行された時点では DB トランザクションがまだ確定していない。

### リスク

`db.commit()` 前に `_enqueue_extraction` が呼ばれると、
rollback が発生した場合に extract タスクが DB に存在しない `source_message_id` で実行される（孤立タスク）。
本番では Redis エラーで握りつぶされているため顕在化していないが、設計上の欠陥。

### 修正

- ループ内: `enqueued_ids.append(str(new_sm_id))` で ID を蓄積
- `await db.commit()` の直後に `for sm_id in enqueued_ids: _enqueue_extraction(sm_id)`

守り手: `backend/tests/test_tcg_line_import.py::test_enqueue_called_after_commit`

## 影響範囲

- 修正ファイル: `backend/app/services/tcg_line_import_svc.py`
- 修正関数: `import_line_export`（step5 の supersede ループ 約10行の順序入れ替え）
- テスト: `backend/tests/test_tcg_line_import.py`（新規1件追加）

他に `import_line_export` を呼ぶ箇所: `backend/app/routers/tcg_line_import.py` のみ（変更なし）。

## 既存 ADR 調査

- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`（TCG LINE インポートパイプライン設計）— MIG-04 全体設計。FK 順序制約の記述なし。
- `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`（テナントスキーマ）— write 系: db.commit() 後 reset_tenant_context() 必須。本 PR 変更外。
