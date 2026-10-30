<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 本番反映の移行が仕入元の表を2時間止めた件の再発防止

**対象ADR**: ADR-1037（拡張。新規 ADR は作らない）。関連 ADR-1005・ADR-1003・ADR-135・ADR-136  
**日付**: 2026-10-29  
**担当**: Planner（Opus）。状態（2026-10-30）: 段1は第8.1版で本番反映済み（PR #4864、本番測定3/3回で K8・K9a 合格、K9b は該当なし）。段3は §15 で本番反映済み（PR #4867、K3-4〜K3-6 合格。K3-4 は PO 2026-10-30 の決定で手の3回に置き換えた）。段2は §16 の設計が審査済み・マージ済み（PR #4868）、実装 PR #4872 は 2026-10-30 に本番反映済み（K2-5・K2-6 は1/3回合格、K2-7 は翌朝3時）。段4は §17 に設計案  
**PO の選択**: 2026-10-29「1」（この順番で正式な設計にまとめ、審査に通してから1つずつ直す）

---

## 1. 目的（PO の言葉に沿って）
- 本番反映の移行が、アプリの読み取りを1.5秒より長く待たせない。
- 本番反映が時間切れで失敗しても、サーバーに作業が取り残されない。
- 次に同じことが起きたら、ロックを握った接続が名前でわかる。

## 2. 起きたこと（事実）
調査の生出力は手元の作業メモにある（社内のみ。PR には載せない）。以下は照合済みの事実だけ。
- 2026-10-29 06:39Z の本番反映で、run_py 経由の `scripts/migrate_inventory_sprint1.py` が 056 を流し直した（適用済みの記録は無い。ADR-1005 段階2 未着手）。
- `migrations/056_add_suppliers_type_and_promote_public.sql` :114 の DROP TRIGGER IF EXISTS は、トリガーがあっても suppliers の排他ロックを取りに行く。
- 名前の無い salesanchor_app の接続1本が、古い取引を開いたまま suppliers 等約151個にロックを保持していた（db-locks の読み取り結果）。
- `scripts/migrate_inventory_sprint1.py` :160 は `create_async_engine(url, echo=False)` だけで、ロック待ちの上限が無い。`scripts/run_all_migrations.sh` :49-59 の run_py は PGOPTIONS も再試行も無い。asyncpg 0.31.0 は PGOPTIONS を読まない。
- 移行は約113分（06:42〜08:35Z）待ち続けた。その後ろにアプリ・定期処理・バックアップの計25接続が並んだ。読み取り監視の時間切れは1316件。
- 本番反映の ssh は10分で切れたが、サーバー側の移行とバックアップは残った。以後6回の本番反映がバックアップ待ちで失敗し、取り残しのバックアップが6本積み重なった。
- 08:35:38Z ごろ保持していた接続が消え、自然に解けた。

未確認: 保持していた接続の正体と消えた理由。接続ログとロック待ちログが無効で特定できない（§3 の段4で直す）。

## 3. 直す順番（一度に1つ。前の段を本番で測ってから次へ）
| 段 | 内容 | 本番への影響の種類 | 状態 |
|---|---|---|---|
| 1 | Python の移行（run_py）にもロック待ち1秒と再試行を付ける（§4） | 本番 scripts・deploy.yml の db_migrations・CI（委任 GO。ADR-1003 の例外7種に当たらない） | 本番反映済み（PR #4864）。本番測定3/3回で合格（2026-10-30） |
| 2 | 本番反映が時間切れのとき、サーバー側の移行・バックアップも止める。開始時に取り残しを片付ける | deploy.yml | §16 の設計マージ済み（PR #4868）。実装 PR #4872 は 2026-10-30 に本番反映済み。K2-5・K2-6 は1/3回合格（移行のある本番反映を待つ）、K2-7 は翌朝3時 |
| 3 | `scripts/backup.sh` :27-29 の pg_dump にロック待ちの上限を付ける | 本番 scripts | §15 で実装・本番反映済み（PR #4867）。K3-4〜K3-6 合格（K3-4 は手の3回で代えた。§15 の状態の行） |
| 4 | アプリの同期接続に名前を付ける。ロック待ちログを有効にする | backend・DB 設定 | §17 に設計案（4a 名前を付ける・4b ロック待ちのログ）。本番は段2の K2-5〜K2-7 の後 |
| 5 | 056 など、流し直しのたびに排他ロックを取る書き方をやめる（存在を確かめてから DROP、または適用済みの記録） | migrations/（PO 本人の GO の要否を確認） | 詳細設計は `docs/handoff/migration-runner-redesign/design.md` §5（ADR-1005 段階1・2 の再開、第7版で設計審査 APPROVE）。次は前調査 P1〜P13（読むだけ） |

段1を先にする理由: 段1だけで「アプリが2時間止まる」形が「最大1秒待って離す」形に変わる。段2〜5は止まった後の後始末と原因の特定で、効き目は段1より小さい。

## 4. 段1 変更前 → 変更後（第2版で入口方式に変えた）

本数の定義（実物 2026-10-29）: run_py の呼び出しは26本（`scripts/run_all_migrations.sh` :224, :255-258, :261, :279-283, :286, :291, :294-295, :298-302, :309-310, :315, :479, :485, :594）。うち create_async_engine で接続するのが21本。残り5本（073・calendar_category_backfill・adr109・adr119・backfill_lead_country）は接続しない版。本書の「21本」は前者、「26本」は呼び出し全体を指す。

変更するファイル（段1の実装 PR の全部）: `scripts/run_all_migrations.sh`、scripts/migration_py_entry.py（新規）、`.github/workflows/migration-test.yml`、`.github/workflows/deploy.yml`（db_migrations の path と、:51-55 の説明コメント1行だけ）、`scripts/tests/test-process-artifacts.js`（入口のパスの試験1件）、`scripts/check-process-artifacts.js`（:68-73 の MIGRATION_PATH_PATTERNS。deploy.yml の db_migrations と同じ範囲に保つと書かれているため、同じ path を足す）、`tests/sandbox/migration-run-sql-retry.sh`、`docs/adr/ADR-1037-migration-lock-timeout.md`、`docs/handoff/migration-lock-timeout/design.md`、ADR 目次。
| | 変更前 | 変更後 |
|---|---|---|
| run_py の移行のロック待ち | 無期限 | 1秒で諦める（接続ごとの server_settings で lock_timeout） |
| 付け方 | — | run_py が本物の移行を直接ではなく、新しい入口 scripts/migration_py_entry.py 経由で動かす。入口が `sqlalchemy.ext.asyncio.create_async_engine` を差し替えてから本物を `runpy.run_path(..., run_name="__main__")` で動かす。移行21本は触らない |
| 移行の接続の名前 | 空 | application_name=salesanchor_migration（ロック保持者の一覧と本番の調査で移行自身を見分けるため。審査の提案11） |
| 待ちの値の正本 | `SQL_LOCK_TIMEOUT`（既定 1s、run_sql のみ） | 同じ `SQL_LOCK_TIMEOUT` を run_py にも `-e MIGRATION_LOCK_TIMEOUT=...` で渡す。入口には既定値を書かない（環境変数が無ければ差し替えない＝手で流すときは今と同じ） |
| run_py の再試行 | 無し（即停止） | run_sql と同じ判定文字列・回数・間隔・全体上限（合計40回は run_sql と共有）。1回目と上限到達時に log_lock_holders |
| run_py の標準エラー | そのまま流れる | 一時ファイルに書き、終わってから `cat "${errlog}" >&2` で画面に出す（run_sql と同じ形。第8版で tee をやめた。§14） |
| ほかのエラー | 即停止 | 即停止（変えない） |

