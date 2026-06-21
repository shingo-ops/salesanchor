# Foundation F1 design

測定日: 2026-06-21

## 目的

- `public.countries` を新設し、ISO alpha-2 の国マスタを全テナント共有で提供する。
- `GET /countries` を read-only で返す。

## 実装方針

- テーブル:
  - `code CHAR(2) PRIMARY KEY`
  - `name TEXT NOT NULL`
  - `dial_code TEXT NOT NULL`
  - `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- migration 内で `frontend/src/constants/countries.ts` と同じ国一覧を seed する。
- API は `backend/app/routers/countries.py` に置き、`backend/app/main.py` で登録する。
- SQLite テストは `backend/tests/conftest.py` で `countries` を作成し、frontend の SSOT から seed する。

## テスト

- migration test: `backend/tests/test_countries_master.py`
- API test: `backend/tests/test_countries_master.py`

## スコープ

- 追加のみ。既存の `country_code` の UI 統制や backfill は次 PR。
