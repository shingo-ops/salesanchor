# ADR-1037: 入れ替え時の migration はロック待ちを1秒で諦め、間を空けて流し直す

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-21） |
| 備考 | PO 2026-10-21「1」で次の成功条件を承認：「アプリの入れ替え中に在庫表を開いても、1回の表示が2秒を超えない（作り替えの作業がほかを待たせるのは最大1秒まで）」「待たせ合いで入れ替えが失敗する回数を0にする（今は週4回）」。設計は PO の委任に基づき Opus が決定。 |
| 起案日 | 2026-10-21 |
| 方針の決定者 | Shingo（PO）＝成功条件。実現方法＝Claude Opus（委任） |
| 関連 | ADR-1005（毎回全件を流す作り。段階2で変わる）、ADR-1003（DROP を含む migration は委任 GO 対象外）、ADR-135、ADR-136 |
| 設計 | `docs/handoff/migration-lock-timeout/design.md`、現状 `docs/handoff/migration-lock-timeout/recon.md` |

---

## What（何を決めたか）

1. `scripts/run_all_migrations.sh` の run_sql で流す SQL は、接続ごとに `lock_timeout=1s` を付けて流す（`docker exec -e PGOPTIONS`）。DB・ロール全体には付けない。
2. "deadlock detected" と "canceling statement due to lock timeout" で落ちたファイルは、3秒あけて流し直す。1回の実行全体で再試行は合計40回まで。1ファイルでもその40回まで使える（便1.1 で、1ファイル最大10回から変えた）。上限に達したら今までどおり止める。ほかのエラーは即停止。
3. 値の正本は `scripts/run_all_migrations.sh` の `SQL_LOCK_TIMEOUT`・`SQL_RETRY_MAX_ATTEMPTS`・`SQL_RETRY_SLEEP_SEC`・`SQL_RETRY_BUDGET` の4行だけ。環境変数での上書きは試験のためで、deploy.yml・.env には書かない。
4. 挙動は `tests/sandbox/migration-run-sql-retry.sh`（本物の run_sql を抜き出して使い捨て DB で試す）で確かめる。run_sql を変えたらこの試験を流す。
5. 鍵が取れなかったとき（ファイルごとの1回目と上限到達時）は、開始から1秒を超えて開いている接続をログに書く（便1.1）。
   - 出すのは、接続番号・利用者名・アプリ名・状態・待ちの種類・秒数・命令の先頭の英字の並び・鍵を持つ表名（今の DB の分）だけ。
   - SQL の文面・接続元アドレス・値は出さない。このリポジトリは公開で、Actions のログは外から読めるため。
6. 移行の一覧を流している間、裏で読み取りの計測を回し、移行の鍵のせいで読み取りが何ミリ秒待たされたかを入れ替えのログに書く（便1.2。設計 `docs/handoff/migration-lock-timeout/design.md` §14）。
   - 2秒ごとに、在庫表の GET が読む14表を1表1文（`SELECT 1 … LIMIT 1`）で読み、1回の時間を測る。2秒を超えた回の時刻と、まとめの1行（`read probe: n= slow= error= invalid= max=`）を書く。SQL の文面と表名は出さない。
   - 値の正本は `scripts/run_all_migrations.sh` の `READ_PROBE_*` の4行。計測の表が在庫表のクエリとずれないことは `backend/tests/test_read_probe_tables.py` で、挙動は `tests/sandbox/migration-read-probe.sh` で確かめる。
   - 計測の成否は入れ替えの成否・終了コードを変えない。
7. 成功条件の「入れ替え中の在庫表が2秒以内」は、「移行の鍵による読み取りの待ちが2秒以内（上の計測の slow=0）」で判定する（PO 2026-10-22「1」）。鍵を待たない部分（在庫表のクエリそのものの時間）は移行と関係なく、Prometheus の普段の値で見る。
   - 在庫表の API を本当に呼ぶ測り方は採らない。スモーク用の利用者の権限を ADR-1017 の最小権限より広げることになり、1回が画面表示と同じ重さで鍵を持つため。

## Why（なぜ）

