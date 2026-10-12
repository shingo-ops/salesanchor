# recon: revert-keyword-schema

## 対象ファイル

- `backend/app/services/tcg_work_reference.py:47-70` — `load_work_reference()` 関数

## PR #3587 の変更内容

PR #3587 で以下3行が変更された:
- `backend/app/services/tcg_work_reference.py:49` — `text("""` → `text(f"""` (f-string化)
- `backend/app/services/tcg_work_reference.py:59` — `public.product_search_keywords` → `{schema}.product_search_keywords`
- `backend/app/services/tcg_work_reference.py:61` — `public.product_exclude_keywords` → `{schema}.product_exclude_keywords`

## 問題

Geminiが参照するキーワードは `public` スキーマ（共用マスタ）が正。
`{schema}` に変更すると tenant_004 スキーマを参照してしまい、
public スキーマへのキーワードコピーをしても改善が見込めない。

## 正しい修正方針

コードを `public` に戻し、データ側（tenant_004 → public コピー）で対処する。

## 関連ADR

- ADR検索: `git grep -i "keyword" docs/adr/` — 該当するADRなし
