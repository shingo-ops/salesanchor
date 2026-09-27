# design: extraction-error-detail

## 目的

抽出エラー発生時にエラーの種類（カテゴリ）と詳細（raw message）を `extraction_attempts.validation_result` に記録し、ダッシュボードで診断できるようにする。

## 変更点

### 1. `_classify_error()` 追加（gemini_extraction_svc.py）

Gemini API例外をカテゴリに分類する関数。

| カテゴリ | 条件 |
|---|---|
| `gemini_rate_limit` | HTTP 429 または `RESOURCE_EXHAUSTED` |
| `gemini_http_error` | HTTP 4xx/5xx |
| `gemini_timeout` | "timeout" または "deadline" を含む |
| `gemini_unknown` | 上記以外 |

`from None` チェーンは維持（SQLペイロード漏洩防止の意図的設計）。`_safe_error_message()` を通してAPIキーを除去した上で記録。

### 2. `record_error_detail()` 追加（tcg_extraction_record_svc.py）

`AttemptRecorder` に `_error_detail: dict` 属性と `record_error_detail()` メソッドを追加。`fail()` 内で `_error_detail` が存在する場合は `validation_result` に `category`/`raw` を追加して書き込む。

migration 不要（`validation_result` は既存の JSONB カラム）。

### 3. `_classify_system_error()` 追加（tcg_extraction.py）

RecordError コードをカテゴリにマッピング。

| コード | カテゴリ |
|---|---|
| `RECORD_WRITE_FAILED`, `CLAIM_CONFLICT`, `ATTEMPT_CONFLICT` | `system_db_error` |
| `INPUT_TOO_LARGE`, `RESPONSE_TOO_LARGE`, `PARSED_TOO_LARGE` | `system_input_error` |
| `INVALID_RESPONSE` | `logic_parse_error` |
| `WORK_ID_CONFLICT`, `REFERENCE_CHANGED` | `logic_conflict` |
| その他 | `system_unknown` |

`SoftTimeLimitExceeded` は `system_timeout` で固定。

### 4. `GET /tcg/extraction-errors` 変更（tcg_analysis_dashboard.py）

`LEFT JOIN LATERAL` で最新の `extraction_attempts` を取得し、`validation_result` から `category`/`raw` を読み出す。

## 検証基準

| 基準 | 検証方法 |
|---|---|
| `validation_result` にエラー詳細が記録される | `SELECT validation_result FROM extraction_attempts WHERE phase='failed'` で `category`/`raw` フィールドを確認 |
| `/tcg/extraction-errors` が `error_category`/`error_detail` を返す | API レスポンスを確認 |
| 既存テストが壊れない | `python3 -m pytest tests/test_tcg_gemini_extraction.py tests/test_gemini_error_redact.py tests/test_tcg_diagnostics.py --no-cov` |

## 外部・過去事例の参照と我々への応用

Sentry/Datadog等のAPMツールでは、エラーをカテゴリ（rate_limit/timeout/http_error等）に分類してダッシュボードに表示する設計が標準的。本実装はDBの既存JSONBカラムを活用し、同様の分類情報を記録する。GeminiのRATE_EXHAUSTED/タイムアウトは頻出エラーパターンであり、カテゴリ分類により原因の素早い特定が可能になる。

## 維持の仕組み

- 守り手: Hikky-dev（Claude Code）
- Geminiの新しいエラーパターンが追加された場合は `_classify_error()` のマッピングを更新する
- `_SYSTEM_ERROR_CATEGORIES` への新コード追加は `RecordError` 新規コード追加時に合わせて行う