### 4-1. 新しい入口 scripts/migration_py_entry.py
- 引数: 本物の移行のパス（scripts/xxx.py）。sys.argv と sys.path[0] を本物を直接動かしたときと同じにしてから runpy で動かす。終了コード・例外はそのまま返す（SystemExit を握らない）。
- MIGRATION_LOCK_TIMEOUT がある時だけ、差し替えた create_async_engine が connect_args の server_settings に lock_timeout と application_name を足す（呼び出し側が渡した connect_args・server_settings は写しを作ってから足す。渡された dict をその場で書き換えない。lock_timeout は上書きし、application_name は無いときだけ足す。今の26本はどれも connect_args を渡さない）。書き方は `backend/app/database.py` :13-16 の server_settings と同じ形。
- 差し替えた回数を終了時に標準エラーへ必ず1行出す。値があるとき `migration_py_entry: lock_timeout=1s applied to N engine(s)`、値が無いとき `migration_py_entry: lock_timeout=unset applied to 0 engine(s)`。この1行は `finally` で出す（SystemExit・例外で終わる回にも出すため）。
- 入口と、`scripts/run_all_migrations.sh` に足す行（コメントを含む）に、SQL の表・列の削除や大量削除の形（DROP TABLE、ALTER TABLE … DROP、TRUNCATE、WHERE の無い DELETE など）を書かない。どちらも `scripts/check-process-artifacts.js` の移行の範囲（:68-73）に入り、.sql 以外ではコメントの中も当てられ（:633-650）、PO 本人の GO の対象になるため。`scripts/tests/test-process-artifacts.js` に「入口のパスが移行の範囲に入る」試験を1件足す。
- 入口では logging を設定しない（26本とも自分で `logging.basicConfig` を呼ぶため。例 `scripts/migrate_meta.py` :14）。行は sys.stderr.write で出す。
- sys.argv は `[本物のパス, *残りの引数]` に入れ替える（`scripts/migrate_meta_messages_message_id_to_text.py` :226-237 が argparse を使うため）。
- 出典（Python 3.12 公式）: from-import は import の時点でモジュールの属性を読む（reference/simple_stmts.html）。runpy.run_path は `__file__`・sys.argv[0]・`__name__` を設定する（library/runpy.html）。入口を `python scripts/…` で起動するので sys.path[0] は本物と同じ scripts/ になる。
- 差し替えが効く前提（実物で確認済み 2026-10-29）: run_py の呼び先26本は全部 `from sqlalchemy.ext.asyncio import create_async_engine` の形で、`sqlalchemy.ext.asyncio.engine` から直接取る書き方も同期の create_engine( も0件。この前提は §4-3 の S1 で見張る。

### 4-2. `scripts/run_all_migrations.sh`
- run_py の docker exec を `python scripts/migration_py_entry.py "${script}"` に変え、`-e MIGRATION_LOCK_TIMEOUT="${SQL_LOCK_TIMEOUT}"` を足す。今の :58 の `"$@"` は docker exec への指定（例 :261 の `-e TENANT_CODE=...`）なので `-w` の前に残す。入口の後ろへ動かさない。今の26本で入口に渡る残りの引数は0個。
- run_py の定義（今の :49-59）を、`SQL_LOCK_TIMEOUT=` の行と run_sql の間（log_lock_holders の後）へ移す。理由: 試験2本（`tests/sandbox/migration-run-sql-retry.sh` :40、`tests/sandbox/migration-read-probe.sh` :53・:232）が同じ awk で「`^SQL_LOCK_TIMEOUT=` 〜 run_sql の閉じ括弧」を本物から抜き出すので、R1 も同じ抜き出しで本物の run_py を使えるようにする。定義の行は `run_py() {` で始まり TOTAL の数え方（:47、行頭 `run_(sql|py)` に空白）に掛からない。
- 再試行の輪は run_sql と共通にする。共通部分（判定文字列の変数と、必要なら共通関数）も同じ範囲の中に置く。新しい関数名・行は TOTAL の数え方に掛からないようにする。
- run_py の標準エラーは `2>"${errlog}"` で一時ファイルに書き、docker exec が終わってから `cat "${errlog}" >&2` で出す（run_sql と同じ形）。プロセス置換・`$!`・wait は run_py の中で使わない（第8版。第7版の「プロセス置換を作った直後に `$!` を wait」は誤りで、本番で止まった。§14）。
- `scripts/run_all_migrations.sh` は set -e なので、docker exec の終了コードは `cmd || rc=$?` の形で受け、再試行の判定より前にスクリプトが終わらないようにする（run_sql :76-105 の受け方に揃える）。
- 触らない範囲: run_py の開始行の echo の文面（今の :52-53。`>>> [N/NN] python <本物のパス> ` のまま。K9 の突き合わせがこの行のファイル名に頼るため）、値4つ（:65-68）、log_lock_holders の中身、run_sql の外から見た動き、:107-171 の read-probe、:194-215 の EXIT trap、移行の登録行、migrations/ と移行21本の中身。

### 4-3. 試験
試験の置き場所は、PR で自動に走る `.github/workflows/migration-test.yml`（:41-48 の条件で、`scripts/run_all_migrations.sh` と scripts/migrate_*.py の変更で起動）と、既存の sandbox 試験2本（`tests/sandbox/migration-run-sql-retry.sh`・`tests/sandbox/migration-read-probe.sh`）に分ける。新しい試験用コンテナは作らない。

起動条件の追加:
- `.github/workflows/migration-test.yml` :41-48 の paths-filter に scripts/migration_py_entry.py を足す（ファイル名が migrate_ で始まらず今の条件に当たらないため。入口だけを直す PR でも S1・S2・P1〜P3 を走らせる）。
- `.github/workflows/deploy.yml` :56-59 の db_migrations にも足す。理由: 移行の段は scripts 配下すべて で入口の変更でも走るのに、本番反映前のバックアップ（:196）は db_migrations でしか走らない。入口は全部の Python 移行の接続を変えるので、変えた回は控えを取ってから流す。

`.github/workflows/migration-test.yml`（PR ごとに自動）。S1・S2・P1〜P3 はすべて migration-test-run ジョブ（:964 の段があるジョブ、DATABASE_URL あり）に置く。migration-full-dryrun（:1112）には置かない:
- S1 付け忘れ・差し替え漏れの静的点検: `^run_py[[:space:]]` の呼び先全部について、(a) `sqlalchemy.ext.asyncio.engine` の出現が0件、(b) create_async_engine を取り込む行がすべて `from sqlalchemy.ext.asyncio import` の形（1行でも別の形があれば赤。「正しい形が1行ある」では判定しない）、(c) 同期の `create_engine(` が0件。`asyncpg.connect(`・psycopg の直接使用も無いこと（差し替えを通らない接続のため）。違えば赤。`モジュール.create_async_engine(` の書き方は差し替えが効くので止めない。手本は :1666- の静的点検。新しい移行が別の書き方で足されたらここで止まる。
- S2 run_py が入口を通ること: run_py の定義の中に migration_py_entry.py と `MIGRATION_LOCK_TIMEOUT` があること（grep）。
- P1 待たせる時間と例外の文字列: 既存の「Sprint 1 マイグレーションを適用」のうち :964 側（同名の段が :1649 の別ジョブにもある）の後に段を足す。別の psql が `BEGIN; LOCK TABLE public.suppliers IN ACCESS SHARE MODE;` のまま6秒保持する。保持役がロックを取ったことを pg_locks で確かめてから（sleep で待たない）、`PYTHONPATH=backend MIGRATION_LOCK_TIMEOUT=1s python scripts/migration_py_entry.py scripts/migrate_inventory_sprint1.py` を流す（:964 の段と同じ PYTHONPATH。P2・P3 も同じ）。その間0.5秒ごとに `SELECT 1 FROM public.suppliers LIMIT 1` の時間を測る。判定: 移行は rc≠0、標準エラーに "canceling statement due to lock timeout" がある（P4 を兼ねる）、読み取りの最大 ≤ 1500ms、移行が失敗するまで 3秒未満（測り始めは保持役のロックを pg_locks で確かめた後、入口を起動する直前）。前提の表・テナントはこの段より前の段が作ったものを使う（新しく作らない）。
- P2 環境変数が無いときは今と同じ: 保持なしで P1 と同じ scripts/migrate_inventory_sprint1.py を入口経由に流して rc 0、差し替え回数の行が「lock_timeout=unset applied to 0」。MIGRATION_LOCK_TIMEOUT が空の文字列のときも「無し」と同じに扱う（入口でそう作る）。
- P3 差し替えが効く: 保持なしで同じ移行を `MIGRATION_LOCK_TIMEOUT=1s` で流して rc 0、差し替え回数の行が「applied to 1」。

sandbox 試験（手で起動。ADR-1037 の試験を広げる）:
- `tests/sandbox/migration-run-sql-retry.sh` の既存 T1〜T8 がそのまま PASS（run_sql の動きを変えていない証拠）。
- `tests/sandbox/migration-read-probe.sh` の既存 T1〜T9 がそのまま PASS（抜き出し範囲に run_py を移しても壊れない証拠）。
- 以下 R1〜R4 は `tests/sandbox/migration-run-sql-retry.sh` に足す。この試験は :5 で `set -uo pipefail` なので、R1〜R4 の前に BACKEND・DATABASE_URL・ADMIN_DATABASE_URL に仮の値を入れる（未定義だと run_py の参照で止まる）。偽 docker は今のこの試験には無い（T1〜T8 は :29 の本物の postgres:16 で動く）。R1〜R4 用に docker 関数を新しく作り、引数に python を含む呼び出しだけを偽の動きにし、含まない呼び出し（dsql・log_lock_holders）は `command docker "$@"` で本物へ渡す。R1〜R4 が終わったら関数を消し、T1〜T8 に影響させない。
- R1 run_py の流し直し: 本物の run_py と再試行部分を抜き出し、docker exec の代わりに「1回目だけ標準エラーへ "canceling statement due to lock timeout" を出して rc 1、2回目は rc 0」の偽コマンドで動かす → rc 0、"lock conflict; retry" 1回、実行中の行が標準エラーに出ている。
- R2 上限: 毎回同じ失敗を返す偽コマンドを `SQL_RETRY_MAX_ATTEMPTS=3 SQL_RETRY_SLEEP_SEC=1` で → rc≠0、"retry limit reached"、所要10秒未満。
- R3 ほかのエラーは即停止: 別の文言で rc 1 → retry 0回。
- R4 全体上限の共有: run_sql で再試行を1回使った後、`SQL_RETRY_BUDGET=2` で run_py が2回目の再試行をしない。
- R5 裏の読み取り監視と一緒に動かしても戻る（第8版で追加。本番で止まった形を再現する）: `tests/sandbox/migration-read-probe.sh` と同じ抜き出しで read_probe_start を取り出し、裏の輪を動かしたまま、本物の run_py を偽コマンド（rc 0 と、1回目 lock timeout→2回目 rc 0 の2通り）で呼ぶ。全体を `timeout 30` で包み、30秒以内に戻って rc 0・"lock conflict; retry" の回数が期待どおりであること。終わったら裏の輪を止め、残っていないことを確かめる（輪は `kill -0` で親の死を見て2秒以内に抜ける。`scripts/run_all_migrations.sh` :127）。第7版の形（tee と `$!` の wait）に戻すとこの試験が rc=124（timeout）で赤になることを、実装 PR で1度示し結果を貼る。
  - R5 の偽コマンドは、PATH の先頭に置く外部の実行ファイル（例 `$OUT_DIR/bin/docker`）にする。シェル関数の docker() は R5 では使わない。理由: 関数だと親の bash がリダイレクトを行い `$!` がプロセス置換を指すので、第7版の形でも wait が戻り、試験が緑になる（§14-1）。偽物にするのは BACKEND 宛ての呼び出しだけで、それ以外（読み取り監視・log_lock_holders）は本物の docker の絶対パスへ渡す（`docker` と書くと自分自身を呼び続ける）。再試行の間隔は `SQL_RETRY_SLEEP_SEC=1` に下げる。make_parent（`tests/sandbox/migration-read-probe.sh` :68-82）と同じく別の bash で流し、その bash を `timeout 30` で包む。
  - R5 は `tests/sandbox/migration-read-probe.sh` に置く（監視の抜き出し :43、`SQL_LOCK_TIMEOUT=` 〜 run_sql の抜き出し :53、make_parent が揃っているため）。偽 docker は別のプロセスなので、シェル変数は見えない。偽物にする相手は固定のコンテナ名（例 `sb-fake-backend`）を BACKEND に入れて引数で見分ける。動きの切り替えと回数は export した環境変数かファイルで渡す。本物の docker の絶対パスは PATH を変える前に `command -v docker` で取っておく。make_parent は BACKEND・DATABASE_URL を設定しないので、R5 の側で足す。
  - 赤の実演は、本番の bash 5.2 と同じ 5.x（sandbox-test の ubuntu-latest。試験が `bash=` を出す）で `$!` の動きを確かめる役も兼ねる（§14-1 の未確認を埋める）。実演が rc=124 にならなかったら、試験を直して赤にしようとせず止まり、設計担当に戻す。
- R1〜R4 の偽コマンドの差し込み方（関数の上書きか変数か）は実装役が決めてよい。本物の run_py の文面は写さず抜き出す。

PR ごとの静的点検にも1つ足す（第8版）:
- S3 裏の作業を待つ書き方が無いこと（S2 と同じ段）: 見る範囲は R1〜R5 と同じ抜き出しの範囲全部（`^SQL_LOCK_TIMEOUT=` 〜 run_sql の閉じ括弧。共通関数に出した場合も含めるため）。コメント行（`^[[:space:]]*#`）を除いてから、`grep -F '$!'`・`grep -F '>('`・`grep -wE 'wait'` のどれかが当たれば赤。今の main の同じ範囲（:65-105）はどれも0件。R5 は手で起動する sandbox 試験なので、同じ誤りが入ったときに PR の CI で止める役をこちらが持つ。

### 4-4. 流し直しの安全性（根拠）
- run_py は失敗するとスクリプト全体を最初から流し直す。Python の移行は1ファイル（またはテナント1つ）ごとに `engine.begin()` の1取引で、全部入るか全部戻る。途中失敗の後に残るのは「一部の取引が適用済み」の形だけ。
- 21本は毎回の本番反映で、適用済みの本番 DB に全部流れて成功している（ADR-1005。直近3回の本番反映で26本とも成功、2026-10-29 の記録）。「適用済みの上にもう一度流す」は毎日確かめられている。
- 009・011 は "already exists"・"duplicate" を含む例外を握りつぶすが、ロック待ちの文言は含まないのでそのまま失敗し、流し直しの判定に乗る。将来この2語を含む文が足されて黙って飛ぶ場合も、次の文が "current transaction is aborted" で落ち、判定から外れて即停止になる（安全側）。

### 4-5. 文書
- `docs/adr/ADR-1037-migration-lock-timeout.md` :40 の対象外「run_py（Python の移行）の接続」を消し、「Python の移行にも入口経由で付けた（本書）」を追記。`node scripts/generate-adr-index.js` で目次を作り直す。
- `docs/handoff/migration-lock-timeout/design.md` :117（案C、20本と記載）・:138（便3 未承認）に「2026-10-29 PO「1」で本書へ。対象は21本、入口方式」とつなぐ。

## 5. 外部・過去事例
- ADR-1037（2026-10-21）: run_sql に1秒と再試行を付け、試験で読み取りの最大待ちが1.5秒以内に収まった（recon §4 で 1085ms）。同じ形を run_py に広げる。
- 外部事例は ADR-1037 の設計（GitLab の移行指針、PostgreSQL 16 公式）を引き継ぐ。新しい技術を選ばないので、新しい外部事例は使わない。
- asyncpg 公式（magicstack.github.io/asyncpg/current/api/、2026-10-29 閲覧）: server_settings は接続ごとのサーバー設定。PGOPTIONS は読む環境変数の一覧に無い。Context7 は月の上限で使えなかった。
- Python 標準の runpy.run_path（docs.python.org/3.12/library/runpy.html）: run_name="__main__" で、スクリプトを直接動かしたときと同じく `if __name__ == "__main__":` の中が動く。実装時に公式で再確認する。

## 6. 受け入れ基準
| 基準 | 検証方法 |
|------|---------|
| K1 Python の移行がロックを待つ間、ほかの読み取りが待たされるのは1.5秒以内 | migration-test の P1 PASS（PR の CI） |
| K2 ロック待ちの失敗が流し直しの判定文字列で拾える | P1 の文字列判定 PASS |
| K3 値を渡さなければ今と同じ／渡せば全エンジンに付く | P2・P3 PASS |
| K4 付け忘れ・差し替え漏れが PR で止まる | S1・S2 PASS（加えて、わざと `from sqlalchemy.ext.asyncio.engine import` の行を足すと赤になることを実装 PR で1度示す） |
| K5 run_py の流し直し・上限・即停止・全体上限の共有 | sandbox-test の R1〜R4 PASS |
| K5b 裏の読み取り監視が動いていても run_py が時間内に戻る（第8版） | sandbox-test の R5 PASS と、第7版の形で R5 が赤になる実演（実装 PR に結果を貼る）。CI の S3 PASS |
| K6 run_sql と読み取り監視の動きが変わらない | sandbox-test の `tests/sandbox/migration-run-sql-retry.sh` T1〜T8 と `tests/sandbox/migration-read-probe.sh` T1〜T9 PASS |
| K6b 入口だけを変える PR でも見張りが走り、本番反映で控えが取られる | paths-filter・db_migrations・check-process-artifacts.js の MIGRATION_PATH_PATTERNS の3か所に入口があること（実装 PR の差分で確認） |
| K7 今ある移行が全部これまでどおり流れる | CI の必須チェック緑。本番反映の移行の段が success |
| K8 本番: この変更を含む本番反映から、移行のある3回で、移行の段が「成功」か「打ち切り10分より前に retry limit reached で止まった」のどちらか。10分の打ち切りで切れた回は0 | 各本番反映のログ（移行の段の成否・所要時間、"lock conflict; retry"・"retry limit reached" の回数、差し替え回数の行） |
| K9a 本番（悪くなっていない）: 同じ3回それぞれで、`>>> [final] read probe:` 行が n≥1・invalid=0・slow=0・error=0（ADR-1037 の K7 と同じ基準。slow は2秒超＝:112 の READ_PROBE_SLOW_MS）。1500ms を閾値にしない理由: 1回の計測は docker exec の起動＋psql の接続＋14表の SELECT の合計で、待ちの無い回でも本番で max=797ms（ADR-1037:70）。1秒の待ちが重なると約1.8秒になり、正しく動いても超える | 本番反映ログの read probe の行（`scripts/run_all_migrations.sh` :165） |
| K9b 本番（効き目）: run_py の "lock conflict; retry" が出た最初の本番反映で、K9a と同じ条件を満たす。3回の中に無ければ「段1の該当なし」と記録し、合格に数えない（効き目の証明は P1 が担う）。次に起きた回で判定して追記する | 同上と、run_py の再試行の行 |
| K9 で slow・error が出たときの判定 | ・分け方: `>>> [final] read probe slow: <時刻> <ms>` の行の時刻を、同じ本番反映ログの `[N/NN] python …`・`[N/NN] psql < …` の行の時刻（Actions のログの時刻）と突き合わせ、どの移行の間かを決める（`docs/handoff/migration-lock-timeout/design.md` :365 と同じ方式）。候補は、開始行から次の開始行までの区間が「slow の時刻 −1秒 〜 slow の時刻＋その ms＋1秒」に重なる移行の全部（slow の時刻は秒単位の切り捨てで、サーバーの時計と Actions の時計のずれは未確認のため幅を持たせる）。候補に run_py が1本でもあれば run_py の間として扱い、候補のファイル名は全部記録する。候補が8ファイルだけなら8ファイルの間、それ以外はその他。error は時刻が出ないので「その他」に入れる。・run_py の移行の間（§9 の「鍵を持ったまま別の表を待つ」形を含む）: 不合格。段1は戻さない（戻すと無期限に待つ形に戻る）。ファイル名を記録し、段5で直す対象に足してから段2へ進む。・`SET LOCAL lock_timeout = '5s'` の8ファイル（ADR-1037:39、段1の範囲外）の間: この K9 では対象外。記録し、その8ファイルを直す別の段の根拠に使う（ADR-1037 の K7 では従来どおり不合格に数える。`docs/handoff/migration-lock-timeout/design.md` :366）。・その他（突き合わせられない・error）: 不合格。段2へ進まず原因を調べ PO に報告する。・K8 が不合格（10分の打ち切りで切れた回がある）なら段1を戻す。 | read probe slow の行（:157-161）と各移行の開始行 |
| K9 の除外 | 使わない（どの回も K9 で判定する）。理由: lock holders の locks 列は表名だけでスキーマ名が無く（`scripts/run_all_migrations.sh` :74）、計測する14表の一部はテナント側にも同じ名前の表があるので、ログだけでは「移行と関係なく読み取りを止める鍵」を見分けられない。長く握る接続がいた回も K9 で判定する（今回の事故の形）。・明細の読み方: 見出しは :73 の `lock holders (xact > 1s):` の行。明細は次の行から `>>> [S/T]   ` で始まり、` \| ` 区切りで pid・usename・application_name・state・wait・xact_sec・cmd・locks の順。列名の行は無い。locks は `表名:ロックの種類` の並び | lock holders の見出しと明細（:73-74） |

## 7. KPI
- 本番反映1回あたり「移行がアプリを待たせた最大時間」。基準値: 2026-10-29 に約113分。目標: 移行の1回の待ちは1秒（CI の P1 で1文の待ち ≤ 1500ms を確かめる）。本番では計測の作り上、読み取り監視の slow（2秒超）=0・error=0 で見る（K9a・K9b）。§9 の「取引の間は鍵を持ち続ける」分は別に記録する。
- 「10分の打ち切りで切れてサーバーに作業が残った本番反映」。基準値: 2026-10-29 に7回。目標0回。長く握る接続がいて上限で止まった失敗は、打ち切りより前に止まったものとして別に数える。

## 8. 選ばなかった案と理由
- 21本それぞれに connect_args を書き足す（第1版）: 21ファイルが変わり、`.github/workflows/migration-test.yml` :999, :1035-1058 が変わった移行21本を名前順に2周流す。名前順は本番の順と違い、通るかは未確認（審査の指摘4）。新しい移行の付け忘れも別の点検が要る。入口方式は21本を触らず、新しい移行にも自動で付く。代わりに「差し替え」が読む人に見えにくいので、入口の冒頭と run_py の定義にコメントで理由を書き、差し替え回数をログに出す。
- jarvis ロール全体に lock_timeout を掛ける: jarvis は管理画面の admin_engine（`backend/app/database.py` :66-84）、データ削除の定期作業（`backend/app/tasks/data_deletion.py` :44-59）、バックアップ、監視、本番反映中の psql にも使われる。それらの待ち方まで変わる。ADR-1037 で却下済み。
- 接続先 URL に lock_timeout を付ける: SQLAlchemy が asyncpg に渡すときの扱いを確かめられなかった（未確認）。確かめられない仕様に頼らない。
- 056 だけ書き換える（段5を先に）: 同じ書き方が migrations/ に62ファイルあり、1本直しても別の移行で同じことが起きる。

## 9. 弊害・トレードオフ
- 時間の上限（実測 2026-10-29、直近の本番反映3回 run 40847667921・40839190579・40810424800）: run_py 1本の所要は最大1.03秒・平均0.87秒。移行の段全体は、再試行の無い回で最大82.3秒（run 40810424800 の146.8秒には run_sql の再試行15回が含まれ、1回あたり約4.2秒だった）。再試行1回の最悪は、run_sql 側（5秒待ちの8ファイル: 待ち5＋間隔3＋流し直し約1.4秒）≒9.4秒、run_py 側（流し直し約1.03＋待ち1＋間隔3）≒5.1秒。全体上限40回を共有するので、最悪は 40×9.4＋82.3 ≒ 458秒。10分（600秒）の打ち切りに約140秒の余裕で収まる。
- アプリが長く握っていると、移行が上限まで試して本番反映が止まる（今回と同じ113分の保持なら、約3〜5分で「retry limit reached」で止まる）。止まったときは古い版のまま動き続ける。今の run_sql と同じ扱い。
- 取引の間は鍵を持ち続ける: Python の移行は1ファイルを1取引で流すので、先に取った鍵をそのファイルの最後まで持つ。lock_timeout は「取りに行く待ち」だけを1秒に抑える。「表 A を握ったまま表 B を1秒待って失敗」が回数分くり返され、読み取りから見ると1回あたり「1秒＋そこまでの実行時間」止まり得る。P1 は空に近い DB での1本しか測れないので、本番の K9 で見る。
- 本番の読み取り監視は取り逃がしがある: 計測は2秒の休み＋計測時間の周期（`scripts/run_all_migrations.sh` :112・:142）なので、1秒の待ちと重ならない回がある（ADR-1037:68-70 でも run_sql の衝突1回で max=797ms）。K9 の合格は「2秒を超えて待たせた回が見つからなかった」という上限の確認で、待たせていない証明ではない。
- 差し替えは暗黙: 入口が create_async_engine を差し替えることは、移行を読むだけでは見えない。入口のコメント・run_py のコメント・差し替え回数のログで補う。
- Python の移行のログが後からまとめて出る（第8版）: 影響は2つ。(1) 標準出力はその場で出るので、標準出力と標準エラーの並びが入れ替わる（遅れは最大で試行1回分）。(2) 移行がロック以外の理由で長く止まり10分の打ち切りで切られた回は、その移行の標準エラー（移行の logging の出力先）が Actions のログに残らない。どちらも run_sql（main :84-85）と同じ性質で、今まで困っていない。本番反映の時刻の突き合わせ（K9）は開始行（`>>> [N/NN] python …`、docker exec の前に出る）に頼るので変わらない。

## 10. 戻し方
この変更の PR を revert して main にマージする。次の本番反映から今の形（Python の移行は無期限待ち・再試行なし）に戻る。DB の中身・移行21本は変えないので、DB 側の戻しは無い。

## 11. 計画表
| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 設計審査（§12） | Opus（Architect） |
| 2 | §4 の実装、sandbox-test の実行、CI | Sonnet |
| 3 | 差分と試験ログの審査 | Opus（reviewer、新しく起動） |
| 4 | PR・GO 記録（委任 GO。本番 scripts と deploy.yml を含み ADR-135・136 の GO 対象。ADR-1003 の例外7種には当たらない。DROP を含む移行の追加・変更は無い）・マージ | Opus |
| 5 | 本番反映後の K8・K9 測定（3回分） | Sonnet が集計、Opus が判定 |
| 6 | 段2の詳細設計へ | Opus |

## 12. 設計審査
- 第1版（21本に書き足す案）: REVISE（2026-10-29、Architect 新規起動）。指摘: 時間計算に run_py の性質が無い／試験の前提が無い／付け忘れの見張りが PR で走らない／名前順2周の影響／標準エラーの扱い／共通部分の置き場所／取引中の鍵保持／KPI と弊害の食い違い／ADR の対象外の行。
- 第2版: 入口方式に変え、run_py 1本の所要を実測し、試験を PR の CI と sandbox に分けた。REVISE（2026-10-29、Architect 新規起動。方式・時間・試験の置き場所は合格）。指摘: 入口が起動条件（paths-filter・db_migrations）から漏れる／抜き出し範囲に依存する試験がもう1本ある／run_py が抜き出し範囲の外／時間計算の元の数字に再試行が含まれる／入口の書き方3点（finally・logging・argv）／S1 に asyncpg.connect・psycopg／P1 は pg_locks で確認。
- 第3版: 上の指摘を §4-1・§4-2・§4-3・§6・§9・§13 に反映。REVISE（2026-10-29、Architect 新規起動。行番号・抜き出し・時間計算・ADR 整合は合格）。指摘: sandbox 試験の set -u と偽 docker の見分け／check-process-artifacts.js の範囲のずれ／set -e で再試行前に止まる／変更ファイル一覧に deploy.yml が無い／版の表記／21本と26本の定義／bash の版は確認できる／S1・S2 の置くジョブ／server_settings の扱い／P1 の PYTHONPATH。
- 第4版: 上の指摘を §3・§4 冒頭・§4-1・§4-2・§4-3・§6・§11・§13 に反映。REVISE（2026-10-29、Architect 新規起動。第3版の指摘10件中9件は合格）。指摘: 偽 docker は実物に無い／S1 の書き方では K4 の実演が通ってしまう／K9 が1.5秒を測れず除外条件もログで判定できない／値が無いときの1行の書式／run_py の "$@" の位置／入口のコメントの語が表削除の検出に掛かる／paths-filter の行番号／deploy.yml の説明コメント／P1 の測り始め。
- 第5版: 上の指摘を §4 冒頭・§4-1・§4-2・§4-3・§6・§8 に反映。REVISE（2026-10-29、Architect 新規起動。第4版の指摘のうち7件合格、方式・時間・行番号は合格）。指摘: K9 の1500ms は計測の作りで正しくても超える／run_sql の5秒の8ファイルと run_py の衝突なしの回の扱い／除外の条件が今回の事故そのものを外す／行番号1か所／表削除の語の禁止の範囲／明細の列の順と n・invalid／P2・P3 の対象。
- 第6版: 上の指摘を §4-1・§4-3・§6（K9a・K9b・記録の分け方）・§7・§9 に反映。REVISE（2026-10-29、Architect 新規起動。直すのは K9 の判定の文面だけ）。指摘: slow が出たときの分け方と次の一手が無い／8ファイルの見分けを lock conflict 行でしていた／ADR-1037 と run_all_migrations.sh の行番号2か所／finally の文の位置／除外が表名だけ。
- 第7版（本書）: 上の指摘を §4-1・§6（K9 の判定・除外）・§9 に反映。APPROVE（2026-10-29、Architect 新規起動。K9 の行の形・Actions の時刻・lock holders の明細を本番反映 run 40810424800 の生ログで照合）。条件として付いた4点（時刻の突き合わせの区間と候補が複数のときの決め方／ADR-1037 の K7 との数え方の違い／除外は使わない／run_py の開始行の echo を変えない）は、同じ日に §4-2・§6 へ追記済み。K9 の文面だけで、実装・CI には影響しない。

- 第8版（本書）: §14 の本番の失敗を受けて §4 の表・§4-2・§4-3（R5・S3）・§6（K5b）・§9・§14 を直した。REVISE（2026-10-29、Architect 新規起動。直し方そのものは合格）。指摘: R5 の偽コマンドが関数だと第7版の形でも緑になる／§4-2 に wait の文が残る／S3 の範囲・コメント・grep の書き方／ログが後から出る影響の書き過ぎ。
- 第8.1版: 上の指摘を §4-2・§4-3（R5・S3）・§9・§14-1 に反映。APPROVE（2026-10-29、Architect 新規起動。S3 を今の main〔0件〕と第7版〔3件とも当たる〕に実際に流して確認。R5 は sandbox の postgres と ubuntu-latest で作れ、監視が失敗しても判定は成り立つ）。条件として付いた文面3点（§14-2 の S3 の書き方／R5 の置き場所と偽 docker への値の渡し方・§13／赤にならなかったときは止まる）は、同じ日に §4-3・§13・§14-2 へ追記済み。

## 13. 継続（維持の仕組み）
- 付け忘れ・差し替え漏れ: 守り手: `.github/workflows/migration-test.yml`（S1・S2。PR で `scripts/run_all_migrations.sh`・scripts/migrate_*.py・入口が変わると走る）。
- 抜き出し範囲（`^SQL_LOCK_TIMEOUT=` 〜 run_sql の閉じ括弧）: 守り手: `tests/sandbox/migration-run-sql-retry.sh` と `tests/sandbox/migration-read-probe.sh`（どちらも抜き出しに失敗すると止まる）。
- 値の正本: `scripts/run_all_migrations.sh` の SQL_LOCK_TIMEOUT だけ。
- 移行の範囲（db_migrations と MIGRATION_PATH_PATTERNS）を揃えること: 人手で守る（`scripts/check-process-artifacts.js` :68-73 のコメントが両者を揃えると定めている）。
- run_sql と run_py の再試行の動き: 守り手: `tests/sandbox/migration-run-sql-retry.sh`（手で起動。run_all_migrations.sh の再試行部分を変える PR で実行し、結果を PR に貼る）。読み取り監視と一緒に動かしたときに戻ること（R5）: 守り手: `tests/sandbox/migration-read-probe.sh`（同じく手で起動）と、PR ごとの S3。

## 14. 第8版の改訂（第7版の実装が本番で止まった）
### 14-1. 事実（2026-10-29）
- 第7版の実装 PR #4861（merge 46f2009b）を含む本番反映 run 40867936152 が、移行の段で10分の打ち切り（Run Command Timeout、11:59:50Z）になった。
- 本番サーバーで読み取りだけで確かめた形: run_all_migrations.sh は run_py の wait の中で止まり、子は読み取り監視の裏の輪（read_probe_start が起動する `sleep 2` の繰り返し）だけ。python・docker exec は残っていなかった。本番の bash は 5.2.21。
- 原因: 第7版の run_py は `docker exec … 2> >(tee "${errlog}" >&2) || rc=$?` の後に `$!` を取って wait していた。この位置の `$!` はプロセス置換ではなく、直前に裏で起動した読み取り監視の輪の番号を指し、その輪は親が生きている限り終わらないので、wait が戻らなかった。docker は外部コマンドなので、bash は fork した子の中でリダイレクト（プロセス置換）を作り、親の `$!` は変わらない（審査役が手元の bash 3.2 で実測: 外部コマンドの後は裏の sleep の番号のまま、シェル関数の後はプロセス置換の番号。5.2 での同じ実測は未確認だが、本番の止まり方と合う）。§4-2 の「プロセス置換を作った直後に `$!` を wait」という前提が誤りだった。
- CI と sandbox の試験は、この組み合わせを捕まえられなかった。CI は裏の作業が無く `$!` が空で、`wait ""` が失敗して `|| true` で抜けた。第7版の R1〜R4 は偽コマンドがシェル関数の docker() だったので、`$!` がプロセス置換を指して正しく戻った（`git show 46f2009b:tests/sandbox/migration-run-sql-retry.sh` :241-263）。
- 戻し: PR #4862（Revert、merge fd85b946）。その本番反映 run 40871954675 では、古い形（ロック待ちに上限なし）の [39/363] scripts/migrate_inventory_sprint1.py が再びロックを待ち、仕入元の表の読み取りが 21:21:05〜21:39:18 JST（約18分）止まった。21:39 ごろに自然に戻った理由と、ロックを握っていた接続の正体は未確認。残った作業は PO が本番サーバーで終わらせた（ps で run_all_migrations と読み取り監視が0件を確認）。
- 結論: main は今、事故の前と同じ「無期限に待つ」形。段1を早く入れ直す必要がある。

### 14-2. 変更
- run_py の標準エラーは run_sql（`scripts/run_all_migrations.sh` :84-85 の `2>"${errlog}" || rc=$?` と `cat "${errlog}" >&2`）と同じ形にする。プロセス置換・`$!`・wait を使わない（§4-2）。
- 試験に R5（読み取り監視を動かしたまま run_py が戻る）と S3（抜き出し範囲全体のコメント以外に `$!`・`>(`・`wait` が無い）を足す（§4-3、K5b）。
- ほかの §4〜§13 は第7版のまま（入口方式・値・再試行・K8/K9 は変えない）。実装は #4861 の差分を入れ直し、run_py の標準エラーの部分と試験だけを変える。

### 14-3. 選ばなかった案
- `$!` を docker exec より前に取り直す・プロセス置換の番号を別の方法で取る: bash の版や書き方で `$!` の指す先が変わる形に再び頼ることになる。標準エラーを途中で見られる利点は、1本約1秒の移行では小さい。
- tee をやめず wait もしない: tee が一時ファイルを書き終える前に判定の grep が走り、lock timeout の文字列を取り逃がす恐れがある。

## 15. 段3 詳細設計 — 控え（`scripts/backup.sh`）の pg_dump にロック待ちの上限を付ける（第2.1版）
状態: 設計審査済み（第2版 条件付き APPROVE、条件 C1〜C5 は第2.1版で反映）。実装・本番反映済み（PR #4867、2026-10-29）。本番測定（2026-10-30）: K3-6 合格（03:01:57 の控えが Completed 547M）。K3-5 は翌朝3時の後の分だけ確認済み（書き途中のファイル0本。記録 /tmp/CC報告ファイル/deploy-db-stall/impl-stage3/k3-cron-0300.txt。pg_dump の残りの記録は無い）。K3-4 の置き換え（PO 2026-10-30「1」）: 控えの段が動く本番反映が来ないため、本番反映の段と同じ命令（`cd /home/ubuntu/salesanchor && bash scripts/backup.sh`、prod1 の backup.sh は origin/main と sha256 が一致。記録 sha256-main.txt・sha256-prod1-and-ps.txt）を PO が手で3回続けて流した。結果は 11:13:18・11:15:16・11:17:14 JST に rc=0、123秒・117秒・117秒（300秒以内）、各回 Completed 551M。3回目の21秒後（11:17:35）の ps の一覧に pg_dump の行は無く、書き途中0本（pgdump-check.txt。K3-5 の3回の後の分）。11:25:56 にも ps で pg_dump の行0（sha256-prod1-and-ps.txt）。run3.sh の最後の数え方（after.txt の pg_dump=2）は、命令の文字列そのものに当たる数え方の誤りで、根拠に使わない。記録 /tmp/CC報告ファイル/deploy-db-stall/k3-4-manual/。弊害: 件数の保持で 10/29 の控え3本（161149・162840・170250）が消えた。保持は更新時刻の順で、名前の順ではない。170250 は出どころ未確認の控えで、一覧の記録（k3-cron-0300.txt）だけが残る。置き換えの理由: PR #4867 の後、控えの段は本番反映2回とも skipped だった（控えの段は db_migrations が真のときだけ動く）。段1の本番測定は3/3回で K8・K9a 合格（run 40887849089・40900915287・40917875119）。
審査の記録: 第1版 REVISE（2026-10-29、Architect 新規起動。方向・段2より先にする判断・影響範囲は合格）。指摘: trap は前面のコマンドが終わるまで動かない／ロック待ちの上限は LOCK 文ごとで表をまとめる作り／B1 の判定文字列／K3-3 を B2・B3 で証明しきれない／B1 はコンテナの中で／古い書き途中が残り続ける／取り残し6本と失敗5回の不一致／§3 の「同上」と冒頭の状態／警報の鳴り方。第2版で §15-1・§15-3（1・2・3・6）・§15-4・§15-5・§15-6・§15-7・§3・冒頭に反映した。第2版 条件付き APPROVE（2026-10-29、Architect 新規起動。9件とも直っていると実物で照合。trap と終了コードを手元の bash で実測）。条件: C1 B1b の接続 B に BEGIN／C2 B1・B4 の入れ物の作り方／C3 K3-1b の言い方／C4 B3 の重複・番号の飛び・守り手・CI の置き場所／C5 trap の置く位置と消す範囲・中断の試験の印と setsid。任意の2点（umask 077・本物の backup.sh を握られた表で流す B4b）も採用。第2.1版で §15-3（3・5）・§15-4・§15-5・§15-8 に反映した。

### 15-1. 段2より先にする理由（事実）
- 2026-10-29 の失敗した本番反映のうち、移行の段で切れたのは最初の1回（run 40830552636）だけ。続く run 40832263125・40833808660・40835601678・40835788220・40838070799 は、どれも「Pre-deploy DB backup」の段がちょうど10分で打ち切られた（例 06:56:58Z→07:06:59Z。gh run view の段の時刻）。
- 打ち切られた控えはサーバーで動き続けた。本番の控えの記録（`/home/ubuntu/backups/postgres/backup.log`、2026-10-29 読み取りのみ）では、開始時刻の名前が 15:56:59〜17:02:50 JST の6本が、17:41:50〜17:41:52 JST に同時に「Backup completed」になった。ロックが解けた 08:35:38Z（17:35 JST）の約6分後。
- その直後、件数の保持（`scripts/backup.sh` :44-54、新しい10本だけ残す）が古い控え6本を消した。いま残る10本はすべて 2026-10-29 の作で、10/26〜10/29 の毎朝3時の控えはこの保存先に無い（同じ読み取り）。
- pg_dump は開始時に全表へ共有ロックを取りに行く。待ちの上限は既定で無い（PostgreSQL 16 文書 pg_dump の --lock-wait-timeout）。移行の排他ロックが待ち行列にいる間、pg_dump の共有ロックはその後ろに並ぶ。
- 段3は1ファイルの小さな変更で、効き目（打ち切りより前に自分で止まる・途中のファイルを残さない）を CI の実物の PostgreSQL 16 で確かめられる。段2は取り残しの形（プロセスの親子関係）の記録が無く、根拠を取る段取りから要る。よって段3を先にする。
- 6本のうち5本は、名前の時刻が失敗した5回の控えの段の開始と1対1で合う（155659↔run 40832263125 06:56:58Z、161149↔40833808660、162840↔40835601678、163941↔40835788220、165148↔40838070799）。残る170250（08:02:50Z 開始）は出どころを特定できていない。その時刻に控えの段を動かしていた本番反映は無い（40838070799 の段は 08:01:48Z に終了、次の 40839190579 の段は 08:55:59Z 開始・成功）。ubuntu の crontab で backup.sh を呼ぶのは毎日3時の1行だけ。root の crontab は sudo の合言葉が要り読めていない。40838070799 の段のログの中身も未確認。
- 推測（未確認）: 取り残しの6本がロック待ちだったこと自体は ps で見ていない。時刻（ロックが解けて約6分後に同時に完了。ふだんの控え1本の所要は約2分）と仕組みからの推測。

### 15-2. ふだんの所要時間（実測。`backup.log` の名前の時刻＝開始、Completed 行＝終了）
| 開始（JST） | 終了 | 所要 |
|---|---|---|
| 10/29 03:00:01（毎朝3時） | 03:01:54 | 113秒 |
| 10/29 17:56:01 | 17:58:01 | 120秒 |
| 10/29 20:46:52 | 20:48:49 | 117秒 |
| 10/29 21:17:32 | 21:19:28 | 116秒 |
| 10/29 22:15:37 | 22:17:33 | 116秒 |
| 10/29 23:04:57 | 23:06:52 | 115秒 |
本番反映の段で見ても run 40867936152 は 11:46:50Z→11:48:49Z（119秒）。控えの大きさは 546M（10/29 23:06）で、10/26 の 496M から1日約13M ずつ増えている。

### 15-3. 変更前 → 変更後（変更するのは `scripts/backup.sh` と試験・CI だけ）
1. pg_dump に `--lock-wait-timeout=120000`（ミリ秒）を付ける。値は backup.sh 冒頭の定数 PG_DUMP_LOCK_WAIT_MS=120000 の1か所だけに置く（環境変数で変えられるようにしない。正本を1つにする）。
   - 120秒の理由: 本番反映の段の打ち切りは600秒。待ち120秒＋ふだんの所要約120秒＝240秒で、増え方（1日約13M、約2.4%/週）を見込んでも打ち切りまで300秒以上の余裕がある。段1の後、移行1回の待ちは1秒・全体の最悪は約458秒（§9）だが、その間ずっと排他ロックを持つわけではないので、120秒あれば移行1本の取り合いは抜けられる。毎朝3時の控えは120秒より長いロックで失敗する（下の弊害）。
   - 上限の正体（PG16 原典 src/bin/pg_dump/pg_dump.c REL_16_STABLE :6705-6718・:6871-6874）: pg_dump は表のロックの前に `SET statement_timeout = <値>` を置き、終わったら0に戻す。表のロックは `LOCK TABLE a, b, … IN ACCESS SHARE MODE` を約100KB ごとに1文にまとめる（:6840-6868。対象は普通の表とパーティション親表、:6835-6837）。よって待ちの最悪は「文の数 × 120秒」。本番の文の数は下の6で測った。
   - 上限が効くのは開始時の表のロックの文だけ。取った後の吐き出しが長くなる場合や、定義を読む途中で別の排他ロックを待つ場合は止まらない。それは段2（本番反映の段の時間切れでサーバー側も止める）で扱う。
2. 書き途中のファイルを残さない: pg_dump と gzip の出力は `${BACKUP_FILE}.partial` に書き、成功したら mv で `${BACKUP_FILE}` にする。`.partial` は `salesanchor_db_*.sql.gz` の形に当たらないので、件数の保持（:45）・本番反映の確認（`.github/workflows/deploy.yml` :212）・S3 への写し（`scripts/backup_to_s3.sh` :91）・復元の一覧（`scripts/restore.sh` :22）のどれにも拾われない。
   - 強制終了（kill -9・メモリ不足・電源断）で残った `.partial` は件数の保持に数えられず残り続ける（約550MB。2026-10-02 のディスク満杯と同じ向きの危険）。そのため backup.sh の開始時（mkdir の直後）に `find "${BACKUP_DIR}" -name 'salesanchor_db_*.sql.gz.partial' -mmin +1440 -delete` を置く。1日より古いものに限るのは、毎朝3時の控えと本番反映の控えが同時に動いたとき、相手の書き途中を消さないため（ふだんの所要は約2分、§15-2）。
3. 終了時の片付けと記録（終了コードの決め方を含む）:
   - trap は BACKUP_FILE を決めた行の後に置く（set -u のため、決める前に trap が動くと未定義で止まる）。
   - EXIT の trap の最初で `rc=$?` を取る。自分の `${BACKUP_FILE}.partial` だけを `rm -f` で消す（glob で消さない。同時に動く別の控えの書き途中を消さないため。B2 の片付けの項の「新しい方は残る」で確かめる）。rc が0でないときだけ backup.log に「Backup FAILED rc=<rc>」の1行を書く。最後に `exit "${rc}"`。
   - シグナルの trap は INT→`exit 130`、TERM→`exit 143`、HUP→`exit 129`（シグナルの番号を終了コードに残す）。どれも EXIT の trap を通る。
   - 本番反映の段は今までどおり失敗する。cron は cron.log に残る。
   - 段3が受け持つのは「ロック待ちの上限で pg_dump が自分から失敗する道」だけ。外から止める道（ssh の打ち切り・シグナル）は段2の範囲とする。理由: bash は前面のコマンドが終わるまで trap を動かさない（GNU bash マニュアル Signals の節）。加えて、docker compose exec の利用側を止めてもコンテナの中の pg_dump は止まらない（moby/moby#9098 として知られた動き。ここでは確かめていない）。backup.sh の中で子を kill しても、コンテナの中のロックは外れない。段2では pg_dump の接続名（pg_dump が既定で付ける application_name 'pg_dump'）で見つけて DB 側から止める案を検討する。
   - そのため試験 B2 の「途中で止められた」は、Ctrl-C と同じ形（プロセスグループ全体に TERM）で送る。backup.sh・偽 docker・gzip がそろって止まる形で判定する（§15-4）。
4. 試験のために保存先を外から変えられるようにする: `BACKUP_DIR="${SALESANCHOR_BACKUP_DIR:-/home/ubuntu/backups/postgres}"`、`COMPOSE_FILE="${SALESANCHOR_BACKUP_COMPOSE_FILE:-/home/ubuntu/salesanchor/docker-compose.yml}"`。本番の cron・本番反映ではどちらも渡さないので今と同じ値（名前が他と重ならないよう SALESANCHOR_ を付ける）。
5. 書き途中も持ち主だけが読めるようにする: pg_dump の前に `umask 077` を置く（今は chmod 600 の前の書き途中が umask のまま作られる）。:32 の chmod 600 は残す。
6. 本番の文の数（reader 鍵の道で測定、2026-10-29 14:47Z）: pg_dump がロックする表（relkind が r と p、システムのスキーマを除く）は513表・6スキーマ（public 116、tenant_001 99、tenant_004 91、tenant_003 69、tenant_006 69 ほか）。名前を並べた長さは 14,466 バイトで、約100KB の区切りの 14% に当たる。LOCK TABLE は1文なので、待ちの最悪は120秒。待ち120＋ふだんの所要約120＝240秒で、600秒の打ち切りより短い。表が約7倍（約3,600表）に増えるまでは1文のまま。テナントを足すときはこの数を測り直す。
7. 変えないもの: 出力の形（プレーン SQL を gzip。復元は `scripts/restore.sh` :50-52 の gunzip→psql のまま）、ファイル名、件数と日数の保持、write_success_timestamp（見出し行 `write_success_timestamp() {` は `scripts/tests/test-backup-timestamp.sh` :32 の抜き出しが頼るので変えない）、`.github/workflows/deploy.yml`。

### 15-4. 試験（PR の CI で毎回走らせる）
- 入れ物（B1・B4 で共用）: 試験用の compose ファイルを1つ作り、サービス名 `postgres`・image `postgres:16`・環境変数 POSTGRES_USER=jarvis、POSTGRES_DB=jarvis_db（backup.sh の既定値に合わせる）、POSTGRES_HOST_AUTH_METHOD=trust（試験用。合言葉を置かない）とする。`docker compose -f <ファイル> up -d` の後、`pg_isready` が通るまで待つ（上限60秒）。表を1つ作る。psql と pg_dump はどちらもコンテナの中で動かす（`docker compose -f <ファイル> exec -T postgres …`。本番と同じ形で、runner 側の版に頼らない）。
- B1 実物の PostgreSQL 16 で:
  - B1a 握られている形: 裏で `psql -c "BEGIN; LOCK TABLE <表> IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(60);"` を動かし、ロックが取れたことを pg_locks で確かめてから `pg_dump --lock-wait-timeout=2000` を流す。
  - B1b 待ち行列にいる形（10/29 と同じ）: 接続 A が `BEGIN; SELECT 1 FROM <表> LIMIT 1; SELECT pg_sleep(60);` で共有ロックを持つ。接続 B が `BEGIN; LOCK TABLE <表> IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(60);` で待つ（LOCK は取引の外では即エラーになるため BEGIN を付ける。PG16 文書 sql-lock.html）。pg_locks で B の granted=false を確かめる。その後ろで同じ pg_dump を流す。
  - 判定（B1a・B1b とも）: rc=1・所要10秒未満・標準エラーに `canceling statement due to statement timeout` と `LOCK TABLE` の両方がある（PG16 原典 src/bin/pg_dump/pg_backup_db.c :268-275 の die_on_query_failure）。その後、握りの接続（B1a の1本、B1b の A と B）を全部 `pg_terminate_backend` で止め、同じ命令が rc=0 になることを確かめる。
  - backup.sh から PG_DUMP_LOCK_WAIT_MS の値を読み取り、数字だけであることも確かめる。
- B2 backup.sh 全体を偽の docker で: PATH の先頭に外部の実行ファイルとして偽 docker を置き（シェル関数は使わない）、SALESANCHOR_BACKUP_DIR と BACKUP_TEXTFILE_DIR は一時フォルダにする。
  - 成功: 古い控え `salesanchor_db_*.sql.gz` を11本（時刻をずらして）置いておく。偽 docker が SQL の文字列を出して0で終わる。判定: rc=0。新しい控えが1本でき、gunzip で元の文字列に戻る。新しい控えの権限が600。保存先の控えが新しいものを含めて10本。backup.log に保持の行と Completed の行がある。BACKUP_TEXTFILE_DIR に backup_local.prom がある。`.partial` が0本。偽 docker が受け取った引数に `--lock-wait-timeout=120000` がある。
  - 失敗: 古い控え11本を置き、偽 docker が少し出力した後に rc=1 で終わる。判定: backup.sh の rc≠0。`salesanchor_db_*.sql.gz` は11本のまま（失敗時に件数の保持へ進まない）。`.partial` が0本。backup.log に「Backup FAILED rc=」の行がある。backup_local.prom ができていない。
  - 古い書き途中の片付け: 2日前の時刻の `.partial` と、いま作った `.partial` を置いて成功させる。判定: 古い方だけ消え、新しい方は残る。
  - 途中で止められた: 偽 docker は始まったら印のファイルを作り、sleep 60 する。backup.sh は CI の非対話の bash から `setsid bash scripts/backup.sh &` で起動する（fork しない形。`ps -o pgid= -p $!` が `$!` と同じことを確かめる）。印のファイルができるのを待ってから、そのグループ全体へ TERM を送る。判定: 10秒以内に backup.sh が rc=143 で終わる。`.partial` が0本。偽 docker が残っていない（pgrep で0本）。backup.log に「Backup FAILED rc=143」がある。
- B3 既存の `scripts/tests/test-backup-retention.sh` と `scripts/tests/test-backup-timestamp.sh` も同じジョブで流す（今は CI で動いていない。2026-10-29 に .github を検索して参照0件）。前者は保持の仕組みの写しを試すもので backup.sh 自体は試さない。backup.sh の保持は B2 の成功の項が受け持つ。
- B4 本物の backup.sh を本物の pg_dump で: 入れ物の compose ファイルを SALESANCHOR_BACKUP_COMPOSE_FILE で渡し、SALESANCHOR_BACKUP_DIR と BACKUP_TEXTFILE_DIR は一時フォルダにする。B1 の握りの接続はすべて止めておく。偽 docker では `docker compose exec` に渡す引数の書き間違いを捕まえられないので、この項を置く。
  - B4a 成功: rc=0。できた控えを gunzip すると、作った表の CREATE TABLE がある。
  - B4b 上限で止まる: B1a と同じ握りを作り（ただし `pg_sleep(300)` にして、120秒の上限より長く握る）、本物の backup.sh を流す。判定: rc≠0、所要は120秒以上・180秒未満、`.partial` が0本、`salesanchor_db_*.sql.gz` が増えない、backup.log に FAILED 行がある。backup.sh の定数が本物の pg_dump に届いて上限で止まることを一続きで確かめる（約2分かかる）。終わったら握りを止める。
- 置き場所: 新しいワークフロー `.github/workflows/backup-script-test.yml` を1つ作る。手本は `.github/workflows/deploy-script-test.yml`（偽 docker の単体試験・必須チェックにしない、という同じ形）。`scripts/backup.sh`・scripts/tests/ の test-backup- で始まるシェル（`scripts/tests/test-backup-lock-wait.sh` など）・試験本体・このワークフロー自身が変わった PR と、手での起動で走らせる。必須チェックにはしない（必須チェックの変更は PO 本人の操作）。ワークフローを足したときに「CI設定整合性チェック」への登録が要るかは未確認で、実装 PR の CI で確かめる。

### 15-5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K3-1 排他ロックを握られている・待ち行列にいるとき、pg_dump が上限で自分から止まる | B1a・B1b PASS（PR の CI） |
| K3-2 失敗・中断で書き途中のファイルが残らず、古い控えも消えない。古い書き途中だけ片付く | B2 の失敗・中断・片付けの項 PASS |
| K3-3 成功時の出力・名前・権限・保持・成功時刻の書き出しが今と同じ | B2 の成功・B3・B4 PASS |
| K3-1b 試験が壊れた実装を捕まえる | 実装 PR で一度だけ、backup.sh から `--lock-wait-timeout` を外すと B2 の引数の判定と B4b が赤になること、trap を外すと B2 の失敗の項が赤になることを示す（結果を PR に貼る。B1 は pg_dump を直接呼ぶので backup.sh の壊れ方では赤にならない） |
| K3-4 本番: この変更を含み、移行のある本番反映3回で、「Pre-deploy DB backup」が success かつ所要300秒以内。backup.log に Completed 行がある | 本番反映ログの段の時刻と backup.log（読み取り） |
| K3-5 本番: 同じ3回の後と、翌朝3時の控えの後に、保存先に `.partial` が0本・pg_dump のプロセスが0本 | prod1 の ls と ps（読み取りのみ。ps の出力は合言葉を伏せる） |
| K3-6 本番: 翌朝3時の控えが Completed になる | backup.log の 03:0x の行 |
効き目（実際にロックで止まること）は本番では起こせないので B1 が担う。本番でロック待ちによる失敗が起きたら、そのとき FAILED 行と段の所要時間を追記する。

### 15-6. 弊害・トレードオフ
- 毎朝3時の控えが、120秒より長く排他ロックを握る作業と重なると失敗する（今は待ち続けて取れていた）。BackupLocalStale は「最後の成功から26時間」で鳴る（`monitoring/prometheus/alert_rules.yml` :247-256）。移行の無い日は本番反映の控えが取られない（`.github/workflows/deploy.yml` :197-198）ので、3時が失敗すると、前日3時の成功から26時間後の同じ日の5時ごろに鳴る。前日3時の後に移行のある本番反映の控えが成功していれば、その時刻から26時間後まで鳴らない。
- 上限で失敗すると、pg_dump は失敗した LOCK TABLE 文を丸ごと標準エラーに出す（最大約100KB、原典 pg_backup_db.c :269-275）。本番反映のログと cron.log が1回あたりその分大きくなる。
- pg_dump が共有ロックを取った後の約2分は、移行の排他ロックが待たされる（今と同じ）。段1の後、移行は1秒で諦めて再試行するので、毎朝3時と本番反映が重なると移行の再試行が増える。
- 本番反映の段は、ロック待ちのときは10分ではなく約2分で失敗する。その後の本番反映は同じ理由でまた失敗し得る（段2の範囲）。

### 15-7. 範囲外として記録すること（この段では直さない）
- 本番反映の控えが毎朝3時の控えを件数の保持で押し出す（10/29 は1日で10本を超えた）。S3 への写し（毎朝3:30、`scripts/backup_to_s3.sh` :91）が3時の控えを外へ写すので、外の写しは残る。S3 側の保持期間は未確認。別件として扱う。宿題の持ち主: 設計担当（Opus）。段3の本番測定の後に、S3 の保持期間を読み取りで確かめて記録する。

### 15-8. 戻し方・計画
- 戻し方: この PR を revert して main にマージ。次の本番反映・次の cron から今の形に戻る。DB・既存の控えは変えない。
- 計画: (1) 本節の Architect 審査（新しく起動） (2) Sonnet が実装・CI (3) reviewer（opus、新しく起動）の審査 (4) 委任 GO（本番 scripts を含み ADR-135・136 の GO 対象。ADR-1003 の例外7種には当たらない。移行・DROP は無い）・マージ (5) K3-4〜K3-6 と、段1の K8・K9 を同じ本番反映で測る (6) 段2の詳細設計へ。
- 継続: 値の正本は backup.sh の PG_DUMP_LOCK_WAIT_MS だけ。守り手: `.github/workflows/backup-script-test.yml`（B1〜B4。実装 PR で作る）。

## 16. 段2 詳細設計 — 本番反映が時間切れで切れたとき、サーバーに残った控え・移行を片付ける（第3.1版）
状態: 設計審査済み（第3.1版 Architect APPROVE）・設計マージ済み（PR #4868）。実装 PR #4872 は reviewer（opus）APPROVE・CI の C1〜C9 緑・赤の実演4本確認済み。段3の本番測定（K3-4〜K3-6、K3-4 は手の3回で代えた）と段1の K8・K9 がそろったので、本番に出す（§3 の順番）。
審査の記録: 第1版 REVISE（2026-10-30、Architect 新規起動。§16-1 の外部の主張・行番号・名前の付け方・id と Finalize への影響は合格）。指摘: R1 控えの段は前回のコードで動くので初回に片付けのスクリプトが無く本番反映が止まり続ける／R2 接続を1回しか切らない／R3 赤の実演が赤にならない／R4 本物の移行スクリプトの trap の試験が無い／R5 待ち60秒が ai_ro の作り直しの最悪より短い／R6 手で止めた回が対象外。条件 1〜7（paths・lib の読み方・S3 の範囲・B5 の書き間違い・ADR-1037 の追記・ADR-1005 との関係・pgrep の正規表現）。第2版で 16-1・16-3〜16-11 に反映した。第2版 REVISE（2026-10-30、Architect 新規起動。R1・R5・R6・条件2〜7 は合格。if 文の動き・古い backup.sh に引数を渡しても rc=0・取り消しの条件式を手元の実測と文書で照合）。指摘: N1 C3 は1回だけ切る版でも緑になる（TERM を先に送ると trap がすぐ動く）／N2 C8 は TERM の trap の有無を区別できない（trap が無くても TERM で EXIT の trap は動く。違いは前面を待つかどうか）／N3 失敗のときの段に cd が無く毎回 skipped になる／N4 プロセスが見つからない取り残しの接続を切り直さない。条件: C-a 時間計算に ai_ro の作り直しが入っていない／C-b C9 が deploy.yml の本文を読まない・paths／C-c ジョブの時間の上限。第3版で 16-2・16-4・16-5・16-6 に反映した。第3版 条件付き APPROVE（2026-10-30、Architect 新規起動。N1〜N4・C-a〜C-c は直っていると、DB を使わない手元の模擬（bash 3.2）で照合）。条件: M1 試験用 DB のコンテナ名が片付けの固定名と違う／M2 C8 の偽 docker の指定（止める run_sql の位置・REPO_DIR・順番の判定の細かさ・TERM の送り先）／M3 16-4 の9 の重なる条件が控えと移行の段の起動条件の違いを見ていない／M4 ai_ro の作り直しは5文／M5 失敗のときの段の台本に set -e。任意: trap を置く位置。第3.1版で 16-1・16-2・16-4・16-5・16-6 に反映した。

### 16-1. 事実（2026-10-30 調べ。行番号は origin/main）
- 本番反映（`.github/workflows/deploy.yml`）のサーバー側の段は全部 `appleboy/ssh-action@v1` で、`command_timeout` を書いていない（with に command_timeout・request_pty の指定は0件）。既定は 10m（appleboy/ssh-action v1 の action.yml :28-30）。
- 時間切れのとき、action はサーバー側へ信号を送らない。action は drone-ssh 1.8.2 を使い（entrypoint.sh の DRONE_SSH_VERSION 既定）、それが使う easyssh-proxy v1.5.0 の Stream は時間切れで session と client を閉じるだけで、Signal の呼び出しが無い（github.com/appleboy/easyssh-proxy v1.5.0 easyssh.go、github.com/appleboy/drone-ssh v1.8.2 go.mod）。request_pty は既定で無効。第1版の審査で同じ出典を照合済み。
- よって、時間切れで切れた段のサーバー側のプロセス（bash・`docker exec`・コンテナの中の pg_dump や移行）は動き続け得る。10/29 はこの形で控え6本が約45〜105分残った（§15-1）。
- 「Pre-deploy DB backup」（deploy.yml :197-218）は「Deploy to VPS」の `git reset --hard origin/main`（:255-256）より前に動く。よって控えの段では、いつも前回の本番反映のときのサーバーの scripts/ が動く。「Deploy to VPS」には if が無い（:232）ので、控えの段が失敗すると飛ばされ、サーバーのコードは古いまま残る。gate（:72-78）は前回成功の本番反映が直前と違うと db_migrations=true にするので、次の本番反映でも控えの段が動く。Finalize の自動の戻し（:714-719）でも、サーバーのコードが前のコミットに戻ることがある。
- 「Run database migrations」は「Deploy to VPS」の後なので、今回のコードで動く。
- 本番反映は concurrency `deploy-production`・`cancel-in-progress: false`（deploy.yml :14-16）で1本ずつ動く。`scripts/run_all_migrations.sh` を呼ぶのは deploy.yml :605 だけ。`scripts/backup.sh` を呼ぶのは deploy.yml :211 と毎朝3時の cron（ubuntu の crontab の1行。cwd は $HOME、`scripts/aws-setup/README.md` :168）だけ（main を git grep。scripts/tests とドキュメントを除く）。
- いまの目印: Python の移行の接続は application_name=salesanchor_migration（`scripts/migration_py_entry.py` :40、MIGRATION_LOCK_TIMEOUT があるとき）。run_sql の psql（`scripts/run_all_migrations.sh` :114）と pg_dump（`scripts/backup.sh` :53-55）には付けていない。読み取り監視は sa_read_probe（:160）。
- 開始時に取り残しを止める仕組みは無い（deploy.yml と scripts/ に pkill・pg_terminate_backend・pg_cancel_backend・killall の該当0件。試験の後始末だけ）。
- `scripts/run_all_migrations.sh` の trap は EXIT の1つだけ（:245）。TERM・HUP・INT の trap は無い。`scripts/backup.sh` は INT・TERM・HUP を exit に変えている（:44-46）。
- ai_ro の作り直し（EXIT の trap、:226-243）は `migrations/20261017_130100_create_ai_ro_views.sql` を1文30秒の上限（:223・:239）で流す。中身は BEGIN〜COMMIT の中の5文（DROP SCHEMA … CASCADE・CREATE SCHEMA・DO・GRANT 2文。ファイルの :8・:9・:11・:78・:79）。lock_timeout は付いていない。GRANT 2文は ai_ro の中の自分で作ったものが相手なので、ほかの接続のロックを待たないと見込む（まだ確かめていない）。最悪約90秒は DROP・CREATE・DO の3文の上限の和。最悪は約90秒＋読み取り監視の停止（2秒以内、:127）。
- 本番 prod1 の ps（2026-10-29 15:31Z、読み取りのみ）: backup.sh・run_all_migrations.sh・pg_dump・docker exec の行は0本。いま取り残しは無い。
- 段1・段3の後、ロック待ちの上限はどちらも10分より短い。移行は最悪約458秒（§9）、控えは待ち120秒＋ふだん約120秒（§15-3）。よって段2が受け持つのは「ロック待ち以外の理由で10分を超えた回」「手で止めた回」と「段1・段3の上限の見込み違い」の後始末。

### 16-2. 変更前 → 変更後
| 項目 | 変更前 | 変更後 |
|---|---|---|
| 控えと移行の段の時間切れ | 書いていない（既定 10m） | 2つの段に `command_timeout: 10m` を書く（値は今と同じ。既定が変わっても動きが変わらないようにする） |
| 控えの接続の名前 | なし（pg_dump の既定） | 本番反映から呼ぶとき salesanchor_backup_deploy、cron から呼ぶとき salesanchor_backup_cron |
| run_sql の接続の名前 | なし | salesanchor_migration（Python と同じ名前） |
| 移行の TERM・HUP・INT | trap なし（TERM を受けると前面の docker exec を待たずに終わり、EXIT の trap が前面と並んで ai_ro を作り直す。第2版の審査の実測 t1） | backup.sh と同じく exit 143・129・130 に変える。置く位置は EXIT の trap（:245）のすぐ隣。前面の文が終わってから EXIT の trap が ai_ro を作り直す（実測 t2）。作り直しが、止めた移行の文と同時に走らない |
| 取り残しの片付け | なし | 新しい片付けのスクリプト（scripts/deploy-db-orphan-cleanup.sh）を、(1) 控えの段の最初 (2) 移行の段の最初 (3) 控えか移行の段が失敗・取り消しになったときの新しい段、で呼ぶ。サーバーにまだ無いときは何もせず通る |

### 16-3. 名前の正本
- 新しい scripts/lib/db-app-names.sh に3つの名前を置く（SA_APPNAME_MIGRATION=salesanchor_migration、SA_APPNAME_BACKUP_DEPLOY=salesanchor_backup_deploy、SA_APPNAME_BACKUP_CRON=salesanchor_backup_cron）。backup.sh・run_all_migrations.sh・片付けのスクリプトは `$(dirname "${BASH_SOURCE[0]}")/lib/db-app-names.sh` を source する（cron は cwd が $HOME なので相対パスにしない）。
- `scripts/migration_py_entry.py` の APP_NAME は Python なので source できない。CI の試験 C4 で、lib の SA_APPNAME_MIGRATION と入口の APP_NAME が同じ文字列であることを確かめる（ずれたら赤）。
- 控えの名前は backup.sh の第1引数で決める（`${1:-}` で読む）。引数なし＝cron（今の crontab の行を変えない）。`deploy` のときだけ deploy の名前。それ以外の引数は rc=2 で止める。引数の判定は trap を置くより前に置く（rc=2 のとき FAILED 行を書かない）。名前は `docker compose exec -T -e PGAPPNAME=<名前> postgres pg_dump …` で渡す（libpq は PGAPPNAME を application_name に使う。PostgreSQL 16 文書 libpq の環境変数の節。C1 で pg_stat_activity に出ることを確かめる）。
- 古い backup.sh は引数を読まないので、`bash scripts/backup.sh deploy` と呼んでも今と同じに動く（名前は付かない）。控えの段は前回のコードで動く（16-1）ので、この変更を含む最初の本番反映では控えに名前が付かない。2回目から付く。
- run_sql は `docker exec -e PGAPPNAME=<名前> -e PGOPTIONS=… -i postgres psql …` にする。log_lock_holders と ai_ro の作り直し（EXIT の trap）は名前を付けない（片付けの対象にしない。止めると後始末が止まる）。
- run_all_migrations.sh に足す行（source と trap）は、`.github/workflows/migration-test.yml` S3（:1013-1023）が調べる範囲（SQL_LOCK_TIMEOUT= から run_sql の終わりまで）の外に置く。run_sql の中では lib の変数を使い、範囲の中に既定値 `${SA_APPNAME_MIGRATION:-salesanchor_migration}` を書く（範囲だけを抜き出して動かす試験があっても動くように）。
- salesanchor_migration の意味が広がる（Python に加えて run_sql にも付き、本番反映が接続を切る目印になる）。ADR-1037 の名前の記述（:78）に、この2点を追記する（実装 PR で）。

### 16-4. 片付けのスクリプト（scripts/deploy-db-orphan-cleanup.sh）
呼ばれたときに残っている「本番反映の控え・移行」は、前の本番反映の取り残しか、手で流したものとみなす。理由: 本番反映は1本ずつ動き（16-1）、片付けを呼ぶ位置はどれも「同じ本番反映の控え・移行が動いていない」時点だから。毎朝3時の控え（cron の名前）は対象にしない。手で流した移行も止めてしまう点は 16-9 に書く。
1. サーバー側のスクリプトに TERM を送る: 引数が完全に一致するプロセスだけを探す（`pgrep -x -f '^bash scripts/run_all_migrations\.sh$'` と `pgrep -x -f '^bash scripts/backup\.sh deploy$'`。`.` はエスケープする）。部分一致は使わない（ssh-action の段の bash は台本全体を引数に持つので、部分一致だと自分の段を止める。C5）。読み取り監視の子（run_all_migrations.sh の中で fork した bash）も同じ引数を持つので数に入る。scripts=<n> は実際の本数より大きく出ることがある。
2. DB 側の接続を切る: `pg_stat_activity` で application_name が SA_APPNAME_MIGRATION か SA_APPNAME_BACKUP_DEPLOY、かつ自分以外の接続に `pg_terminate_backend`。Python の移行は1ファイル1取引なので、切った取引は戻る。run_sql のファイルは取引でまとめていないので、切った位置より前の文は残る。どちらも冪等の前提（`scripts/run_all_migrations.sh` :13・§4-4）で、次の本番反映が全件を流し直す。
3. 待ちながら切り続ける: 2秒ごとに、名前の付いた接続が1本でもあれば2をもう一度行う（1でプロセスが見つかったかどうかに関係なく）。「対象のプロセスが0本」かつ「名前の付いた接続が0本」になったら終わる。理由: TERM の trap は前面の `docker exec` が終わるまで動かない（§15 第1版の審査の指摘、第2版の審査の実測 t2）。前面の1つの子プロセス（Python の移行1本）が、中で接続を作り直すことがある。1回だけ切ると、作り直した接続が終わるまで前面が終わらず、trap が後ろにずれる。また、手で絶対パスで流した取り残しのように、1でプロセスが見つからず接続だけが見える形もある。
4. 待つ上限は120秒。内訳: ai_ro の作り直しの最悪約90秒（16-1）＋読み取り監視の停止2秒＋切ってから前面の docker exec が終わるまでの余裕。
5. 記録: 見つけた数・切った回数・残った数を1行ずつ出す（`>>> [cleanup] scripts=<n> backends=<n> remaining=<n>`）。SQL の文面と接続元アドレスは出さない（公開ログ。:62 と同じ方針）。
6. 残った（120秒で消えない）ときは rc=1 で止め、その段を失敗にする。KILL は送らない（ai_ro の作り直しや控えの書き途中の片付けを飛ばさないため。人が見て判断する）。
7. 見つからないときは何もせず rc=0。ふだんの本番反映はこの形。
8. DB への問い合わせは `docker exec astro-webapp-postgres-1 psql -U jarvis -d jarvis_db`（run_all_migrations.sh :24-25 と同じ）。コンテナ名はスクリプトに固定で書き、外から変えられるようにはしない（本番の値を1か所に保つ。試験は 16-6 で入れ物の名前を本番にそろえる）。`statement_timeout=5s`・`lock_timeout=1s` を付ける。名前は付けない。
9. 時間の上限: §9 の最悪458秒は移行の実測82.3秒に再試行40回を足したもので、移行が失敗で終わるときの ai_ro の作り直し（最悪約90秒、16-1）を含まない。移行の段の最悪は「最初の片付け（最悪120秒＋問い合わせ）＋458秒＋作り直し約90秒」≒670秒で、600秒を超え得る。控えの段は db_migrations（deploy.yml :198、範囲が狭い）、移行の段は migrations（:592、backend・scripts・deploy.yml まで含む）で動くので、控えの段が動かず移行の段の最初の片付けだけが取り残しに当たる本番反映はふだんからあり得る（:48-50 の記録では25件中 migrations 16件・db_migrations 3件）。片付けが rc=1 で終わると set -e で移行は始まらない。よって670秒に近づくのは「移行の段の最初の片付けが120秒近くかかり、最後に消しきれた」回だけ。前の本番反映の失敗のときの段（16-5）が先に片付けているので、まれと見込む。超えて段が切れた場合は、失敗のときの段がその取り残しを止める。控えの段は「片付け（最悪約125秒）＋待ち120秒＋ふだん約120秒」≒365秒。

### 16-5. deploy.yml の変更
- 3か所とも、片付けは「サーバーにファイルがあるときだけ呼ぶ」書き方にする: `if [ -f scripts/deploy-db-orphan-cleanup.sh ]; then bash scripts/deploy-db-orphan-cleanup.sh; else echo ">>> [cleanup] skipped: script not present (old checkout)"; fi`。理由: 控えの段と失敗のときの段は前回のコードで動き得る（16-1）。無いときに rc=127 で止まると、本番反映が手で直すまで通らなくなる。
- 「Pre-deploy DB backup」: id を backup にする。`command_timeout: 10m` を足す。台本の `bash scripts/backup.sh` の前に片付けを置き、`bash scripts/backup.sh deploy` に変える。
- 「Run database migrations」: id を migrate にする。`command_timeout: 10m` を足す。`bash scripts/run_all_migrations.sh` の前に片付けを置く（この段は今回のコードで動くので、ファイルは必ずある。書き方は3か所でそろえる）。
- 新しい段「Clean up DB orphans after failure」: 「Run database migrations」の直後に置く。条件は `always() && (steps.backup.outcome == 'failure' || steps.backup.outcome == 'cancelled' || steps.migrate.outcome == 'failure' || steps.migrate.outcome == 'cancelled')`（手で止めた回の outcome は cancelled で、failure() は偽になるため）。中身は `set -e`・`cd /home/ubuntu/salesanchor`・片付けの if 文をこの順に書くだけ（set -e が無いと cd が失敗しても段は緑のまま何もしない。ssh の段は $HOME から始まり、if 文は相対パスでファイルを探すので、cd が無いと毎回 skipped になる。ほかの段もはじめに cd している、deploy.yml :209・:244・:604・:621・:643）。`command_timeout: 5m`。この段の結果は、後ろの「Finalize」（if: always()）と「Emergency block /design/」（if: failure()）の動きを変えない（本番反映全体は既に失敗か取り消し）。
- 時間切れで段が切れた直後に片付けるので、取り残しが次の本番反映まで残らない。次の本番反映の段の最初の片付けは、この段自体が動かなかったとき（Actions 側の障害など）の保険。
- `cancel-in-progress` と他の段は変えない。

### 16-6. 試験（PR の CI。`.github/workflows/backup-script-test.yml` の入れ物（§15-4、postgres:16 の compose）を使う。新しいジョブを同じファイルに足す）
- 入れ物の compose ファイルに `name: astro-webapp` を書き、コンテナ名を本番と同じ astro-webapp-postgres-1 にする。理由: §15-4 の試験（scripts/tests/test-backup-lock-wait.sh）は名前を書かずに一時フォルダの compose/ に作るので、コンテナ名が本番と違う。そのままだと片付けは試験用 DB を見に行けず、C2・C3 は赤、C5・C6 は何も確かめずに緑になる。試験の最初に `docker inspect astro-webapp-postgres-1` が動くことを確かめ、動かなければ FAIL にする。
- paths に足す（pull_request と push の両方）: scripts/lib/db-app-names.sh・scripts/deploy-db-orphan-cleanup.sh・`scripts/migration_py_entry.py`・`scripts/run_all_migrations.sh`・`.github/workflows/deploy.yml`・新しい試験のファイル（名前の正本だけ、または deploy.yml だけを変える PR でも C4・C9 が動くように）。
- 新しいジョブの `timeout-minutes: 15`。見積もり: 入れ物の起動 約1分＋C2 最悪約125秒＋C7 120〜135秒＋C3 約10秒＋C1・C4〜C6・C8・C9 合わせて約1分 ≒ 約7分。15分は今のジョブと同じで、見積もりの約2倍。
- C1 名前が付く: `bash scripts/backup.sh deploy` を流している間に pg_stat_activity を見て、application_name=salesanchor_backup_deploy の接続が1本ある。引数なしでは salesanchor_backup_cron。`bash scripts/backup.sh foo` は rc=2 で控えを作らず、backup.log に FAILED 行を書かない。cwd を $HOME にして絶対パスで呼んでも lib を読める。
- C2 取り残しを止める（控え）: B4b と同じ握り（pg_sleep 300 の排他ロック）を作り、`setsid bash scripts/backup.sh deploy` を裏で起動して待ちに入ったことを pg_stat_activity で確かめる。片付けを流す。判定: 片付けは rc=0 で、backup.sh の bash が120秒以内に消える・名前の接続が0本・`.partial` が0本・backup.log に FAILED 行・握りの接続は残っている（関係ない接続を止めない）。
- C3 取り残しを止める（移行の形）: 偽の run_all_migrations.sh（試験用の一時フォルダに scripts/run_all_migrations.sh を置き、そこを cwd にして `bash scripts/run_all_migrations.sh` の形で起動）を使う。偽物の前面は子プロセス1つで、その子の中で名前（salesanchor_migration）を付けた接続の `SELECT pg_sleep(300)` を3回続けて作り直す（切られたら待たずに次を始める。本物の Python の移行1本が中で接続を作り直す形に合わせる）。子は pgrep の完全一致に当たらない命令行にする（TERM は親だけに届く）。TERM・EXIT の trap は本物と同じ形にし、EXIT で印のファイルを書く。判定: 片付けの後120秒以内に偽物が消え、EXIT の印がある・名前の接続が0本・片付けは rc=0。1回だけ切る実装では、親は TERM を受けても前面の子が2回目の pg_sleep(300) を終えるまで終わらないので、120秒以内に消えず赤になる。
- C4 名前の正本: lib の3つの名前と `scripts/migration_py_entry.py` の APP_NAME を読み、移行の名前が一致する。
- C5 部分一致で止めない: `bash -c "…; bash scripts/run_all_migrations.sh; …"` の形の bash を裏で動かしておき、片付けの後も残っている（ssh-action の段と同じ形を止めない）。cron の名前の控えの接続（引数なしの backup.sh を握りで待たせる）も残っている。
- C6 何も無いとき: rc=0・出力は `scripts=0 backends=0 remaining=0`。
- C7 残ったら止まる: TERM を無視する偽スクリプト（trap '' TERM）で、片付けが120秒後に rc=1 になる（所要 120〜135秒）。
- C8 本物の移行スクリプトの trap: 本物の run_all_migrations.sh を、`.github/workflows/migration-test.yml` の S3・R5 と同じ考え方の偽 docker（PATH の先頭に置く外部の実行ファイル）の上で動かす。偽 docker は、EXIT の trap（:245）の後の最初の run_sql（:255、013 のファイル）の呼び出しでだけ sleep 300 し、:215 の drop・ai_ro の作り直し・preflight・docker cp など、ほかの呼び出しはすぐ rc=0 で返す（:215 の drop は trap より前なので、そこで止めると正しい実装でも [final] 行が出ない）。呼ばれるたびに「開始・終了・引数」を1行ずつ、1つの記録のファイルに追記する。REPO_DIR は checkout の根を指す（一時フォルダにすると preflight（:205-208）と :114・:232 が migrations を見つけられず止まる）。スクリプトは `bash scripts/run_all_migrations.sh &` で起動し、TERM はそのとき得た `$!` にだけ送る（pgrep で探すと、同じ命令行を持つ読み取り監視の子 :150-174 にも当たる）。013 の sleep に入ったことを記録で確かめてから TERM を送る。数秒おいて偽 docker の sleep を止めて前面を終わらせる。判定: rc=143、標準出力に `>>> [final] psql < migrations/20261017_130100_create_ai_ro_views.sql` の行がある、記録のファイルの行の順で「ai_ro の作り直しの最初の呼び出しの開始」が「止めた run_sql の呼び出しの終了」より後（秒単位の時刻では同じ秒になるので、時刻ではなく行の順で比べる）。判定は、止めた run_sql の終了の行が記録に書かれるのを待ってから行う（赤の側で、終了の行より先に判定しないため）。TERM の trap が無いと、スクリプトは前面を待たずに終わり、EXIT の trap が止めた run_sql と並んで作り直しを始めるので、順番の判定が赤になる（第2版の審査の実測 t1、手元の bash 3.2）。本番の bash 5 で同じ動きかは確かめていない。C8 は CI の Ubuntu（bash 5）で動くので、そこで確かめる。
- C9 古いサーバーのコード: `.github/workflows/deploy.yml` の本文から、id が backup・migrate の段と「Clean up DB orphans after failure」の段の台本を抜き出す（YAML として読む。道具は `pip install pyyaml` で入れる。前例 `.github/workflows/monitoring-check.yml` :45）。判定: 3つとも `set -e`・`cd /home/ubuntu/salesanchor`・片付けの if 文がこの順にある・3つの if 文が16-5の文と一字一句同じ・抜き出した if 文を片付けのファイルが無い一時フォルダで `set -e` の下で流すと rc=0 と skipped の行が出る。
- 赤の実演（実装 PR で1回、結果を PR に貼る）: (1) pgrep の完全一致を部分一致に変えると C5 が赤 (2) 16-4 の3の「切り続ける」を1回だけ切る形に戻すと C3 が赤（前面の子が2回目の pg_sleep(300) を始め、親は120秒で消えない） (3) run_all_migrations.sh の TERM の trap を外すと C8 が赤（作り直しが止めた run_sql の終了より前に始まり、順番の判定が赤） (4) deploy.yml の失敗のときの段から `cd /home/ubuntu/salesanchor` を消すと C9 が赤。

### 16-7. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K2-1 取り残しの控え・移行を止め、関係ない接続・cron の控え・自分の段は止めない | C2・C3・C5 PASS（PR の CI） |
| K2-2 ふだんの本番反映では何もしない。古いサーバーのコードでも止まらない | C6・C9 PASS と、本番反映ログの片付けの行 |
| K2-3 本物の移行スクリプトが TERM で ai_ro を作り直して終わる | C8 PASS |
| K2-4 試験が壊れた実装を捕まえる | 赤の実演（16-6） |
| K2-5 本番: この変更を含み、移行のある本番反映3回で、控えと移行の段が success、失敗のときの段は skipped。片付けの行は、1回目の控えの段だけ `skipped: script not present (old checkout)`、それ以外は `scripts=0 backends=0 remaining=0` | 本番反映ログ |
| K2-6 本番: 同じ3回の後に、prod1 の ps に backup.sh deploy・run_all_migrations.sh が0本、pg_stat_activity に2つの名前が0本、ai_ro のビューがある | ps（読み取り）と reader 鍵の道 |
| K2-7 本番: 翌朝3時の控えが Completed | backup.log の 03:0x の行（名前はその時刻には見られないので、C1 で代える） |
効き目（時間切れの後に本当に止まること）は本番では起こさない。C2・C3・C8 が担う。本番で時間切れや手で止めた回が起きたら、その回の片付けの行と ps を追記する。

### 16-8. 選ばなかった案
- サーバー側で `timeout 540 bash …` と包む: 時間で強制的に切るので、ロック待ち以外の正当に長い回（例: 控えが大きくなった回）も切る。片付けは「前の本番反映の取り残し」だけを対象にでき、正当な回を切らない。
- `command_timeout` を延ばす: 切れるまでの時間が延びるだけで、切れた後に残る形は変わらない。10/29 は待ちが約113分で、どの長さでも足りない。
- サーバー側で切り離して動かし（nohup・systemd-run）、段は終わるのを見に行くだけにする: 段の作りが大きく変わり、見に行く側の時間切れで同じ問題が残る。
- `request_pty: true`（接続を閉じたときサーバーが SIGHUP を送る見込み）: 挙動を実測しておらず、コンテナの中の pg_dump・移行には届かない（`docker exec` の先は別のプロセスの木）。DB 側の接続を切る方が確実。
- `pg_cancel_backend`（今の文だけ取り消す）: 移行スクリプトは次の文・次のファイルへ進み得る。接続ごと切る方が止まる。
- 部分一致の `pkill -f`: ssh-action の段の bash を止める恐れ（C5）。
- `application_name` だけで切り、プロセスは止めない: 取り残しが次のファイルへ進む。
- 古いサーバーのコードへの対処として、Actions 側の checkout から片付けのスクリプトを rsync で送ってから呼ぶ（deploy.yml :97-117 の rsync を使う）: 確実に今回の版で動くが、送る段の失敗という新しい道が増える。片付けは保険なので、無いときは通す方を選ぶ。2回目の本番反映からは必ずある。

### 16-9. 弊害・トレードオフ
- run_sql のファイルを途中で止めると、そのファイルの前半だけが入った状態になる。冪等の前提で次の本番反映が流し直すが、その間は前半だけの状態。今も時間切れの後に残ったスクリプトが進み続けて同じことが起こり得るので、悪くはならない。
- 手で流した移行（`bash scripts/run_all_migrations.sh`）も、本番反映の片付けに止められる。手で流すときは本番反映と重ならない時間にする（16-11 の継続に書く）。
- 片付けが rc=1（120秒で消えない）になると、その段は失敗し、gate の働きで次の本番反映も同じ段で止まり得る。人が prod1 で見て止めるまで本番反映が通らない。失敗の知らせは今と同じ（Deployment Failure Notification の段、:1078-1083 は echo だけ）。
- この変更を含む最初の本番反映では、控えに名前が付かない（16-3）。その回に取り残しが出ても、片付けは DB 側の接続を見つけられず、プロセスだけを止める。
- 片付けのスクリプトが DB に数回つなぐ（ふだんは1本反映あたり2回、各数十ミリ秒）。
- 本番反映の段が1つ増える（失敗・取り消しのときだけ動く）。
- cron の控えが本番反映の取り残しの控えと重なると、cron の控えは止めないので、ロックの取り合いは段3の上限（120秒）任せのまま。

### 16-10. 範囲外（記録のみ）
- 「Deploy to VPS」など、DB に触らない段の時間切れ（docker build など）。取り残しの形が別で、10/29 の事故とは関係ない。
- ssh が切れた後、取り残しの移行スクリプトが次の echo で SIGPIPE を受けて死ぬ道（未実測）。その場合、EXIT の trap が動かず ai_ro が外れたまま残り得る（今もある危険）。K2-6 で ai_ro の有無を見る。起きたら別の段で直す。
- ADR-1005 段階2（適用済みの記録）との関係: 記録は「そのファイルが成功した後にだけ書く」前提を保つ。そうすれば、途中で切られたファイルは記録されず、次の本番反映で流し直される。段階2を設計するときにこの前提を書く。
- 170250 の出どころ（§15-1）と、root の crontab の中身。

### 16-11. 戻し方・計画
- 戻し方: この PR を revert して main にマージ。次の本番反映から今の形に戻る。backup.sh は引数なしの動きが今と同じなので cron は影響を受けない。片付けのスクリプトがサーバーに残っても、呼ぶ行が無くなるので動かない。DB は変えない。
- 計画: (1) 本節の Architect 審査（新しく起動） (2) Sonnet が実装・CI・赤の実演・ADR-1037 の追記 (3) reviewer（opus、新しく起動） (4) 本番に出すのは段3の K3-4〜K3-6 と段1の K8・K9 がそろった後。委任 GO（deploy.yml と本番 scripts を含む。ADR-1003 の例外7種には当たらない。移行・DROP は無い） (5) K2-5〜K2-7 (6) 段4の詳細設計へ。
- 継続: 名前の正本は scripts/lib/db-app-names.sh。守り手: `.github/workflows/backup-script-test.yml`（C1〜C9）。手で移行を流すときは本番反映が動いていないことを Actions の画面で確かめる（人手で守る）。

## 17. 段4 詳細設計 — アプリの全ての DB 接続に名前を付け、ロック待ちのログを出す（第1.1版）
状態: 設計審査済み（第1版 条件付き APPROVE、条件 A1〜A4 は第1.1版で反映。条件どおりに入っていれば再審査は要らない、と審査役が明記）。
審査の記録: 第1版 条件付き APPROVE（2026-10-30、Architect 新規起動。17-1 の行番号・同期16行が psycopg2 の URL に置き換えていること・SQLAlchemy の connect_args・psycopg2 のキーワード・asyncpg の server_settings を実物と公式資料で照合）。必須: A1 C4-1 の判定の形（`**` で渡す辞書）／A2 25本目の接続（`backend/app/ops/readonly_query.py` :282・:289）／A3 smoke [7b] の見張りの範囲が狭くなる／A4 片付けのスクリプトも名前を読む。推奨 B1〜B7 と 4b の補足も反映した。マージ前の審査（reviewer、opus 新規起動、391105c2f）で B5・A4 の継続の行・B2〜B4 の置き場所の漏れを指摘され、同じ第1.1版の中で直した。段4は 4a（名前を付ける）と 4b（ロック待ちのログ）に分け、4a を詳細、4b を概要とする。4a を本番に出すのは、段2の K2-5〜K2-7 がそろった後（§3 の順番）。4b は 4a の本番測定（K4-5）の後に詳細設計する。

### 17-1. 事実（2026-10-30 調べ。行番号は origin/main ddbe41261）
- 10/29 にロックを握っていたのは、名前の無い salesanchor_app の接続1本だった（§2）。名前が無いので、どのコンテナのどの処理かを特定できていない。
- `scripts/run_all_migrations.sh` の log_lock_holders は、移行が待ちで失敗したときに、開いている接続の application_name と握っている表を出す（段1）。名前の無い接続は空欄で出るので、相手を特定できない。
- アプリ（backend/app）の中で DB 接続を作る行は24行。名前を付けているのは5行だけ: `backend/app/database.py` :15（salesanchor_backend）・:70（salesanchor_admin_ops）、`backend/app/tasks/tcg_extraction.py` :790、`backend/app/tasks/tcg_extraction_recovery.py` :170、`backend/app/tasks/viewer_inventory_cache.py` :117。残り19行は名前が無い（celery の同期 create_engine 12行、`backend/app/tasks/priority_scoring_check.py` :83 の psycopg2.connect、`backend/app/tasks/buyback_scraper.py` :29、`backend/app/services/email_sender.py` :38、`backend/app/services/gemini_extraction_svc.py` :105・:154、`backend/app/services/tcg_product_master_svc.py` :828、`backend/app/discord_gateway/reaction_writer.py` :35 の asyncpg.create_pool）。調べの全表は作業メモ（社内）にある。同期の16行は全部 psycopg2 の URL に置き換えてから作っている（審査で照合）。
- これとは別に、`backend/app/ops/readonly_query.py` :282・:289 が psycopg2.connect を別の名前に入れてから呼ぶ（25本目）。DB ユーザーは ai_reader で、アプリの salesanchor_app・jarvis の接続ではない。
- 同期の engine を作る関数 `_get_sync_engine` は11ファイルに1つずつ別々にあり、共通の関数は無い。
- `backend/app/database.py` は celery-worker・celery-beat・discord-gateway でも import されるので、そこでの接続も「salesanchor_backend」と名乗る。名前があっても、どのコンテナかが分からない。
- backend・celery-worker・celery-beat・discord-gateway の4つは同じ backend のビルドで動く（`docker-compose.yml` :63・:215・:310・:354）。役割を区別する環境変数は今は無い。
- celery-worker・celery-beat・discord-gateway は本番反映の `docker compose up`（`.github/workflows/deploy.yml` :466）で起動し、compose の environment が効く。backend は `scripts/blue-green-cutover.sh` の docker run で起動し、渡るのは .env のキー（:81-84）と :98-99 の2つだけ。compose の environment は backend に効かない。
- 今のアプリの名前を読んでいるのは `scripts/smoke_test_post_deploy.sh` :125・:133（salesanchor_backend で salesanchor_app と jarvis の接続を区別する確認 [7a]・[7b]）と `scripts/test_rollback_simulation.sh` :91 だけ（backend/app と docs 以外を git grep。監視の設定に該当0件）。
- 名前で接続を切る仕組みもある。`scripts/deploy-db-orphan-cleanup.sh` :50 は、`scripts/lib/db-app-names.sh` の salesanchor_migration・salesanchor_backup_deploy の接続を pg_terminate_backend で切る（段2）。アプリの名前がこれと重なると、本番反映のたびにアプリの接続が切られる。
- smoke [7b]（`scripts/smoke_test_post_deploy.sh` :131-137）は「jarvis で salesanchor_backend と名乗る接続が0本」を見る。今は worker・gateway も salesanchor_backend と名乗るので、それらが jarvis でつないでも見つかる。
- asyncpg は application_name を接続の引数で受けず、server_settings で渡す（ADR-115 :9、`backend/app/database.py` :11-13）。asyncpg 0.31.0 は環境変数 PGAPPNAME を読まない（公式の connect_utils.py）。psycopg2 は libpq の接続の引数 application_name を渡せる（PostgreSQL 16 文書 libpq の接続の引数の節）。
- 本番 DB の設定（10/30 reader 鍵の道）: log_lock_waits=off、log_connections=off、log_line_prefix は時刻と番号だけ、ログは stderr。
- ロック待ちのログ（PostgreSQL 16 proc.c）は deadlock_timeout（既定1秒）を過ぎてから出て、握っている接続の番号（pid）を書く。名前は書かない。

### 17-2. 変更前 → 変更後（4a）
| 項目 | 変更前 | 変更後 |
|---|---|---|
| 名前の正本 | 5か所に文字列で直書き | backend/app の中に新しいモジュールを1つ置き、名前の表を持たせる（置き場所は実装で既存の共通モジュールの並びに合わせ、本節を直す） |
| コンテナの区別 | なし | 環境変数 SA_PROCESS_ROLE。celery-worker=worker・celery-beat=beat・discord-gateway=gateway を `docker-compose.yml` の environment に書く。backend には書かない（無いときの既定が backend）。.env と blue-green の台本は変えない |
| 名前の形 | ばらばら | `salesanchor_<役割>_<道>`。ただし今の5つの名前は保つ（下の表） |
| 名前の無い接続の作り方 | 19行 | 0行（CI の試験で守る） |

名前の表（正本に置く。全部63文字以内・すべて salesanchor_ で始まる・重複なし）:
| 役割 | 道 | 名前 | 使う DB ユーザー | 理由 |
|---|---|---|---|---|
| backend | main（database.py の engine） | salesanchor_backend | アプリ用（DATABASE_URL） | 今のまま。smoke [7a]・[7b] が読む |
| backend | admin（database.py の admin_engine） | salesanchor_admin_ops | 管理用（ADMIN_DATABASE_URL） | 今のまま |
| worker・beat・gateway | main・admin | salesanchor_<役割>_main・salesanchor_<役割>_admin | main はアプリ用・admin は管理用 | backend と取り違えないため |
| worker | distribute・extraction_recovery・viewer_cache | 今の3つの名前のまま | 実装で各行の URL を表に書く | celery-worker だけで動く |
| どの役割でも | 上以外の道（同期の engine・buyback・email・gemini の2つ・product master・priority・reaction・data_deletion） | salesanchor_<役割>_<道> | 実装で各行の URL を表に書く（data_deletion は管理用） | 道の名はファイル名を基にし、実装で表に全部書く |

- 名前の正本は2か所になる。アプリの名前はこの Python の表、本番反映の控え・移行の名前は `scripts/lib/db-app-names.sh`（段2）。理由: シェルの台本は Python を読めず、アプリはシェルの lib を読めない。2つの重なりは C4-2 が止める（片付けのスクリプトがアプリの接続を切らないため）。

- 名前を返す関数は1つにする。あわせて、同期用の `{"application_name": 名前}` と、SQLAlchemy の非同期用の `{"server_settings": {"application_name": 名前}}` を返す小さな関数を置く。各行は自分で文字列を書かず、これを呼ぶ。asyncpg.create_pool には server_settings で渡す。
- 役割は、名前の関数が呼ばれたときに環境変数から読む（import のときに固定しない。試験で役割を変えて確かめられるように）。
- smoke [7b] を広げる（A3）: 「jarvis で salesanchor_backend と名乗る接続が0本」を「jarvis で表の main の4つ（salesanchor_backend・salesanchor_worker_main・salesanchor_beat_main・salesanchor_gateway_main）のどれかと名乗る接続が0本」に変える（`scripts/smoke_test_post_deploy.sh` :131-137）。今と同じく worker・gateway の main の接続も見張る。台本の4つの名前が表の main の名前と同じことを C4-2 で確かめる。[7a] は今のまま（backend の接続を数える）。
- SA_PROCESS_ROLE が表に無い値のときは、止めずに役割を unknown として名前を作る（salesanchor_unknown_<道>）。綴りの誤りで本番の worker が起動しなくなるのを避ける。誤りは CI の試験 C4-3 で捕まえる。
- 接続の他の設定（prepared_statement_cache_size など）は変えない。connect_args が既にある行は、名前の分を足すだけにする。

### 17-3. 試験（PR の CI。`.github/workflows/test.yml` で流れる backend の pytest に足す）
- C4-1 名前の無い接続を作らない: backend/app の全 .py を ast で読み、create_engine・create_async_engine・psycopg2.connect・asyncpg.connect・asyncpg.create_pool の呼び出し（別の名前に入れてから呼ぶ形も含める。例 `backend/app/ops/readonly_query.py` :282・:289）を全部見つける。前例 `backend/tests/test_no_exception_text_in_http_detail.py` :62-68。合格とする形は次の3つだけ（A1）:
  (1) 呼び出しの引数に、名前の正本の関数の呼び出しを直接書く（engine は connect_args=、psycopg2.connect は application_name=、create_pool は server_settings=）。
  (2) 呼び出しの引数の `**辞書` の中に、(1) と同じキーで正本の関数の呼び出しがある。
  (3) (1)・(2) のキーに渡す値が、同じファイルの中で正本の関数の呼び出しを代入した変数（または、そのキーを持つ辞書の変数。`backend/app/database.py` :13-15・:24-33 の `_connect_args` を `_engine_kwargs` に入れて `**` で渡す形）。
  これ以外は赤。対象外は許可リストに理由付きで書く: `backend/app/ops/readonly_query.py` :282・:289（DB ユーザーが ai_reader で、K4-5 が数えるアプリの接続ではない。A2）。見つけた呼び出しの数が「24＋許可リストの数」より少なければ赤にする（試験が何も見ずに緑になるのを防ぐ）。
- C4-2 名前の表: 全部の名前が63文字以内・salesanchor_ で始まる・重複なし。backend の main が salesanchor_backend であること（smoke [7a] の前提）。`scripts/lib/db-app-names.sh` の3つの名前と重ならないこと（A4）。`scripts/smoke_test_post_deploy.sh` の [7b] に書く4つの名前が、表の main の4つと同じであること（A3）。
- C4-3 役割の書き忘れ: `docker-compose.yml` を YAML として読み、build が ./backend のサービスのうち backend 以外は、environment の SA_PROCESS_ROLE が表の役割の1つであること。backend には SA_PROCESS_ROLE が無いこと。environment は今は `- KEY=value` の並びの形で書かれている。試験は並びの形と `KEY: value` の辞書の形の両方を読む。YAML を読む道具（PyYAML）は直接の依存ではなく uvicorn[standard] 経由で入っている。依存は足さず、この経路を使う（入らなくなったら C4-3 が import で赤になって気づける）。
- C4-4 実際に名乗る: 試験の PostgreSQL（`.github/workflows/test.yml` の pytest の job :114-242。test.yml の変更は要らない）につなぎ、同期・非同期・create_pool の各1本で `SELECT current_setting('application_name')` が表の名前と一致する。SA_PROCESS_ROLE を worker にしたときと無いときの2通り。CI（環境変数 GITHUB_ACTIONS が true）で DB が無いときは skip にせず赤にする。手元で DB なしに流すときは skip にする。
- 赤の実演（実装 PR で1回、結果を PR に貼る）: (1) 同期の1行から名前を外すと C4-1 が赤 (2) `backend/app/database.py` の `_connect_args` から名前を外すと C4-1 が赤（`**` で渡す形を本当に見ているか） (3) 別の名前に入れた psycopg2.connect を許可リストの外に1つ足すと C4-1 が赤 (4) celery-worker の SA_PROCESS_ROLE を消すと C4-3 が赤 (5) 非同期用の関数が server_settings を返さない形にすると C4-4 が赤。

### 17-4. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K4-1 名前の無い接続の作り方が0 | C4-1 PASS |
| K4-2 名前の表と役割の書き方が決まりに合う | C4-2・C4-3 PASS |
| K4-3 接続が表の名前を名乗る | C4-4 PASS |
| K4-4 試験が壊れた実装を捕まえる | 赤の実演（17-3） |
| K4-5 本番: 本番反映の後、時刻を変えた3回（反映の直後・1時間後・翌日 02:10 JST の毎日のアイコン取得の作業の最中）に、reader 鍵の道で pg_stat_activity を見て、usename が salesanchor_app・jarvis の接続のうち `coalesce(application_name,'')=''` のものが0本。名前ごとの本数を記録する | reader 鍵の道の記録 |
| K4-6 本番: 本番反映の確認 smoke の [7a]・[7b] が PASS のまま（[7b] は広げた形） | 本番反映ログ |
- reader の権限では、ほかのユーザーの接続の application_name と usename は見え、state・backend_type・client_addr は空になる（PostgreSQL 16 pgstatfuncs.c :335-351・:619-635、審査で照合）。よって数え方は usename で絞る形にする。実際に引けるかは、実装 PR の前に1回 reader 鍵の道で確かめる（まだ確かめていない）。
- 3回目の時刻にアイコン取得の作業が終わっていたら（作業の長さはまだ確かめていない）、その回は作業の接続を見られない。そのときは翌日の 02:00〜02:05 JST に見直し、それでも見られなければ、C4-4 で代える。
- K4-5 で jarvis の名前の無い接続が残ったら、4b に進まずに止める。アプリの外（手で流す道具・監視など）の接続とみなして出どころを調べる。reader では接続元の場所が見えないので、prod1 の ss と docker ps（読み取りだけ）で調べる。候補は postgres-exporter（`docker-compose.exporters.yml` :30-34。本番で動いているかはまだ確かめていない）。記録は社内のみ。

### 17-5. 選ばなかった案
- 名前を環境変数 PGAPPNAME だけで渡す: asyncpg が読まない（17-1）。アプリの接続の大半は asyncpg。
- 役割を .env に足して backend にも書く: .env は秘密の値を置くファイルで、本番反映の台本が作る。役割は秘密ではないので、変える場所を増やさない。backend は既定で足りる。
- 役割をホスト名やコマンドの行から自動で判断する: blue-green の backend はホスト名がコンテナ id で、判断の決まりが見えにくい。compose に1行書く方が読める。
- 同期の engine を1つの共通関数にまとめ直す: 11ファイルの作りを変えることになり、名前を付ける目的より広い。今回は名前だけを足す。
- 今の5つの名前も新しい形にそろえる: smoke [7] が salesanchor_backend を読む。変える利点が小さく、壊す危険がある。

### 17-6. 弊害・トレードオフ
- worker・beat・gateway の main の接続の名前が salesanchor_backend から変わる。smoke [7a] は backend の接続だけを数えることになる（backend は salesanchor_backend のまま名乗るので、0 にはならない）。[7b] は表の main の4つに広げるので、見張りの範囲は今と同じ。
- smoke の台本（本番 scripts）を変えるので、本番反映の確認の段の動きが変わる。名前の一覧がずれると [7b] が見落とすので、C4-2 で表と照らす。
- 新しいコンテナを足すときに SA_PROCESS_ROLE を書き忘れると、backend と名乗る。C4-3 が `docker-compose.yml` のサービスを見て止める。compose の外で docker run するコンテナは対象外。
- アプリの動きは変わらない（接続の名前だけ）。接続の数・取引の長さも変わらない。

### 17-7. 範囲外（記録のみ）
- scripts の手で流す道具（create_engine などが54行）と backend/scripts・backend/tcg_migration/scripts（6行）。本番反映からは run_py（名前付き、`scripts/migration_py_entry.py` :40）だけが呼ばれる。手で流すときの名前は、K4-5 で jarvis の名前の無い接続が残ったときに考える。
- 名前の無い jarvis の接続の候補（K4-5 で残ったときに調べる）: postgres-exporter（`docker-compose.exporters.yml` :30-34。本番で動いているかはまだ確かめていない）と、手で流す道具。
- 移行の入口（`scripts/migration_py_entry.py` :40）は setdefault で名前を足すので、アプリの engine を import して使う移行は、アプリの名前を名乗る。今登録されている26本の移行では起きない（審査で照合）。起きると段2の片付けの対象から外れるので、新しい Python の移行を足すときに見る（人手で守る）。
- idle_in_transaction_session_timeout（取引を開いたまま放置した接続を切る）: アプリの動きを変えるので、段4に入れない。4a で名前が分かった後に、別の段として考える。
- 毎日 02:00 JST のアイコン取得の作業（`backend/app/tasks/avatar.py`）は、取引を開いたまま外の API を1件ずつ呼ぶ。10/29 06:42Z の時刻とは重ならない。K4-5 の3回目でこの作業の接続を見る。

### 17-8. 4b の概要（4a の本番測定の後に詳細設計）
- 目的: 次にロック待ちが起きたら、待った接続と握った接続の名前が、本番の DB のログに残るようにする。
- 候補: log_lock_waits=on。log_line_prefix に %a（application_name）を足す。log_line_prefix は設定ファイルかサーバーの起動の引数でしか変えられない（PostgreSQL 16 文書）ので、ALTER SYSTEM と設定の読み直し（pg_reload_conf）で行う案を軸にする。DB の再起動はしない。
- 握った側はログに番号（pid）だけが出る。番号から名前を引くには、log_connections を on にして接続の始まりの行（名前を含む）を残す必要がある。接続は約55本/10分なので、増えるログは1日あたり数 MB の見込み（今のログは約0.5MB/日、Loki で30日保持）。要否と量は 4b の設計で実測から決める。
- 移行のロック待ちの上限（1秒）は deadlock_timeout（1秒）と同じなので、移行自身の待ちのログは出ないことがある。アプリの読み取りの待ち（上限なし）は1秒後に必ず出る。4b ではこの差を受け入れ基準に書く。
- ALTER SYSTEM は DB のデータの場所の postgresql.auto.conf に書くので、リポジトリに残らない。設定の正本をどこに置くか（移行のファイル・手順書と、本番の値を読む確認）を 4b で決める。
- 決める点: 実行の道（移行のファイルか、手順書に沿った1回の操作か）。ADR-1003 の例外7種に当たるかを 4b の設計で確かめる。

### 17-9. 戻し方・計画・継続
- 戻し方（4a）: 実装 PR を revert して main にマージ。次の本番反映から今の名前に戻る。DB は変えない。
- 計画: (1) 本節の Architect 審査（新しく起動） (2) 設計 PR をマージ (3) 段2の K2-5〜K2-7 がそろった後、実装の前に reader 鍵の道で usename・application_name の列を1回引けることを確かめる。そのあと Sonnet が 4a を実装・CI・赤の実演・ADR-1037 の追記（名前の正本の場所と役割の環境変数） (4) reviewer（opus、新しく起動） (5) 委任 GO で本番へ（backend・`docker-compose.yml`・`scripts/smoke_test_post_deploy.sh` を含む。移行・DROP・秘密の値は無い） (6) K4-5・K4-6 (7) 4b の詳細設計。
- 継続: 名前の正本は2か所ある。アプリの接続の名前は 4a で置く新しいモジュール（場所は実装 PR で本節に書く）。本番反映の控え・移行の名前は `scripts/lib/db-app-names.sh`（段2）。分ける理由は、シェルの台本は Python を読めず、アプリはシェルの lib を読めないから（17-2）。2つが重ならないことは C4-2 が守る。守り手: backend の pytest（C4-1〜C4-4、実装 PR で足す）と `.github/workflows/backup-script-test.yml`（C1〜C9）。
