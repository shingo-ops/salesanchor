# SEC-01 recon: Gemini エラーメッセージ API キー漏洩

## 調査日
2026-09-05

## 問題

### 事実

`backend/app/services/gemini_extraction_svc.py:268`
```python
"error_message": str(exc),
```

`backend/app/tasks/tcg_extraction.py:95`
```python
"error_message": str(exc),
```

Gemini SDK が API 呼び出し失敗時に送出する例外には、リクエスト URL がそのまま含まれる場合がある。
例:
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=AIzaSyXXXXX returned 429
```

`str(exc)` をそのまま `extraction_jobs.error_message` に保存すると、APIキーの値がDBに永続化される。

### 流れ（コールスタック）

```
tcg_extraction.extract_and_analyze_source_message()
  └─ _run_extraction()
       └─ gemini_extraction_svc.extract_message()
            └─ call_gemini_extraction()
                 └─ client.models.generate_content()  ← SDK 例外発生
                 └─ raise RuntimeError(f"Gemini API 呼び出し失敗: {exc}")  ← key= が含まれる
            └─ except: error_message = str(exc)  ← DB 保存
       └─ UPDATE extraction_jobs SET error_message = :error_message  ← DB 永続化
```

### 既存 ADR

`git grep -i key docs/adr/` → 関連 ADR なし（セキュリティ一般は ADR-025）

## 影響範囲

| ファイル | 行 | 変更内容 |
|---------|---|----|
| `backend/app/services/gemini_extraction_svc.py` | 46-79, 133, 268 | `_safe_error_message()` 追加・適用 |
| `backend/app/tasks/tcg_extraction.py` | 29, 95 | `_safe_error_message` インポート・適用 |
| `backend/tests/test_gemini_error_redact.py` | 新規 | テスト 11 件 |

## 触らない範囲

- DB スキーマ（`extraction_jobs.error_message` カラム定義は変更なし）
- Celery タスク定義
- プロンプト定数・パーサーロジック
