# recon: extraction-error-detail

## 対象ADR

- ADR検索結果: `git grep -i "extraction" docs/adr/` で関連ADRを確認
- extraction_attempts / validation_result に関するADRなし（新規実装）
- 既存のエラーログ設計: `backend/app/services/tcg_extraction_record_svc.py:166` の `validation_result` JSONB カラムを活用

## 現状の実装

### gemini_extraction_svc.py

- `_safe_error_message()`: `backend/app/services/gemini_extraction_svc.py:162`
  - APIキーを除いた安全なエラーメッセージを生成
- `call_gemini_extraction()` の except ブロック: `backend/app/services/gemini_extraction_svc.py:377-381`
  - `recorder` がある場合は `RecordError("API_ERROR")` を raise するが、エラー詳細は記録しない

### tcg_extraction_record_svc.py

- `AttemptRecorder.__init__()`: `backend/app/services/tcg_extraction_record_svc.py:52-61`
- `fail()` メソッド: `backend/app/services/tcg_extraction_record_svc.py:166-192`
  - `validation_result=jsonb_build_object('status','failed','code',CAST(:code AS text))` のみ
  - エラー詳細（category, raw）は記録されない

### tcg_extraction.py

- `_run_extraction()` の except ブロック: `backend/app/tasks/tcg_extraction.py:224-231`
  - `SoftTimeLimitExceeded` / `RecordError` / 汎用 `Exception` を catch
  - エラー詳細は `recorder.fail(code)` に渡すだけで分類情報なし

### tcg_analysis_dashboard.py

- `list_extraction_errors()`: `backend/app/routers/tcg_analysis_dashboard.py:363-393`
  - `extraction_jobs` からのみクエリ。`extraction_attempts.validation_result` を参照しない
  - レスポンスに `error_category`/`error_detail` なし

## 変更前後の比較

| 項目 | 変更前 | 変更後 |
|---|---|---|
| `validation_result` の内容 | `{"status":"failed","code":"API_ERROR"}` | `{"status":"failed","code":"API_ERROR","category":"gemini_rate_limit","raw":"レート制限超過 (HTTP 429)"}` |
| `/tcg/extraction-errors` レスポンス | `error_category: null`, `error_detail: null` | `error_category: "gemini_rate_limit"`, `error_detail: "レート制限超過 (HTTP 429)"` |
