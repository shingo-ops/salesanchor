<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 2 現在地 — 本番反映の移行が仕入元の表を2時間止めた件

**日付**: 2026-10-29  
**担当**: Planner（Opus）。調査は Sonnet。本番 DB は reader 鍵の道で読むだけ。

## 0. PO の依頼と選択（原文）
- 2026-10-29 本番 DB がつかえて本番反映が止まった件で、PO が「1」（原因を調べ、再発防止の案を作る）を選択。
- 調査報告のあと PO が「1」（この順番で正式な設計にまとめ、審査に通してから1つずつ直す）を選択。

## 1. 既存 ADR の検索結果
- ADR-1037（`docs/adr/ADR-1037-migration-lock-timeout.md`）: run_sql に lock_timeout=1s と再試行を付けた。run_py は対象外のまま。→ 今回はこの ADR の拡張とする。
- ADR-1005（`docs/adr/ADR-1005-migration-run-once-ledger.md`）: 移行を毎回全件流す。段階2（未実行だけ流す）は未着手。
- ADR-1003・ADR-135・ADR-136: scripts/ と deploy.yml は危険パスで GO 記録が要る。

## 2. 実物の照合（2026-10-29）
- `scripts/run_all_migrations.sh` :65-68 にロック待ちの値4つ、:76-105 に run_sql（PGOPTIONS と再試行あり）。:49-59 の run_py には上限も再試行も無い。
- `scripts/migrate_inventory_sprint1.py` :160 は `create_async_engine(url, echo=False)` だけ。asyncpg は PGOPTIONS を読まない（server_settings で渡す必要がある）。
- `migrations/056_add_suppliers_type_and_promote_public.sql` :114 の DROP TRIGGER IF EXISTS は suppliers の排他ロックを取りに行く。
- run_py の呼び出しは26本、うち接続を作るのは21本（内訳は design.md §4）。

## 3. 本番で観測した事実（読み取りのみ）
- 06:39Z の本番反映で run_py 経由の移行が 056 を流し直し、06:42〜08:35Z の約113分ロックを待った。
- 名前の無いアプリ接続1本が古い取引を開いたまま、suppliers 等にロックを保持していた。
- 待ちの後ろに計25接続が並び、読み取り監視の時間切れは1316件。
- 本番反映の ssh は10分で切れたが、サーバー側の処理は残り、以後6回の本番反映が失敗した。

調査の生出力は手元の作業メモにある（認証情報を含むため PR には載せない）。

## 4. 未確認
- ロックを保持していた接続の正体と、消えた理由（接続ログとロック待ちログが無効のため。design.md §3 段4で直す）。

## 5. 次
- 設計: `docs/handoff/deploy-db-stall/design.md`