- 入れ替えのたびに全 migration を流し直し（ADR-1005）、その中の `DROP TABLE IF EXISTS public.parse_logs` が FK 先の products に最強のロックを取りに行く。今はロック待ちに上限が無く、待っている間は後から来た在庫表の読み取りも全部止まる。試験用 DB の再現で、後から来た読み取りが 8912ms 待たされた。lock_timeout=1s では 1085ms で諦め、読み取りは止まらず、流し直しで 84ms で通った（`docs/handoff/migration-lock-timeout/recon.md` §4）。
- 本番では 10/19 の入れ替え中に在庫表の平均が最大 13.5 秒になり、deadlock で在庫表が 500 を返した。直近300回の入れ替えで deadlock による失敗が4件あり、4件とも run_sql 側だった（同 §3）。
- 回数と間隔は、移行ステップの打ち切り10分（ssh-action v1 の既定）と通常の所要最大138秒から決めた。最悪でも約300秒（5秒待ちの8ファイルが毎回上限まで待っても458秒）に収まる。
- PostgreSQL 公式文書は lock_timeout のサーバー全体設定を勧めていない。アプリの接続の挙動を変えないため、移行の接続だけに付ける。

## 対象外（この ADR では決めない）

- `SET LOCAL lock_timeout = '5s'` を持つ 8 ファイル（そのトランザクションの中では5秒待つ）。2本は DROP を含み、変えるには PO 本人の GO が要る。
- （対象外だったが 2026-10-29 に拡張で対象にした）run_py（Python の移行）の接続。下の「拡張」を参照。
- parse_logs を毎回作って消すこと（ADR-1005 の段階2で扱う）。

## 結果

- 便1（PR #4610）の入れ替え1回目（Deploy to VPS run 39575250541、2026-10-21 09:22 UTC）は失敗した。
  - `migrations/082_extend_products_box_attributes.sql` が約38秒、lock timeout を10回続け、1ファイルの上限で止まった（全体の再試行は 9/40）。
  - products の鍵を離さなかった接続が何だったかは未確認。
  - 失敗時に ai_ro のビューが外れ、次の入れ替え（run 39575404756、同 09:30 UTC 成功。"lock conflict" 0行）で戻った。
  - この結果を受けて便1.1（What 2・5）にした。設計は `docs/handoff/migration-lock-timeout/design.md` §13。
- 便1.1（PR #4613）の入れ替え1回目（Deploy to VPS run 39584411250、2026-10-21 10:28〜10:29 UTC）は成功した。
  - 移行ステップは77秒。"lock conflict; retry" 1回（`migrations/20261009_180000_v102_engine_columns.sql`、全体 1/40）、"retry limit reached" 0回。
  - 鍵の持ち主の一覧が1回出た。開いていたのは `salesanchor_celery_viewer_cache` の SELECT（1秒）で、文面・値は出ていない（K9 合格）。
  - K7 は判定不能。移行の時間帯に Prometheus の在庫表 GET の系列が無かった（再起動で系列が消え、10:20〜10:30 UTC に0件）。次の回で数える。
  - K6（失敗0回）は、この回を1回目として数える（1/3）。
- 便1.1 以降、移行ステップのある入れ替え3回分の結果を追記する。書くのは、失敗回数、"lock conflict; retry" と "retry limit reached" の回数、移行中に在庫表が2秒を超えた件数。
- 移行ステップのある入れ替え2回目（Deploy to VPS run 39604739864、PR #4618、2026-10-21 13:07:43〜13:08:59 UTC）は成功した。
  - "lock conflict; retry" 0回、"retry limit reached" 0回、"lock holders" 0回。K6 は 2/3（失敗0）。
  - 間の run 39595679550・39602336552 は移行ステップが skipped（`Filter db_migrations = false`）なので、回数に入れない。
  - K7 は今回も判定不能。
    - 訂正（#4621 の記載の誤り）: handler="/api/v1/inventory" の系列は Prometheus にある。在庫表が行を取る API も GET /api/v1/inventory（`frontend/src/pages/inventory/InventoryPage.tsx:227` → `backend/app/routers/inventory_offers.py:351`）で、design の名前は正しかった。
    - 測れなかった理由は、移行の時間帯（13:05〜13:12 UTC、10:25〜10:32 UTC）にこの GET が0件だったため（どちらの時間帯にも該当の系列が無い）。この系列は 10/21 09:15 UTC 以降は増えていない。
    - Loki に nginx のアクセスログは無いので、Loki では在庫表の GET を数えられない。
    - 計測（`backend/app/metrics.py`）は、1件目の要求で系列を作り、再起動で0に戻す。待っているだけでは、移行中に在庫表が開かれた回しか数えられない。
    - 移行中にこちらから在庫表の GET を流して測る方法を決めるまで、K7 は測れない（PO 判断）。
    - その後: PO 2026-10-22「1」で、K7 は What 7 の数え方に変えた（便1.2）。便1.2 の後の入れ替えから、K7 を3回分数える。
  - 生の記録: Mac の /tmp/CC報告ファイル/ai-ro-restore/k67/report.md（リポジトリ外）。
