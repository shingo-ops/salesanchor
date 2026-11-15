---
mode: handoff
---
# P10 の試し run_py 26本が流れるか（使い捨ての DB `p10_db` = `jarvis_report` の写し）

本報告はカード 前調査 5-0b の実行結果である。

- 読んだ commit: `d0f0a52544167df5e255cee6b00c50704474bd96`
- 手順2〜5・試験のファイルの全文: `common.md`（`test_p10_run_py`）。
- 使った命令（全文）: `cd /root/worktrees/salesanchor/release-migration-skip-applied-5-0/backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_0b.py -s -p no:cacheprovider -k "p01 or p08 or p09 or p10"`（`4 passed in 26.06s`）。P8 で終わった `jarvis_report`（13 表を1回流し直した後の状態。`p08.md`）に対し、`CREATE DATABASE p10_db TEMPLATE jarvis_report` で写しを作った。
- 流し方（`scripts/run_all_migrations.sh` の `run_py`（`:74-109`・`:85-88`）と同じ形。コンテナの `docker exec` だけ外した）:
  - 台本の一覧は `^run_py\s+` の行（`:287`〜`:657`の26行）を試験が読む。
  - 1本ずつ、作業場所を `backend/` にし（`cwd=backend`）、`PYTHONPATH` を付けずに、`/tmp/recon/venv/bin/python <repo>/scripts/migration_py_entry.py <repo>/scripts/<台本>.py` を `subprocess` で流した。env は `DATABASE_URL=postgresql://jarvis:testpass@localhost:55432/p10_db`・`MIGRATION_LOCK_TIMEOUT=1s`（`SQL_LOCK_TIMEOUT` の既定 `:57`）・`PGHOST`・`PGPORT`・`PGUSER`・`PGPASSWORD`。`:324` の `-e TENANT_CODE=highlife-jpn` は env の `TENANT_CODE=highlife-jpn` として渡した。
  - 落ちた台本だけ、`PYTHONPATH=<backend の絶対パス>`（`/root/worktrees/salesanchor/release-migration-skip-applied-5-0/backend`）を付けて、同じ命令でもう1回流した（2回目）。
  - 注: 本番では作業場所が `/app`（backend の中身と `scripts/`・`migrations/` が同じ所にある）。ここでは `backend/` を作業場所にして台本は絶対パスで指したので、台本が `migrations/` を相対パスで探す造りなら、本番とは違う動きになりうる（今回の26本で、そのために落ちた物は見つからなかった。未確認の範囲は、`migrations/` を相対で読む台本が26本にあるかどうか）。
  - `sleep`・流し直しの回数管理（`SQL_RETRY_*`）は再現していない（ロック競合が無い単独の DB のため）。

## 26本の表

| 登録の行 | 台本 | 1回目の終わりの番号 | 2回目（流し直した時だけ） | エラーの先頭の1行 | 外す候補か（理由） |
|---|---|---|---|---|---|
| 287 | scripts/migrate_meta.py | 0 | | | いいえ |
| 318 | scripts/migrate_meta_inbox_phase1d.py | 0 | | | いいえ |
| 319 | scripts/migrate_meta_inbox_phase1d_sprint4.py | 0 | | | いいえ |
| 320 | scripts/migrate_meta_page_routing.py | 0 | | | いいえ |
| 321 | scripts/migrate_meta_messages_page_id.py | 0 | | | いいえ |
| 324 | scripts/migrate_adr015_lead_foundation.py（`TENANT_CODE=highlife-jpn`） | 0 | | | いいえ |
| 342 | scripts/migrate_adr021_sprint2_financials.py | 1 | 1 | `asyncpg.exceptions.UndefinedTableError: relation "tenant_001.orders" does not exist` | はい（下の理由 A） |
| 343 | scripts/migrate_adr021_sprint3_shipping.py | 1 | 1 | 同上 | はい（理由 A） |
| 344 | scripts/migrate_adr021_sprint4_purchase.py | 1 | 1 | 同上 | はい（理由 A） |
| 345 | scripts/migrate_adr021_sprint5_commissions.py | 1 | 1 | 同上 | はい（理由 A） |
| 346 | scripts/migrate_adr021_remove_confirmed_status.py | 0 | | | いいえ |
| 349 | scripts/migrate_meta_messages_message_id_to_text.py | 0 | | | いいえ |
| 354 | scripts/migrate_adr041_granted_scopes.py | 0 | | | いいえ |
| 357 | scripts/migrate_009_phase4_tenant_tables.py | 0 | | | いいえ |
| 358 | scripts/migrate_011_phase5_tenant_tables.py | 0 | | | いいえ |
| 361 | scripts/migrate_inventory_sprint1.py | 0 | | | いいえ |
| 362 | scripts/migrate_inventory_sprint2.py | 0 | | | いいえ |
| 363 | scripts/migrate_inventory_sprint5_to_7.py | 0 | | | いいえ |
| 364 | scripts/migrate_inventory_sprint8.py | 0 | | | いいえ |
| 365 | scripts/migrate_inventory_sprint9.py | 0 | | | いいえ |
| 372 | scripts/migrate_073_lead_status.py | 0 | | | いいえ（中身なし。下） |
| 373 | scripts/migrate_074_rename_english_name_to_nickname.py | 0 | | | いいえ |
| 378 | scripts/migrate_20260620_080000_calendar_category_backfill.py | 0 | | | いいえ（中身なし。下） |
| 542 | scripts/migrate_adr109_status_codes.py | 0 | | | いいえ（中身なし。下） |
| 548 | scripts/migrate_adr119_lead_channels_backfill.py | 0 | | | いいえ（中身なし。下） |
| 657 | scripts/migrate_20260621_020000_backfill_lead_country.py | 1 | 0 | `ModuleNotFoundError: No module named 'app'` | いいえ（`PYTHONPATH=backend` を付ければ通る。下の理由 B） |

