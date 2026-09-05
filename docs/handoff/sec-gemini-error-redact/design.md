# SEC-01 design: Gemini エラーメッセージ sanitize

## KGI

DB `extraction_jobs.error_message` に `key=<値>` が保存されない。

| 基準 | 検証方法 |
|------|---------|
| `error_message` に文字列 `key=` を含まない | テスト `test_api_exception_with_key_in_url_is_redacted` が GREEN |
| 429 等の HTTP ステータスは日本語で表示される | テスト `test_rate_limit_error_shows_japanese_reason` が GREEN |

## 設計

### `_safe_error_message(exc: Exception) -> str`

`gemini_extraction_svc.py` に追加するユーティリティ関数。

```
入力例外 → str(exc)
           ↓
           HTTP 4xx/5xx を正規表現で検索
           ↓ 見つかった場合
           「理由 (HTTP NNN)」を返す  ← key= を含まない
           ↓ 見つからない場合
           re.sub(r"key=[^\s&'\"<>]+", "(APIキー省略)", msg) を返す  ← key= を含まない
```

### HTTP ステータスマッピング

| コード | メッセージ |
|-------|-----------|
| 400 | リクエストエラー |
| 401 | 認証エラー |
| 403 | アクセス拒否 |
| 429 | レート制限超過 |
| 500 | サーバーエラー |
| 503 | サービス利用不可 |
| その他 4xx/5xx | HTTPエラー |

### 適用箇所

1. `call_gemini_extraction()` → RuntimeError を raise するとき
2. `extract_message()` → except で error_message を設定するとき
3. `extract_and_analyze_source_message()` → outer except で error_message を設定するとき

### 外部事例

Google Gemini SDK は `google.api_core.exceptions.ResourceExhausted` 等を送出し、メッセージにリクエスト URL（`?key=<value>` 付き）を含める実装になっている。同様の sanitize パターンは OpenAI SDK wrapper 等でも広く採用されている。

### 守り手

- `backend/tests/test_gemini_error_redact.py` の 11 件のテストが regression guard として機能する
- CI (pytest) が通ること

### 弊害

- エラーログ（logger.exception）には生の例外が残る（ログはローテートされるが永続化されない）
- デバッグ時は `extraction_jobs.error_message` だけでは詳細不明になるが、ログで補える

### 戻し方

`_safe_error_message()` を削除し、`str(exc)` に戻す（1コミットで完全に戻せる）
