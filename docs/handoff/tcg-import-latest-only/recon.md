# recon — tcg-import-latest-only (SQR-05 移植)

## 調査対象

GAS SQR-05（tcg-inventory-parser PR #279）で変更された「仕入元別・最新1件採用」ロジックが、
Python 版 `backend/app/services/tcg_line_import_svc.py` に移植されていないことを確認し、修正する。

## 根本原因の特定

### GAS 側 変更（SQR-05 / PR #279、2026-08-30）

`~/sqr01_work/tcg-inventory-parser/Latest24LineImport.js` の `buildLatest24Dataset` (line 88):

```diff
- var raw = rows.map(function(m) { return m.body; }).join(LATEST24_SEPARATOR_);
+ var latestMsg = rows[rows.length - 1];
+ var raw = latestMsg.body;
```

`applyLatest24Extraction` (line 215) にも同等変更。

### Python 側 現状（SQR-05 未適用）

`backend/app/services/tcg_line_import_svc.py:221`（修正前）:

```python
raw_text = _MSG_SEPARATOR.join(m["body"] for m in sorted_msgs)  # 全件結合
```

→ GAS（最新1件のみ）と不一致。

## 影響範囲

- 修正ファイル: `backend/app/services/tcg_line_import_svc.py`
- 修正関数: `build_provider_entries`（line 194）
- 変更行数: 本体 2行変更 + 1フィールド追加
- `import_line_export` の戻り値: `skipped_message_count` 追加
- `backend/app/routers/tcg_line_import.py`: `ImportResultResponse` に `skipped_message_count: int` 追加
- テスト: `backend/tests/test_tcg_line_import.py`（既存2件更新 + 新規2件追加）

他に `build_provider_entries` を呼ぶ箇所は `import_line_export` のみ（grep 確認済み）。

## 既存 ADR 調査

- `docs/adr/ADR-154`（TCG LINE インポートパイプライン設計）— MIG-04 全体設計。SQR-05 相当の記述なし。
- `docs/adr/ADR-072`（テナントスキーマ）— write 系: db.commit() 後 reset_tenant_context() 必須。本PR 変更外。

## supersede の挙動（確認済み・変更なし）

`import_line_export` step5（`backend/app/services/tcg_line_import_svc.py:336〜`）:
- `build_provider_entries` が仕入元ごとに1エントリを返す
- 既存 `is_active=TRUE` レコードを `superseded_by` でリンクして無効化
- 新規1件を INSERT
- 同一アップロード内の複数メッセージは `build_provider_entries` で集約済みのため、supersede は機能しない（INSERT は1件のみ）
