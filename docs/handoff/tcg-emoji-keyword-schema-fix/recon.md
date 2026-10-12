# recon: tcg-emoji-keyword-schema-fix

## 対象ADR
なし（既存機能のバグ修正のみ）

## 問題の実測

### キーワード件数の差異
- `public.product_search_keywords`: 708件（実測）
- `tenant_004.product_search_keywords`: 1,325件（実測）
- 差分: 617件が Gemini に渡されていなかった

### 根拠コード
`backend/app/services/tcg_work_reference.py:58-61`

修正前:
```sql
FROM public.product_search_keywords k WHERE k.product_id=p.id
FROM public.product_exclude_keywords k WHERE k.product_id=p.id
```

修正後:
```sql
FROM {schema}.product_search_keywords k WHERE k.product_id=p.id
FROM {schema}.product_exclude_keywords k WHERE k.product_id=p.id
```

`load_work_reference(session, schema)` は `schema` パラメータを受け取るが、
キーワードサブクエリが `public` ハードコードになっていた。

### 絵文字除去
`backend/app/services/gemini_extraction_svc.py`

`strip_emoji()` 関数を追加し、`format_prompt_input()` で呼び出す。
INVALID_RESPONSE エラーの一因として絵文字が Gemini レスポンスを乱す可能性があるため追加。