（生データ: `/tmp/recon/out/p10-result.tsv`。各本の出力の全文: `/tmp/recon/out/p10-logs/<行>-1.log`・`<行>-2.log`。）

## 合否の線: 通った本数・落ちた本数・外す候補の本数と理由

| 区分 | 本数 | 台本 |
|---|---|---|
| 1回目で通った | 21 | 上の表の「1回目 0」の行 |
| 1回目で落ち、`PYTHONPATH=backend` を付けて通った | 1 | `:657` migrate_20260621_020000_backfill_lead_country.py |
| 2回目でも落ちた | 4 | `:342`・`:343`・`:344`・`:345` |
| 通った合計 | 22 | |
| 落ちた合計 | 4 | |
| 外す候補（`dryrun-exclusions.tsv` に足す候補） | 4 | `:342`〜`:345` |

- **理由 A（外す候補 4本）**: 4本とも、最初の SQL（`tenant_001.orders` を指す）で `relation "tenant_001.orders" does not exist`。CI の全件ドライランの `tenant_001` は手書きの最小の表から作られ（`migration-test.yml` :1572 付近）、`orders` 表が無い（`p08-shape/columns.tsv` に `orders` の行が0件。本番 003 の `prod003/columns.tsv` には1件ある）。`PYTHONPATH` を付けても同じ（2回目も終わりの番号 1・同じエラー）。1回目と2回目のエラーの先頭の行は同じ。
- **理由 B（`:657`）**: `scripts/migrate_20260621_020000_backfill_lead_country.py:34` の `from app.services.country_codes import parse_country_code` が、作業場所を `backend/` にして `PYTHONPATH` が無いと `ModuleNotFoundError: No module named 'app'` になる。ただし、この台本の本文は何もせず終わる造り（下の「中身を無くした5本」）。`import` が先に走るので、中身が無くても落ちる。本番の `/app` ではこの問題が出るかは未確認（`/app` なら `app/` が作業場所の直下にあるため、`PYTHONPATH` 無しでも入れる可能性があるが、本番のコンテナでは試していない）。
- 「外す候補」の判断はカードの定義（空の DB で通らないことが実測で分かった物）に従った。`scripts/migration-guard/dryrun-exclusions.tsv` は書き換えていない。
- 参考: `:287`〜`:365` と `:373` の21本のうち、`DATABASE_URL` を読んで `create_async_engine` を作った台本は、入口が1回ずつ `lock_timeout=1s applied to 1 engine(s)` を出した（4本の落ちた台本を含めて21本。`-1.log` の末尾）。

## 中身を無くした5本（`recon-5-0a/p10.md` の「接続しない」の5本）が、流れても何もしないこと

| 登録の行 | 台本 | 終わりの番号 | 標準出力の原文 | 標準エラーの末尾の原文 |
|---|---|---|---|---|
| 372 | migrate_073_lead_status.py | 0 | `ADR-1007 neutralized: migrate_073_lead_status.py no longer writes values` | `migration_py_entry: lock_timeout=1s applied to 0 engine(s)` |
| 378 | migrate_20260620_080000_calendar_category_backfill.py | 0 | `ADR-1007 neutralized: migrate_20260620_080000_calendar_category_backfill.py no longer writes values` | `... applied to 0 engine(s)` |
| 542 | migrate_adr109_status_codes.py | 0 | `ADR-1007 neutralized: migrate_adr109_status_codes.py no longer writes values` | `... applied to 0 engine(s)` |
| 548 | migrate_adr119_lead_channels_backfill.py | 0 | `ADR-1007 neutralized: migrate_adr119_lead_channels_backfill.py no longer writes values` | `... applied to 0 engine(s)` |
| 657 | migrate_20260621_020000_backfill_lead_country.py | 1回目 1（`ModuleNotFoundError`）／2回目 0 | 2回目: `ADR-1007 neutralized: migrate_20260621_020000_backfill_lead_country.py no longer writes values` | 2回目: `... applied to 0 engine(s)` |

- 5本とも、DB に1回も接続しない（`applied to 0 engine(s)`）。流れても何もしない: ○。ただし `:657` だけは、`app` を import する行が先にあるため、`PYTHONPATH` が無いと何もしない前に落ちる（理由 B）。
