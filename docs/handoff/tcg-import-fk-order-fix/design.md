# design — tcg-import-fk-order-fix (supersede FK 順序修正)

参照: `docs/handoff/tcg-import-fk-order-fix/recon.md`
ADR 参照: ADR-154

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| LINE エクスポートアップロードが「データベースエラー」なく完了する | 本番で 1713.7 KB ファイルをアップロードし status: "imported" が返ること |
| INSERT INTO source_messages が UPDATE source_messages より先に呼ばれる | `pytest backend/tests/test_tcg_line_import.py::test_source_message_insert_before_update_supersede` PASS |
| 既存テスト 31 件が全件 PASS を維持 | `pytest backend/tests/test_tcg_line_import.py --no-cov` 32 passed |

## 外部・過去事例の参照と我々への応用

PostgreSQL の FK `NOT DEFERRABLE INITIALLY IMMEDIATE`（デフォルト）は
UPDATE/INSERT の各文実行直後に制約チェックを行う。
自己参照 FK（`superseded_by REFERENCES source_messages(id)`）を持つテーブルで
「参照先をまず INSERT してから参照元を UPDATE する」順序は標準パターン。
逆順で実装されていた本ケースは FK 制約の即時チェックを看過した設計ミス。
（代替: DEFERRABLE INITIALLY DEFERRED に変更すれば逆順も許容されるが、migration 追加を要するため採用しない）

## 修正方針

`import_line_export` の step5 ループ内で `received_at` 変換と INSERT/UPDATE の順序を入れ替える。
ロジック・SQL 文の内容は変えない。

### 変更前後（`backend/app/services/tcg_line_import_svc.py:377〜423`）

```python
# 変更前（FK 違反）
new_sm_id = uuid.uuid4()
for old_rec in active_records:          # UPDATE（new_sm_id はまだ DB にない）
    await db.execute(UPDATE superseded_by = new_sm_id ...)
try:
    received_at_dt = ...
except:
    received_at_dt = None
await db.execute(INSERT INTO source_messages (id=new_sm_id, ...))  # INSERTが後

# 変更後（FK 違反なし）
new_sm_id = uuid.uuid4()
try:
    received_at_dt = ...
except:
    received_at_dt = None
await db.execute(INSERT INTO source_messages (id=new_sm_id, ...))  # INSERTが先
for old_rec in active_records:          # UPDATE（new_sm_id が DB に存在する）
    await db.execute(UPDATE superseded_by = new_sm_id ...)
```

### 戻し方

INSERT ブロックと UPDATE ループを再び逆順に入れ替える（1手順）。
ただし本修正が正しい対応であり revert は不要。

## 維持の仕組み

守り手: `backend/tests/test_tcg_line_import.py::test_source_message_insert_before_update_supersede`
（db.execute の呼び出し順を追跡し、INSERT が UPDATE より先であることを CI pytest で毎PR検証）