- 便1.2（PR #4626）の入れ替え（Deploy to VPS run 39634747232、2026-10-21 16:29:11〜16:30:41 UTC。移行ステップの開始・終了時刻）は成功した。移行ステップのある入れ替えの3回目。
  - "lock conflict; retry" 3回（`migrations/20261017_125900_drop_ai_ro_views.sql` 2回、`migrations/20260922_040000_fix_phase2c_fk_blocker.sql` 1回、全体 3/40）、"retry limit reached" 0回。K6 は 3/3（失敗0）で合格。
  - 鍵の持ち主の一覧が2回出た。開いていたのは `ai_reader`（6秒、読み取りの鍵だけ）と `salesanchor_celery_viewer_cache` の SELECT（1秒）。文面・値は出ていない（K9）。
  - 計測のまとめは `read probe: n=35 slow=0 error=0 invalid=0 max=797ms`。K10 は合格（prod1 で `$EPOCHREALTIME` が取れた）。
  - K7 は 1/3（slow=0・error=0）。この回は ai_ro のビューを外す run_sql（計測を始める前）で鍵待ちがあったが、計測は trap の後から始まるため、その分は数えていない（design §14-3）。
  - 生の記録: Mac の /tmp/CC報告ファイル/k7-probe/deploy-39634747232.txt（リポジトリ外）。
- 2026-10-22 便2 は保留（PO「1」）。調べた時点で、5秒の8ファイルに由来する待ちは入れ替え3回で0件、read probe も slow=0。K7 の残り2回で該当ファイルの待ちが出たら再相談する。根拠: docs/handoff/migration-lock-timeout/design.md の便2の行と :366。

## 拡張（2026-10-29・deploy-db-stall 段1）

- 2026-10-29 に本番反映の Python の移行が約113分ロックを待ち、アプリの読み取りを止めた。PO「1」で、run_py（Python の移行）の接続にも同じロック待ち1秒と流し直しを付けることにした。設計は docs/handoff/deploy-db-stall/design.md（第7版 APPROVE）。
- 付け方は入口方式。run_py が移行を直接ではなく `scripts/migration_py_entry.py` 経由で動かし、入口が `create_async_engine` を差し替えて接続ごとに lock_timeout（`SQL_LOCK_TIMEOUT` と同じ値）と application_name=salesanchor_migration を付ける。移行本体は変えない。
- 流し直しの判定文字列・回数・間隔・全体上限（合計40回）は run_sql と共有する。
- 見張りは `.github/workflows/migration-test.yml`（S1〜S3・P1〜P3）、`tests/sandbox/migration-run-sql-retry.sh`（R1〜R4）、`tests/sandbox/migration-read-probe.sh`（R5）。
- 第8版で run_py の標準エラーを run_sql と同じ形（一時ファイルに書いてから出す）にした。最初の入れ方（PR #4861）はプロセス置換の後に裏の番号を待つ書き方で、本番反映が止まり PR #4862 で戻した（docs/handoff/deploy-db-stall/design.md §14）。

## 追記（2026-10-30・deploy-db-stall 段2）

- `application_name=salesanchor_migration` の意味を広げた。run_py に加えて run_sql の接続にも付く（`PGAPPNAME`）。さらに、本番反映の取り残しを片付ける `scripts/deploy-db-orphan-cleanup.sh` が、この名前の接続を切る目印として使う。名前の正本は `scripts/lib/db-app-names.sh`。
- 控え（backup.sh）にも `salesanchor_backup_deploy`（本番反映）と `salesanchor_backup_cron`（毎朝3時。片付けの対象外）を付けた。設計は docs/handoff/deploy-db-stall/design.md §16。
