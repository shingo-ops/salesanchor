# 実装カード — S3 db-error-detail

**設計**: [design.md](design.md)（審査 APPROVE: [review-opus.md](review-opus.md)）　**KGI**: [../../specs/db-error-detail/kgi.md](../../specs/db-error-detail/kgi.md)（PO 承認 2026-10-16「y」）
**作業場所**: /Users/tanizawashingo/worktrees/salesanchor/release-s3-hide-db-error-detail（ブランチ release/s3-hide-db-error-detail）

## 手順

1. 実物点検: recon.md 付録の 59 件の行が、いまの HEAD でも同じ中身か確かめる（行がずれていたら関数名で探す。中身が違えば止めて報告）。
2. 赤を先に: backend/tests/test_no_exception_text_in_http_detail.py を design §5 T1 のとおり書き、変更前のコードで走らせて 59 件を見つけて落ちることを確かめる。出力を /tmp/CC報告ファイル/s3-sql/impl/t1-red.txt に保存。59 件でなければ止めて報告。
3. backend/app/routers/_utils.py に `log_hidden_error` を design §2 の中身のとおり足す。T2 を backend/tests/test_db_exceptions.py に足す。
4. 59 件を design §2 の型で書き換える。detail は前置きだけ（末尾の `: ` を消す）。buyback_prices.py と erp.py は design §2 の注記どおり。
5. T3 を backend/tests/test_super_admin_unit_ignore_phrases.py の重複 409 試験に足す。期待する detail は super_admin_unit_ignore_phrases.py の該当行の前置きに合わせる。
6. 緑の確認: T1・T2 と、59 件のファイルに対応する既存試験をローカルで走らせる。出力を /tmp/CC報告ファイル/s3-sql/impl/ に保存。`cd backend && ruff check app tests` も通す。
7. commit（push はしない）。

## 想定分岐

- 59 件のどこかで except の変数を detail 以外にも使っている（例 erp.py の erp_sync_logs）→ その使い方は残す。
- T1 が対象外の 48 件のどれかを拾う → 止めて報告（型の集合の見直しは Opus が決める）。
- detail を別の変数に入れてから渡す形を見つけた → 書き換えたうえで報告に件数を書く。
- 既存試験が detail の旧文言を見ていて落ちる → 止めて報告（recon §5 では 0 件のはず）。

## 触らない

backend/app/main.py、backend/app/database.py、frontend、migrations、.github、nginx、対象外の 48 件。
