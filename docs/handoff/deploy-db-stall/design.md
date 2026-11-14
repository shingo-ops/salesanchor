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

## 18. 段6 詳細設計 — 試しの道具の取引を読んだらすぐ閉じる／移行の前に開いたままの取引を点検してから入れ替える（第4.2版）
状態（第4.2版の追補、2026-11-10）: 便2 は #5345 で本番反映済み（2026-11-10 10:09Z 合流・run 42796774375 success、K18-4 の1回目）。18-14（点検の設定をサーバー側の環境で変えられないようにする）は設計審査済み（3回目 APPROVE、軽3件は第3.1稿で取り込み済み）。PO の決定 2026-11-10「1」。18-14 は #5371 で本番反映済み（2026-11-10 13:03:36Z 合流・merge commit 348ede8bb・run 42821073480 success）。その run の点検の段の記録: deploy.yml の新しい2行（`unset $(env | sed -n ...)` と `env -u BASH_ENV bash "$TMP"`）が流れ、start の行は `poll=5s streak=3 limit=600s xact>5s long_active>60s`（既定の値）。1回目の数え count=1、2〜4回目 count=0 で `clean: no open transactions for 3 samples in a row`、`waited=16`。移行の段は 13:06:07Z〜13:07:59Z で成功。K18-10 合格（記録 /tmp/CC報告ファイル/deploy-precheck/deploy-5371-log.txt）。K18-4 は合格（5回、3回以上）: 点検の段と移行の段がともに success で、結論が clean・待った秒数あり・FAKE の行0の本番反映は、run 42796774375（便2を出した回、10:10:39Z waited=11）・42805760255（11:24:06Z waited=11）・42805522437（11:31:20Z waited=11）・42808889592（11:38:42Z waited=11）・42821073480（#5371、13:04:32Z waited=16）。各 run の `gh run view --log` で確かめた（2026-11-11）。残り: K18-5（便2の後30日）。
状態（第4.1版、2026-11-10）: 設計審査済み（第4版の審査 APPROVE、2026-11-10 クラウドの Architect＝Opus。中4・軽3 は第4.1版で反映、18-13）。実装未着手（便2 は未実装、道具の設計の追補 C5・C6 も未実装）。第4版を書く前の状態: 第3.2版を受けたクラウドの Architect の審査（2026-11-10、origin/main 96a63df05 で照合）は REVISE（重2・中2・軽1）。第4版で全件を直した（18-12）。便1 は別の設計 docs/handoff/replay-tx-release/design.md（以下「道具の設計」）に置き換えた。道具の設計は PR #5340 で実装済みで、2026-11-10 04:28 JST に本番反映済み。便2（点検の段）は実装未着手。
第3.2版までの状態: 設計審査済み（第3版 APPROVE、2026-11-10。推奨5件は第3.1版で反映。第3.1版のマージ前審査も APPROVE で、推奨6件は第3.2版で反映）。第1版の審査（クラウドの Architect＝Opus、2026-11-10）は REVISE（必須2・推奨5）。第2版で全件を直した。第2版の審査も REVISE（必須1・推奨4）で、第3版で全件を直した（18-11）。PO の選択: 2026-11-10「1、2」（(1) 試しの道具が読み終えたらすぐ表を放す (2) 移行の前に、動いている試しと開いたままの取引を確かめ、待つか知らせる）。本番に出す GO は委任（opus-delegation）に基づく Claude Opus 発行。

### 18-1. 事実（2026-11-10 調べ。行番号は origin/main 96a63df05）
本番反映の記録（`gh run view --log`、2026-10-29 14:00Z 以降の deploy.yml の実行 447 回）を全部読んだ。生の記録は社内の作業メモにある。
| 数えたもの | 回数 |
|---|---|
| 移行の段が動いた回 | 34 |
| そのうちロック待ちが1回以上あった回 | 12 |
| そのうちロック待ちの上限（40/40 前後）に達して移行が失敗した回 | 6（11/7 1回・11/9 5回） |

ロック待ちのあった12回の握り手（`scripts/run_all_migrations.sh` :66 の log_lock_holders の行。列は pid・ユーザー・application_name・状態・待ちの種類・取引の秒数・最後の文・握った表）:
| 握り手 | 状態 | 取引の秒数 | 出た回 | 移行の結果 |
|---|---|---|---|---|
| 名前なし（salesanchor_app） | idle in transaction・最後の文 SELECT・8〜9表 | 1〜96秒 | 11/2 1回、11/9 6回 | 11/2 は成功、11/9 の5回は失敗 |
| salesanchor_backend | idle in transaction・最後の文 SET・users 1表（ほかに SELECT で5〜6表の行が2つ） | 1〜29秒 | 10/31・11/4・11/7・11/9 | 11/7 は失敗、ほかは成功 |
| salesanchor_celery_viewer_cache・salesanchor_celery_distribute | active | 1〜6秒 | 10/30・11/2・11/6 | すべて成功 |

- 11/9 の名前なしの握り手は、別セッションの試し condwords-replay（`docker compose run` で `backend/app/tools/v102_replay_diff.py` を流す）だった。接続元の場所と、最後の文と、読んだ9表で突き合わせた（記録は社内の作業メモ。11/9 22:3x JST の裏取り）。11/2 の名前なしの握り手はまだ確かめていない。
- 移行が失敗した6回とも、新しいコードへの入れ替え（「Deploy to VPS」の段）は移行の前に済んでいた。`.github/workflows/deploy.yml` の段の順は「空き容量 :161 → 控え :197 → 入れ替え :235 → … → 移行 :765」。11/5 は、新しいアプリが列の無いまま約20分動いた（段5の設計の根拠と同じ）。
- 失敗の回では `if: failure()` の段（`.github/workflows/deploy.yml` :1261 の /design/ の緊急遮断、:1310 の「Deployment Failure Notification」。この段は echo と exit 1 だけで、Discord には送らない）と `if: always()` の段（:869 の最後の確認）も動く。11/9 の失敗の回の記録に、/design/ の遮断の段の行が186行あった。最後の確認は、アプリが応答すれば戻しはしない（:869〜:905）。
- 前例: 「Check free disk space」（`.github/workflows/deploy.yml` :161〜:185）は、控えと入れ替えの前に止まる点検。`exit 1` で止まる。
- サーバーの作業場所（/home/ubuntu/salesanchor）を最新の main にするのは、入れ替えの段の中の `git fetch origin main`・`git reset --hard origin/main`（`.github/workflows/deploy.yml` :258〜:259）。それより前の段（空き容量・控え）が動く時点では、作業場所は1つ前の本番反映のまま。控えの段は、台本が無い古い作業場所を `if [ -f scripts/deploy-db-orphan-cleanup.sh ]; … else … skipped (old checkout)` で避けている（:213）。
- 試しの道具の取引（`backend/app/tools/`。下の3本の記述は直す前の姿。道具の設計の PR #5340 で直り、2026-11-10 04:28 JST に本番反映。今の姿は 18-12 の事実の欄）:
  - `backend/app/tools/v102_replay_diff.py` :77〜:97 replay_post は、9表を読んだあと、同じ取引のまま run_v102_pipeline（:96）で計算する。取引を閉じるのは :120 の finally（計算の後）。:103 のマスタの読み込みも、閉じずに最初の投稿へ進む。
  - `backend/app/tools/prompt_ab_recompute.py` :81〜:91 _recompute_row は、読んだあと同じ取引のまま _v102_row_fields で計算する。:94〜:131 recompute は、失敗した行のとき（:111）しか取引を閉じない。成功が続くと、全部の行が1つの取引になる。
  - `backend/app/tools/prompt_ab.py` :537 で文脈を読んだあと、取引を閉じずに Gemini を呼ぶ（:548〜:559）。:597〜:602 で台帳に書いて commit し、すぐ fetch_ledger_totals で読む。この読み取りの取引は、次の回の Gemini の呼び出しの間も開いたまま。:490・:495・:514〜:516 の読み込みも閉じずに繰り返しへ入る。
  - `backend/app/tools/reextract_v6_with_v102.py` は、投稿ごとに取引を閉じている（前の調べ。:456）。直さない。
- 道具の接続は `backend/app/tasks/tcg_extraction.py` :94 の `_engine`（名前なし）から :97 の _get_sync_session で作る。
- 計算の関数に渡すマスタは、ORM の品物ではなく普通の値（`backend/app/services/line_analysis_v102_svc.py` :217〜:241。このファイルに session.query と .scalars() は0件）。取引を閉じても、計算の途中で読み直しは起きない。
- `docker compose run` で作った一時コンテナには、ラベル com.docker.compose.oneoff=True が付く（Context7 の docker/compose 資料で確かめた）。`.github/workflows/deploy.yml` :480・:940 と `scripts/blue-green-cutover.sh` :107 は、このラベルで一時コンテナを消さないようにしている。`scripts/ops/reextract-v6-loop.sh` :41 も一時コンテナで動く。名前の頭（fhd-・llmcmp-・condwords- など）の決まりの正本は無い。
- 移行の段の点検は jarvis で `docker exec astro-webapp-postgres-1 psql` を流す（`scripts/run_all_migrations.sh` の PSQL・POSTGRES）。同じ道で pg_stat_activity の state と xact_start を全部見られる。reader 鍵の道では、ほかのユーザーの接続の state が空になる（§17-4）。

### 18-2. 目的と成功の条件
目的: 試しが本番で動いていても、移行を含む本番反映がロック待ちで失敗しない。失敗しそうなときは、コードを入れ替える前に止まる。

| 成功の条件 | 判定 |
|---|---|
| K18-1 道具3本: 計算と Gemini の呼び出しの間、取引が開いていない | 第4版で道具の設計に移した。判定は道具の設計の K1〜K5（試験は K4・K5、本番の測定は P4）だけで行い、本節では数えない（正本を1つにする） |
| K18-2 点検の台本: 開いたままの取引があれば待ち、上限を過ぎたら止まる。無ければ通る | 試験 P1〜P8（P4a〜P4c を含む）PASS（18-4）。P4a〜P4c・P7・P8 は必須の pytest、P1〜P3・P5・P6 は backup-script-test（必須ではない）で流す |
| K18-3 試験が壊れた実装を捕まえる | 赤の実演（18-4） |
| K18-4 本番: 便2の後、移行の段が動く本番反映（backend・scripts などを変えた回。`.github/workflows/deploy.yml` :38〜:43）3回で、各回が「点検の段の結論の行が clean で、待った秒数が記録に出る」か「止まって、止めた理由の握り手が記録に出る」のどちらか。止まった回も3回に数える。便2を出す回そのものも数える（台本は origin/main から読むため、18-3 の動き0）。3回とも記録に「FAKE」の行が無い | 本番反映の記録 |
| K18-5 本番: 便2の後30日、新しいコードに入れ替えた後に移行がロック待ちの上限で失敗した回が0（基準: 10/29〜11/9 の34回中6回）。失敗があれば、2つの軸で分けて数える。(a) 握り手の取引の始まりが点検の段の終わりより前か後か（後なら「点検の後に来た握り手」＝18-6 の隙） (b) 握り手の持ち主（log_lock_holders の行のユーザーと application_name だけで分ける。この行は公開の記録に出るため接続元の場所を出さない作り＝`scripts/run_all_migrations.sh` :65 の注記。新しい列は足さない）: 「道具の疑い」＝ユーザー salesanchor_app で application_name が空（11/9 の道具の接続と同じ形。段4 で道具に名前が付いたら、その名前に置き換える）／「アプリ」＝application_name が salesanchor_backend か salesanchor_celery_ で始まる／「その他」＝それ以外。持ち主ごとの回数を表で出す。アプリが握り手の回が1回でもあれば、18-7 の範囲外の件（アプリが SET の後に取引を開いたまま置く）を別の設計に起こすかを PO に聞く | 本番反映の記録を同じ数え方で数える。点検の段の終わりの時刻は、その段の記録の最後の行の時刻 |
| K18-6（第4版で廃止） | 道具の取引の減り方は、道具の設計の K1（P4 の前後の比べ。基準は道具の設計 §11 の P1: 193回中183回が idle in transaction、1回の待ちの最長 49.44 秒）で測る。同じことを2か所で測ると合否が割れうるため、本節の K18-6 は数えない |

### 18-3. 変更前 → 変更後
便1（試しの道具）: 第4版で道具の設計（docs/handoff/replay-tx-release/design.md の C1〜C4、追補 C5・C6）に置き換えた。第3.2版にあった「道具に直に session.rollback() を書く」形は採らない（道具の設計は共通の関数 `release_before_compute` を通す決まり）。道具の変更前後・試験・測定の正本は道具の設計だけにする。本節には書かない。

便2（本番反映。危険なパス）:
| 場所 | 変更前 | 変更後 |
|---|---|---|
| 本番の台本 | なし | 新しい台本 scripts/deploy-db-precheck.sh（下の動き） |
| `.github/workflows/deploy.yml` | 空き容量の点検 → 控え → 入れ替え | 空き容量の点検 → 新しい段「Check open DB transactions before deploy」→ 控え → 入れ替え。条件は移行の段（`.github/workflows/deploy.yml` :767「Run database migrations」）と文字列まで同じ `if: ${{ success() && steps.gate.outputs.migrations == 'true' }}` |
| `.github/workflows/backup-script-test.yml` | C1〜C10 | 新しい試験の台本 scripts/tests/test-deploy-db-precheck.sh（DB が要る P1〜P3・P5・P6）を足す。`on.pull_request.paths` と `on.push.paths`（:9〜:30。今は2つの一覧が同じ）の両方に scripts/deploy-db-precheck.sh と scripts/tests/test-deploy-db-precheck.sh の2行を足す |
| 新しい試験 backend/tests/ops/test_deploy_precheck_wiring.py | なし | DB が要らない P4a〜P4c・P7・P8 を pytest で書く（必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で毎回走る。`backend/pyproject.toml` :54 の testpaths は tests なので tests/ops も入る）。P4a〜P4c は subprocess で `bash scripts/deploy-db-precheck.sh` を `DB_PRECHECK_FAKE_COUNTS` 付きで流す。リポジトリの根は前例 `backend/tests/ops/test_nginx_case_api_guard.py` :15 と同じ `Path(__file__).resolve().parents[3]` で求める |
| `.github/workflows/test.yml` の detect-changes の backend の filters（:42〜:50） | backend/**・migrations/**・scripts/**・pyproject.toml・docker-compose.yml・docker-compose.test.yml・.github/workflows/test.yml（:44〜:50 の7行） | `.github/workflows/deploy.yml` を足す（deploy.yml だけを変える PR でも P7・P8 が必須チェックの中で走る。scripts/deploy-db-precheck.sh は scripts/** で既に入る） |

新しい段の中身（ssh の script。作業場所は書き換えない）:
0. `set -e` の下で、次の順に固定する。(a) `cd /home/ubuntu/salesanchor` (b) `git fetch origin main`（失敗なら exit 1） (c) `git rev-parse --verify origin/main`（失敗なら exit 1） (d) `if ! git cat-file -e origin/main:scripts/deploy-db-precheck.sh; then echo ">>> [precheck] skipped: script not in origin/main"; exit 0; fi`（`set -e` の下で if で包まないと rc=128 で止まり skipped が出ない。第3版の審査の実測） (e) `TMP=$(mktemp)` と `trap 'rm -f "$TMP"' EXIT` で置き場所を作る (f) `git show origin/main:scripts/deploy-db-precheck.sh > "$TMP"`（失敗なら exit 1） (g) `bash "$TMP"`。決まった名前の /tmp は使わない。台本はそれだけで動き、作業場所の他のファイルを読まない（作業場所は1つ前の版のため）。同時に2回の本番反映は動かない（`.github/workflows/deploy.yml` :14〜:16 の `concurrency: deploy-production`・`cancel-in-progress: false`）。理由: 作業場所は入れ替えの段（:258〜:259）までは1つ前の版のため（18-1）、作業場所の台本を流すと、便2を出す回は台本が無く、その後も毎回1つ前の版が動く。origin/main から読めば、今まさに出す版の台本が動く。入れ替えの段も同じ `git fetch origin main` をするので、新しい通信先・権限は足さない。

新しい台本の動き:
1. jarvis で `docker exec astro-webapp-postgres-1 psql`（statement_timeout 5s・lock_timeout 1s）を流し、pg_stat_activity から「state が idle in transaction（aborted も含む）で、`now() - xact_start` が5秒より長く、`pid <> pg_backend_pid()`、`backend_type = 'client backend'`、`datname = current_database()` の接続」を数える（`pid <> pg_backend_pid()` と `backend_type` は前例 `scripts/run_all_migrations.sh` :66〜:68 と同じ。前例は datname を pg_locks の結合（:68）でだけ使い、state では絞らないので、`datname` と `state` の条件は段6で新しく足す）。台本は作業場所のファイルを読まないので、接続先は台本に直接書く: `psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1`（`scripts/run_all_migrations.sh` :25 と同じ値）。psql の呼び出しは `timeout -k 2 10` で包み、`docker exec -e PGCONNECT_TIMEOUT=5` でつなぐ（つながる前や `docker exec` で止まっても10秒で戻り、`$SECONDS` の判定に戻れる）。timeout で戻った回・psql が失敗した回は数えられなかったとして止まる（exit 1。P6）。
2. 5秒おきに数え、3回続けて0本なら「clean」と書いて通る（最短10秒）。1回でも1本以上なら、続けての数えは0に戻る。投稿ごとに取引を開き直す試しは、1回だけの見た目では0本に見えることがあるため、3回続けて見る。数えるたびに「sample N: count=K streak=S elapsed=E」を1行書く。
3. 待ちの時間は、回数×5秒ではなく bash の `$SECONDS`（実際の経過秒）で測る（psql 1回の時間が足されても上限がずれない）。600秒たっても3回続けて0本にならなければ止まる（exit 1）。止まるときは、握り手の pid・ユーザー・application_name・状態・取引の秒数・握った表の名前と、動いている一時コンテナの名前（`docker ps --filter label=com.docker.compose.oneoff=True`）を書く。文の中身（SQL）と接続元の場所は書かない。偽の数を使う回（5b）は、握り手の記録と `docker ps` を飛ばす（試験の場所で止まり方が変わらないように。exit 1 は変えない）。
4. 止まったら Discord に1通送る（`.github/workflows/deploy.yml` :875 で使っている既存の DISCORD_WEBHOOK_OWNER_PING。新しい秘密の値は足さない）。送るのは VPS の中の台本なので、渡し方は今の Finalize（`.github/workflows/deploy.yml` :874〜:880）と同じにする: 段の `env:` に `ROLLBACK_DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}`、`with:` に `envs: ROLLBACK_DISCORD_WEBHOOK`。台本はこの変数が空なら「webhook not set」と書いて送らずに exit 1 を続ける。送信は `curl --max-time 10` とし、送信の失敗は記録に1行書くだけで exit 1 は変えない。文面は「移行の前の点検で止めました。本番は前のままです。止めた理由: 開いたままの取引 N 本（名前: …）。試しが終わってから、この回をやり直してください。」。
5. 待ちの秒数（5・3回・600）と取引の長さ（5秒）は台本の頭に1か所だけ書く（正本）。試験は環境変数で短くして流す。
5b. 試験のためだけに、環境変数 `DB_PRECHECK_FAKE_COUNTS`（例 `0,1,0,0,0`）があれば psql の代わりにその数を順に使う。並びを使い切ったら最後の値を繰り返す（使い切りで止まる形にすると、上限の判定が壊れていても P4b が緑になるため）。この変数を使った回は、最初に「FAKE counts in use」を1行書く。本番の deploy.yml はこの変数を渡さない（P8 で確かめる）。本番の記録に「FAKE」の行が無いことは K18-4 で見る（サーバー側の環境に変数が残っていた場合を捕まえる）。
6. 試しを止める・接続を切ることはしない（PO の選択「待つか知らせる」）。
7. 第4版で足す（記録だけ。止めない）: 毎回の数えの最後に、同じ絞り込み（`pid <> pg_backend_pid()`・`backend_type`・`datname`）で「state が active で `now() - query_start` が60秒より長い文」の本数を「info: long active statements=N」と1行書く。数には入れず、通る・止まるの判定は変えない。理由: 18-1 の active の握り手は1〜6秒で、移行はすべて成功した（数えて止めると、18-10 の S3 の注意のとおり点検が通らなくなる）。一方で、長い active の文が移行を止めた回があれば K18-5 で見分けたい。偽の数の回（5b）はこの行を飛ばす。
- ssh の段の command_timeout は 12m にする（待ち600秒＋最後の1回の psql（timeout 10秒）＋握り手の記録＋Discord の送信＋fetch の余裕。`$SECONDS` で測るので、待ちは600秒を大きく超えない）。
- 最後に「precheck finished at <UTC 時刻> waited=<秒>」を1行書く。移行の段の始まりの時刻との差が、点検の後の隙（18-6）の長さになる。

### 18-4. 試験
便1: 試験は道具の設計の K4・K5（試験ファイル backend/tests/test_v102_replay_diff.py・test_prompt_ab_recompute.py・test_prompt_ab.py・test_tx_guard.py は #5340 で作成済み）と追補の C5・C6 の試験だけ。第3.2版の T1〜T3 は道具の設計の K4 に移した（T3 の「2回目の Gemini の呼び出しでも取引なし」は道具の設計の K4 に足した）。本節では試験を作らない（同じ試験ファイルを2つの設計が作る形をやめる）。

便2 の試験の置き場所:
| 試験 | 置き場所 | 必須チェックか |
|---|---|---|
| P4a〜P4c・P7・P8（DB が要らない） | backend/tests/ops/test_deploy_precheck_wiring.py（pytest） | 必須（「pytest (SQLite + PostgreSQL RLS)」。`.github/workflows/test.yml` :9〜:12・:262〜:263） |
| P1〜P3・P5・P6（本物の DB が要る） | scripts/tests/test-deploy-db-precheck.sh（`.github/workflows/backup-script-test.yml` の新しい job） | 必須ではない（`.github/workflows/backup-script-test.yml` :6 の注記）。赤でもマージは止まらない。この隙は 18-9 に書く |

P1〜P3・P5・P6 の job は入れ物の名前を本番と同じ astro-webapp-postgres-1 にする（前例 `scripts/tests/test-deploy-orphan-cleanup.sh`）:
- P1 何も無い → 3回続けて0本で通る（exit 0）・「clean」の行が出る。
- P2 6秒以上 idle in transaction の接続が1本ある → 上限（試験では短く）で止まる（exit 1）・握り手の application_name と表の名前が出る・SQL の中身は出ない。
- P3 待っている間に握り手が取引を閉じる → 通る。
- P4 3回続けての数え（DB を使わず `DB_PRECHECK_FAKE_COUNTS` で決まった数を渡す。間隔は0秒）:
  - P4a `0,1,0,0,0` → exit 0。「clean」は5回目の数えの後に出る（1回目の0では通らない。記録の sample 行が5行）。
  - P4b 並び `1`（使い切ったら最後の値を繰り返すので、ずっと1本）・間隔1秒・上限3秒 → exit 1。「上限で止まった」の行（止めた理由の行）が出て、台本が書いた最後の sample 行の elapsed が3以上（外の時計では見ない。`$SECONDS` は整数秒のため）。試験の台本の中で `timeout 30 bash …` として流し、rc=124 なら FAIL。
  - P4c 並び `0,1,0,0,0` で「FAKE counts in use」の行が1行出る。
- P5 active の長い文だけ → 通る（数えない）。第4版: 61秒以上 active の文が1本あるとき「info: long active statements=1」の行が出る（試験では60秒を環境変数で短くする。正本は台本の頭の1か所）。
- P6 DB につながらない → 止まる（exit 1。黙って通らない）。
- P7 `.github/workflows/deploy.yml` を YAML として読み、新しい段が控えの段と入れ替えの段より前にあり、`if:` の文字列が移行の段（:767）の `if:` と完全に同じ（前後の空白を除いて文字列で比べる。移行の段の `if:` を名前「Run database migrations」で探して読み、値を試験に書き写さない）で、script に `git show origin/main:scripts/deploy-db-precheck.sh`・skipped の分岐・`mktemp` があり、作業場所の台本を流す形（`bash scripts/deploy-db-precheck.sh`）が無いこと。段の `env:` に `ROLLBACK_DISCORD_WEBHOOK` が DISCORD_WEBHOOK_OWNER_PING から渡され、`envs:` に `ROLLBACK_DISCORD_WEBHOOK` があること。
- P8 `.github/workflows/deploy.yml` のどこにも `DB_PRECHECK_FAKE_COUNTS` が無いこと。
- 赤の実演（便2の PR で1回、結果を PR に貼る）: (1) 数える state の条件を消すと P5 が赤（active も数えてしまう）、`'active'` に変えると P2 が赤 (2) 3回続けての数えを1回にすると P4a が赤（1回目の0で通ってしまう） (3) 新しい段を入れ替えの段の後ろへ動かすと P7 が赤 (4) 台本を origin/main からでなく作業場所から読む形にすると P7 が赤（origin/main から読む行を残したまま作業場所の台本も流す形も赤） (5) 台本から上限（`$SECONDS` が600を超えたら止める）の判定を外すと P4b が赤（試験の時間切れ30秒で落ちる形にする）。

### 18-5. 選ばなかった案
- 一時コンテナ（oneoff=True）が1つでも動いていたら止める: 投稿ごとに取引を閉じる正しい道具（`scripts/ops/reextract-v6-loop.sh`）まで止める。止めたいのは「取引を開いたまま表を握る」ことで、コンテナの有無ではない。コンテナの名前は止めた理由の記録にだけ使う。
- 名前の頭（condwords- など）で試しを見分ける: 正本が無く、新しい試しの名前で漏れる。
- 握り手の接続を切る（pg_terminate_backend）: 試しの結果を壊す。アプリの接続も切りうる。PO の選択は「待つか知らせる」。
- 取引を開いたまま放置した接続を DB が自動で切る設定（idle_in_transaction_session_timeout）を、DB 全体（postgresql.conf）やアプリの接続に入れる案: アプリの動きを変える。§17-7 と同じく段6に入れない。試しの道具の接続にだけ入れることは採用済み（道具の設計の C4・C5。道具の処理の中だけで効き、アプリの接続には効かない）。
- 道具の接続に1文の時間の上限（statement_timeout）も置く案: 第4版では入れない。理由: (1) 握り手として記録に出た道具の接続はすべて idle in transaction で、active の長い文は1回も出ていない（18-1・道具の設計 §11 の写し193回のうち active は10回で、その文の経過はどれも0.49秒以下、10回とも次の写しは idle in transaction。2026-11-10 に P1 の生の写しを数え直した） (2) 文の長さの測定が無いまま上限を決めると、正しい長い読み取りを切りうる。点検の段で「長い active の文」の本数を記録する（18-3 の動き7）ので、30日で1回でもそれが握り手として移行を止めたら、測った値を根拠に入れ直す。
- 移行を入れ替えの前に動かす: 段5（migration-runner-redesign）で扱う。段6は、その前でも効く小さな止め方。
- 待たずにすぐ止める: アプリの短い握り（1〜29秒）でも止まり、本番反映が無駄に止まる。

### 18-6. 弊害・トレードオフ
- 移行の段が動く本番反映（backend・scripts・docker-compose.yml・deploy.yml などを変えた回。`.github/workflows/deploy.yml` :38〜:43。10/29〜11/9 で 447 回中 34 回）が、最短10秒、最長600秒遅くなる。それ以外の回は変わらない。
- アプリ（salesanchor_backend）が SET の後に取引を開いたまま 29 秒まで置くことがある（18-1）。点検はそれが閉じるのを待つので、その分だけ遅れる。このアプリ側の握りそのものは段6では直さない（範囲外。ADR-1070 と段4で扱う）。点検の後にアプリが握った回は K18-5 の (b) で「アプリ」として数え、1回でもあれば PO に聞く。
- 点検は idle in transaction だけを数える。長い active の文が移行を止める形は、点検では止められない（記録だけ。18-3 の動き7）。
- 止まったときは、ほかの失敗と同じく /design/ の緊急遮断（`.github/workflows/deploy.yml` :1261）と最後の確認（:869）が動く。今の「空き容量で止まる」と同じ動きで、本番のアプリは前のまま。/design/ は次の本番反映の「Setup design-site htpasswd」（:125）で戻る。
- 試しが600秒より長く表を握り続けると、本番反映は止まる。試しの持ち主が試しを止めるか、試しが終わってからやり直す。止まったことは Discord に出る。
- 点検の台本は、移行の段と同じ jarvis の道を使う。新しい鍵・新しい権限は足さない。
- 点検の後に来た握り手は見えない（隙）。点検の段の後、移行の段（:765）の前に、控え（command_timeout 10m、:205）・入れ替え・ほかの段が入る。この間に始まった試しが、移行の時まで取引を開いたまま表を握ると、今と同じくロック待ちの上限（ADR-1037）で失敗しうる。便1でこの型の試しの握りは短くなる。隙の長さは毎回「precheck finished at」と移行の段の始まりの時刻の差で記録に残り、K18-5 で「点検の後に来た握り手」を分けて数える。根本の直し（移行を入れ替えの前に動かす）は段5で扱う。

### 18-7. 範囲外（記録のみ）
- アプリの salesanchor_backend が SET の後に取引を開いたまま置く件（10/31・11/4・11/7・11/9。11/7 は移行の失敗の原因）。
- 11/2 の名前なしの握り手の出どころ。
- `scripts/accuracy/llm_compare/fhd_snapshot.py` など scripts/ の下の試しの道具。わざと1つの写しで読む作りで、計算の待ちが無い（道具の設計 §2）。点検の段は持ち主に関係なく開いたままの取引を数えるので、これらが握っても本番反映の前に見つかる。
- 道具の接続の名前（application_name）。正本は段4 の名前の表（§17-2）だけ。道具の名前は段4 の実装のときに表へ足す（道具の設計 §9）。名前が付くまで、K18-5 の (b) は「ユーザー salesanchor_app で名前が空」を道具の疑いとして数える。
- `backend/app/tools/` の新しい道具の守りは、道具の設計の C6（共通の関数を使わない道具を pytest で赤にする）に置いた。

### 18-8. 戻し方・計画
- 第4版の計画（下の第3.2版の計画を置き換える）: (1) 第4版と道具の設計の追補をクラウドの Architect（新しく起動）で審査 (2) 設計 PR → reviewer（opus）→ マージ (3) PO に結果を伝える（実装を始める前） (4) クラウドの Sonnet が道具の設計の追補（C5・C6・K4 の足し）を実装 → reviewer（opus）→ マージ → 本番反映（道具は一時コンテナで動くので、次に道具を流す回から効く） (5) クラウドの Sonnet が便2 を実装・試験・赤の実演、ADR-1037 に「移行の前の点検」を追記 → reviewer（opus）→ PR 本文に GO 記録（委任に基づく Claude Opus 発行。deploy.yml を含む危険な PR）→ マージ → 本番反映 → K18-4 (6) 便2の後30日で K18-5。(4) と (5) は触るファイルが重ならない（(4) は backend/app/tools と試験、(5) は scripts・workflows・backend/tests/ops）が、変更は一度に1つにするため (4) の本番反映の後に (5) を始める。
- 戻し方: 便1・便2とも PR を revert して main にマージ。便2は次の本番反映から点検の段が無くなる。DB は変えない。
- 重なり（2026-11-10 02:16 JST に確かめた事実）: 別の作業の PR #5333（docs/handoff/replay-tx-release/design.md、PO 承認は設計の用意まで・実装は未承認）が、便1と同じ道具3本の直しを設計している。同じ時刻に、本番で一時の入れ物 replaytx-base（134投稿の流し直し）が動いていた（`docker ps --filter label=com.docker.compose.oneoff=True`）。便1をどちらの設計で作るかは PO が決める。それまで便1と K18-6 の基準値は止め、便2（点検の段。PR #5333 には無い）を先に進める。（第4版: PO は 2026-11-10「1」で #5333 の道具の設計で作ると決め、#5340 で本番反映済み。K18-6 は廃止）便2は便1が無くても単独で効く（握り手が誰でも数える）。
- 第3.2版の計画（第4版の計画で置き換え済み。記録として残す）: (1) 本節の審査（クラウドで新しく起動） (2) 設計 PR をマージ (3) Sonnet（クラウド）が便2を実装・試験・赤の実演、ADR-1037 に「移行の前の点検」を追記 (4) reviewer（opus）→ PR 本文に GO 記録（委任に基づく Claude Opus 発行）→ マージ → 本番反映 → K18-4 (5) 便1をどちらの設計で作るかの PO の判断 (6) 便1の前に K18-6 の基準値を取る (7) 便1を実装・試験・赤の実演 → reviewer（opus）→ マージ → 本番反映 → K18-6 (8) 便2の後30日で K18-5。

### 18-9. 継続（維持の仕組み）
- 第4版: 点検の段が消えたり、入れ替えの後ろへ動いたり、作業場所の古い台本を読む形に戻ったり、偽の数の変数が deploy.yml に入ったりしたら、P7・P8 が赤になる。P7・P8 は必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で走り、赤ならマージできない（`.github/workflows/test.yml` :9〜:12・:262〜:263。deploy.yml を detect-changes の filters に足すので、deploy.yml だけを変える PR でも走る）。3回続けての数えと上限の判定を壊すと P4a〜P4c が同じ必須チェックで赤になる。
- 必須でない所（正直に書く）: 本物の DB が要る P1〜P3・P5・P6 は `.github/workflows/backup-script-test.yml` で走り、必須チェックではない（:6 の注記）。数える条件（state・秒数）を壊す変更は、この job が赤になってもマージは止まらない。必須に上げるのは Ruleset の変更で PO だけができる操作なので、本設計では上げない。代わりに、scripts/deploy-db-precheck.sh を変える PR では reviewer（opus）がこの job の結果を確かめる（ADR-1029 のマージ前の審査）。
- 台本を直したときは、その版が出る本番反映の回から効く（origin/main から読むため）。
- 待ちの秒数・取引の長さ・長い active の文の秒数の正本は、新しい台本の頭の1か所。
- 道具3本が読んだまま計算や Gemini を呼ぶ形に戻ったら、道具の設計の K4 の試験が赤になる（必須の pytest）。DB を使う道具が `set_idle_tx_limit(` を呼んでいない、または `backend/app/tools/` の外から app.tools を読み込んだら、道具の設計 §14 の C6' の試験が赤になる（必須の pytest）。
- 新しい試しの道具は、点検の段が本番反映の前に必ず見つける（道具の名前に関係なく、開いたままの取引を数える）。
- 止まった回の記録は、本番反映の記録と Discord に残る。K18-5 は 30 日後に同じ数え方（18-1）で数え直す。

### 18-10. 外部の事例
- PostgreSQL 16 の文書（pg_stat_activity の state の idle in transaction の説明、xact_start の説明）を判定の根拠にする。数え方の前例は本リポジトリの `scripts/run_all_migrations.sh` :66。
- ほかの会社の本番反映の事例（移行の前に開いたままの取引を待つ仕組み）は、この設計の正しさの根拠にしない。判定は本リポジトリの本番の記録（18-1）と試験（18-4）だけで行う。
- 第4版で読んだ外の事例（2026-11-10、Opus が本文を全部読んだ。方向が合うことの裏付けで、成功の証明ではない）:
  | 事例 | いつ・どこ | 数値 | この設計との関係 |
  |---|---|---|---|
  | F1 LLM Gateway の停止（llmgateway.io の 2026-10-20 の事故報告） | 2026-10-19、AI の中継サービス | 7時間超の読み取りの後ろで列を足す移行が鍵を待ち、約48分停止 | 直しに「読み取りの時間の上限」「移行の前の点検（長い取引があれば流さず握り手の名前を出す）」「接続ごとの上限と名前」。便1・便2・段4 と同じ方向。効果の数値はまだ無い |
  | F2 GoCardless（gocardless.com の zero-downtime-postgres-migrations-the-hard-parts、2024-06 更新） | 決済会社の API | 長い読み取りと移行が重なり API が約15秒停止（写しでは数百ミリ秒） | 長い取引をなくす＝便1 |
  | F3 GoCardless（同社の a-little-help、2024-06 更新） | 同上 | 数値なし | 時間をずらす運用を人の決まりだけで数か月続け「重く、作る速さを妨げた」。機械の止め役が要る理由 |
  | F4 Percona（idle_session_timeout の記事、2023-12-29） | 一般の勧め | 数値なし | 切断の設定は全体でなく接続の持ち主ごとに。道具の接続だけに置く C4・C5 の理由 |
  | S1 GoCardless の移行の上限 | 同上 | 鍵待ち750ミリ秒の上限を約2か月、「何度か停止を防いだ」（回数なし） | ADR-1037 と同じ形 |
  | S3 postgres.ai（2021-09-23） | 手元の試し | 上限50ミリ秒・送り直しで12回目に成功 | 「鍵が0になるまで待つ」点検は短い読み取りが絶えない DB では通らない、点検は長い取引に絞れ。便2が5秒より長い idle in transaction だけを数え、active を数えない理由（18-3 の動き7） |
  - 見つからなかったもの: 接続ごとの上限を入れて止まりが何件から何件に減ったという数値、時間をずらす決まりを機械で強制して効いた数値。成功の判定は K18-4・K18-5 の実測で行う。

### 18-11. 審査の記録
- 第1版（HEAD 3e7879586）: クラウドの Architect（Opus、2026-11-10、読むだけ）→ REVISE。引用した行（deploy.yml :125〜:1310、道具3本、backup-script-test.yml）は origin/main 96a63df05 と一致。
  - 必須1 点検の段は入れ替え（:258〜:259 の fetch・reset）より前なので、作業場所の台本は1つ前の版。便2を出す回は台本が無い → 18-3 の動き0（origin/main から読む・無ければ skipped）、P7・赤の実演(4)、K18-4 に反映。
  - 必須2 P4 の実 DB の握り手（1秒の取引）は5秒を超えず、3回続けての数えを試していない → P4 を `DB_PRECHECK_FAKE_COUNTS` の固い○×（P4a・P4b）に、P8 を追加。
  - 推奨3 点検の後に来た握り手の隙 → 18-6・K18-5・「precheck finished at」の行。
  - 推奨4 待ちを回数×5秒で数えると上限がずれる → `$SECONDS`。
  - 推奨5 数える範囲 → `pg_backend_pid()`・`backend_type`・`datname` で絞る。
  - 推奨6 K18-6 の判定の数 → 60回中6回以下かつ基準値の半分以下、基準値30回未満なら止まる。reader 鍵で見えるかを先に確かめる。
  - 推奨7 :1310 は Discord に送らない → 18-1 の書き方を直した。
- 第2版（HEAD 3a421a9f4）: クラウドの Architect（Opus、2026-11-10、読むだけ）→ REVISE（必須1・推奨4）。1回目の7件は○（必須2 は下の必須1 に回した）。入れ替えの段も `origin/main` に合わせる（:258〜:259。`github.sha` ではない）ので、点検の台本と入れ替え後の版の基準は同じ、と確認された。ADR-1003 の例外7種には当たらない。
  - 必須1 偽の数の並びを使い切ったときの動きが無く、P4b の判定が決まらない → 最後の値を繰り返す（5b）、P4b を並び `1`・間隔1秒・上限3秒に、赤(5) を追加。
  - 推奨2 Discord の webhook の渡し方 → 動き4 に Finalize と同じ `env:`・`envs:` を明記し、P7 で確かめる。
  - 推奨3 /tmp の決まった名前・順番 → 動き0 を `mktemp`・`trap`、rev-parse → cat-file → show の順に固定。
  - 推奨4 つながる前や docker exec で止まると上限の判定に戻れない → psql を `timeout 10` で包む。
  - 推奨5 サーバー側の環境に偽の数の変数が残る → 「FAKE counts in use」の行、P4c、K18-4 で FAKE の行が0。
- 第3版（HEAD 611a646b9）: クラウドの Architect（Opus、2026-11-10、読むだけ）→ APPROVE（必須0・推奨5）。2回目の5件はすべて○。写しで set -e・trap・timeout・`$SECONDS` を実測（if で包まない cat-file は rc=128、trap は rc=1 を保ち一時ファイルを消す、並び1・間隔1秒・上限3秒は3回とも「sample 4 elapsed=3」で止まり実時間3.01秒、上限の判定を外すと timeout 30 で rc=124）。ADR-1003 の例外7種（ADR-1003:35〜:41）に当たらない。
  - 推奨1 skipped の書き方を if で包む形に明記 → 動き0(d)。
  - 推奨2 `PGCONNECT_TIMEOUT=5`・`timeout -k 2 10` → 動き1。
  - 推奨3 P4b は台本の elapsed の行で判定・`timeout 30` は試験の台本の中 → P4b。
  - 推奨4 赤(1) は state の条件を消すと P5、`'active'` に変えると P2 → 赤の実演(1)。
  - 推奨5 偽の数の回は握り手の記録と docker ps を飛ばす・`curl --max-time` → 動き3・4。
- 第3.1版: 上の推奨5件を反映（審査の合否は変わらない形の明記だけ）。
- 第3.1版のマージ前審査（HEAD cb223e416、reviewer＝Opus、手元で新規起動、2026-11-10）→ APPROVE（必須0・推奨6）。引用行は origin/main 96a63df05 と一致（:214 を除く）。ADR-1003 の例外7種に当たらない。
  - 推奨1 old checkout の分岐は :213（:214 は backup.sh）→ 18-1 を直した。
  - 推奨2 前例は datname を pg_locks の結合でだけ使い state で絞らない → 動き1 で前例と同じ所・新しく足す所を書き分けた。
  - 推奨3 台本は作業場所を読まないので接続先を直書き → 動き1 に `-U jarvis -d jarvis_db -v ON_ERROR_STOP=1`。
  - 推奨4 rollback の位置が引数の式の中で曖昧・新しい試験ファイルの名前 → 便1 の変更前後と backend/tests/test_v102_replay_diff.py。
  - 推奨5 K18-4 で止まった回を3回に数えるか → 数えると明記。
  - 推奨6 「移行のある本番反映」は実態と合わない（条件は backend・scripts なども含む。:38〜:43）→ K18-4・18-6 の言い方を直した。
- K18-6 の見え方の確認（2026-11-10 02:01〜02:04 JST、reader 鍵の道、読むだけ）: ほかのユーザーの接続の usename・application_name は見える。state・xact_start は空（null）。pg_locks の pid・relation・mode は見え、pg_class で extraction_items（public と tenant_001）の名前も引ける。K18-6 は「名前なしの salesanchor_app の接続が extraction_items を握っていた回」を pg_locks と pg_stat_activity の結合で数えるので、この道で測れる。state は使わない。

### 18-12. 第4版の改訂（2026-11-10。第3.2版の審査 REVISE の直し）
審査: クラウドの Architect（Opus、2026-11-10、読むだけ、origin/main 96a63df05 で照合）→ REVISE（重2・中2・軽1）。「時間をずらす新しい仕組みは要らない」は、重の2件を直す条件で正しいと判定された。

第4版を書いた時点の事実（origin/main 11838e9d0）:
- 道具の設計（PR #5333）は 2026-11-09T18:51Z にマージ。その実装 PR #5340（release/replay-tx-impl）は 2026-11-09T19:27:59Z にマージ、本番反映は 19:28Z（2026-11-10 04:28 JST）。第3.2版の記録（#5336、2026-11-10T00:37Z マージ）より前に本番に入っていた。
- 共通の関数 `backend/app/tools/_tx_guard.py`: `release_before_compute`（:19。rollback）と `set_idle_tx_limit`（:23。SET → commit → SHOW → rollback → ログ `[tx_guard] idle_in_transaction_session_timeout=`）。
- 呼び出し: `backend/app/tools/v102_replay_diff.py` :100・:108・:110・:126（失敗の後に置き直し）、`backend/app/tools/prompt_ab_recompute.py` :89・:99・:101・:116（同）、`backend/app/tools/prompt_ab.py` :485（上限）・:547（Gemini の前）。
- 道具の接続は `backend/app/tasks/tcg_extraction.py` :94 の `_engine = create_engine(_DB_URL, echo=False)`。接続ごとの設定（connect_args・connect の受け手）は無い。
- 便2 は未実装: origin/main に scripts/deploy-db-precheck.sh は無く、`.github/workflows/deploy.yml` に点検の段は無い。
- `.github/workflows/test.yml` :42〜:50 の filters に deploy.yml は無い。`.github/workflows/backup-script-test.yml` :6 は必須チェックではないと書く。

| 指摘 | 中身 | 第4版の直し |
|---|---|---|
| 1 重 | 上限の SET は最初の接続にだけ効く。接続が作り直されると上限が無い | 道具の設計の C5（接続ごとに SET する受け手）と K5 の足し（作り直した接続でも30秒）。失敗の後に置き直す形（道具の設計 §12-5、v102_replay_diff.py :126・prompt_ab_recompute.py :116）は審査のときに読まれた版より後に入っていた。残る穴は「失敗を経ずに接続が作り直された場合」で、C5 で塞ぐ |
| 2 重 | 守りの仕組みが走るだけで止めない | P4a〜P4c・P7・P8 を必須の pytest（backend/tests/ops/test_deploy_precheck_wiring.py）へ、deploy.yml を test.yml の filters へ（18-3・18-4・18-9）。共通の関数を使わない道具を赤にする試験＝道具の設計の C6。P1〜P3・P5・P6 は必須ではないまま残ることを 18-9 に書いた |
| 3 中 | 本節と道具の設計の食い違い（全体の切断設定の外し方の範囲・直に rollback・同じ試験ファイル・名前の置き場） | 便1 を道具の設計に置き換え（18-3）、18-5 の範囲を「DB 全体とアプリの接続」に、T1〜T3 を道具の設計の K4 へ（18-4）、名前は段4 の表だけ（18-7）、K18-6 を廃止（18-2） |
| 4 中 | 残る穴（長い active の文・fhd_snapshot・アプリの握り） | K18-5 に持ち主の分け方 (b)、点検の段に長い active の文の記録（18-3 の動き7・P5）、statement_timeout は入れない理由（18-5）、scripts/ の道具は範囲外の理由（18-7） |
| 5 軽 | 道具の設計の受入条件のあいまいさ | 道具の設計の §13 で直した（K1 の測り方・K2・P2・K4・C3） |

### 18-13. 第4版の審査と第4.1版の改訂（2026-11-10）
審査: クラウドの Architect（Opus、2026-11-10 01:38Z 終了、読むだけ、審査対象 f21f8c43f、origin/main b960a1937 で照合）→ **APPROVE**。前回の5件はすべて実物と合う形で直ったと判定。新しい指摘は中4・軽3 で、作り直しは要らず実装カードに足せば足りる、とされた。全文の写しは Opus の手元の記録（/tmp/CC報告ファイル/deploy-lock-1109/rev2/architect-rev2-1110.md）。

第4.1版を書いた時点の事実（Opus が origin/main c5bd38863 で読み直した）: 移行の段の `if:` は `.github/workflows/deploy.yml` :767。同じ文字列が :805（Post-deploy smoke tests）にもあるので、P7 は段の名前で移行の段を探す。`.github/workflows/backup-script-test.yml` の paths は :9〜:30。`.github/workflows/test.yml` の backend の filters は :44〜:50 の7行。

| 指摘 | 中身 | 第4.1版の直し |
|---|---|---|
| 中1 | 道具の設計の C6 は見る範囲が狭い（下のフォルダ・別の接続の取り方・import だけで呼ばない形がすり抜ける） | 道具の設計 §14 の C6' |
| 中2 | C5 を足すと MagicMock の session を使う今の試験が赤になる見込み | 道具の設計 §14 の C5'（登録は bind が Engine のときだけ・今の試験の直しをカードに書く） |
| 中3 | C5 の試験がプールの返却・作り直しを通らない | 道具の設計 §14 の K5'（本物の PostgreSQL で返却後と invalidate 後に 30s） |
| 中4 | アプリに漏れない守りが今の grep だけ | 道具の設計 §14 の C6'（tools の外から app.tools を読み込んだら赤） |
| 軽1 | P7 の条件の比べ方があいまい | 18-3 の deploy.yml の行と P7 を「移行の段の `if:` と文字列で完全に同じ」に直した |
| 軽2 | backup-script-test.yml の paths に足す物が書かれていない | 18-3 に2行・2か所を書いた |
| 軽3 | test.yml の filters の書き方が実物と違う | 18-3 を実物の7行どおりに直した |

マージ前の審査（reviewer＝opus、手元で新しく起動、2026-11-10、PR #5348）: APPROVE（必須0・推奨5）。推奨1・2 は道具の設計 §14 に、推奨3 は本節の見出し・18-9・台帳・道具の設計 §6 K5 と §13 C5 に反映した。推奨4（`.github/workflows/test.yml` :17〜:26 の push の paths に deploy.yml が無い）は範囲外とする。理由: main への直の push は Branch Protection で止められていて、main に入る道は PR だけ。PR では pytest の job が paths なしで必ず走り、detect-changes の filters に deploy.yml を足すので P7・P8 が流れる（18-3）。推奨5（PR の確かめ guard-authoring/evaluation の赤）は、枝が main より古く、確かめの最初の「main がこの枝の祖先か」で止まったもの（`scripts/run-guard-evaluation.js` :25 の merge-base --is-ancestor）。main を取り込んで直した。

### 18-14. 第4.2版の追補（2026-11-10）— 点検の設定をサーバー側の環境で変えられないようにする

PO の決定: 2026-11-10「1」（抜け道をふさぎ、古い記述も一緒に直す）。便2（#5345）の本番反映の後、マージ前の審査（reviewer＝opus）の MINOR から Opus が調べて PO に出した。

#### 18-14-1. 事実（origin/main 931a3c443 で読んだ）
- 台本の設定5つは環境変数があればそれを使う: `scripts/deploy-db-precheck.sh` :27 `POLL_SEC="${DB_PRECHECK_POLL_SEC:-5}"`・:28 `CLEAN_STREAK="${DB_PRECHECK_STREAK:-3}"`・:29 `WAIT_LIMIT_SEC="${DB_PRECHECK_LIMIT_SEC:-600}"`・:30 `XACT_SEC="${DB_PRECHECK_XACT_SEC:-5}"`・:31 `LONG_ACTIVE_SEC="${DB_PRECHECK_LONG_ACTIVE_SEC:-60}"`。偽の数は :39 `FAKE="${DB_PRECHECK_FAKE_COUNTS:-}"`。
- 通る判定は :168 `if [ "${STREAK}" -ge "${CLEAN_STREAK}" ]`。STREAK は1回目の数えの後 0 か 1（:161〜:165）。CLEAN_STREAK が 0 なら、1回目に開いたままの取引が何本あっても `0 -ge 0` で clean と書いて exit 0 になる（台本を読んで確かめた。実行での確かめは試験 P4d で行う）。
- `XACT_SEC` は SQL の文字列に直に入る（:50 `interval '${XACT_SEC} seconds'`、:112 も同じ）。大きな値（例 99999）にすると何も数えず通る。`LONG_ACTIVE_SEC` も SQL に入る（:67）。
- 本番反映が失敗したときの段「Deployment Failure Notification」（`.github/workflows/deploy.yml` :1346〜:1351）は echo して exit 1 するだけで、Discord には送らない。知らせは GitHub の失敗の記録（実行の赤）だけ。
- bash は、殻の外から渡された `BASH_ENV` が指すファイルを、台本の前に読む。審査（クラウドの Architect、2026-11-10）で、足す1行の後に `bash 台本` と流すと、そのファイルで入れた `DB_PRECHECK_STREAK=0` が台本に届くことを実際に流して確かめた。`env -u BASH_ENV bash 台本` なら届かない（同じ審査で実測）。
- `.github/workflows/backup-script-test.yml` の db-precheck の job（:83〜:104）は、注記「P7 が deploy.yml を読むのに使う」（:92）・setup-python（:93）・pyyaml（:97〜:98）を持つ。P7 は必須の pytest に移り、`scripts/tests/test-deploy-db-precheck.sh` は python も yaml も使わない（中で `python`・`yaml` を探して、頭の説明の :8 も含めて0件）。
- 偽の数の変数がサーバー側の環境にあると、DB を見ずにその数で判定する（:80〜:89）。値が `0` なら3回目で clean になる。
- deploy.yml の点検の段（`.github/workflows/deploy.yml` :195〜:222）は、これらの変数を渡さない（`envs: ROLLBACK_DISCORD_WEBHOOK` だけ）。ただし、台本は ssh の先の環境をそのまま受け継ぐ（:222 `bash "$TMP"`）。サーバー側の環境に `DB_PRECHECK_` の変数があれば効く。
- 今の守り: P8（`backend/tests/ops/test_deploy_precheck_wiring.py` :164〜:165）は deploy.yml の文字列に偽の数の変数名が無いことだけを見る。サーバー側の環境は見ない。K18-4 は本番の記録の「FAKE」の行で後から見るだけで、止めない。
- 本番の1回目（run 42796774375、2026-11-10 10:10Z）の記録は `start: poll=5s streak=3 limit=600s xact>5s` で、FAKE の行は無かった。今サーバー側に変数が入っている形跡は無い。LONG_ACTIVE_SEC は start の行に出ていない。
- 試験が環境変数で変える設定は POLL・LIMIT・LONG_ACTIVE と偽の数だけ（`scripts/tests/test-deploy-db-precheck.sh` :69〜:220、`backend/tests/ops/test_deploy_precheck_wiring.py` :58・:75・:92）。STREAK と XACT は試験で変えていない。

#### 18-14-2. 目的と成功の条件
目的: 本番の点検は、いつも台本の頭に書いた値（5秒・3回・600秒・5秒・60秒）で動く。サーバー側の環境に何が残っていても、点検を素通りしない。

| 成功の条件 | 判定 |
|---|---|
| K18-7 サーバー側の環境に `DB_PRECHECK_` で始まる変数や `BASH_ENV` があっても、点検の段は台本を流す前にそれを全部外す | 必須の pytest P9 が PASS（下の 18-14-4） |
| K18-8 台本は設定が整数でなければ、または続けて0本の回数が1未満なら、数える前に止まる（exit 1・「invalid setting」の行・clean の行なし・sample の行なし） | 必須の pytest P4d・P4e が PASS |
| K18-9 試験の説明の古い記述が無くなる | `.github/workflows/backup-script-test.yml` と ADR-1037 に「P1〜P8」「P1-P8」が0件。`.github/workflows/backup-script-test.yml` の db-precheck の job に、注記「P7 が deploy.yml を読むのに使う」・setup-python・pyyaml が0件（新しい :100 の注記の「P7〜P9」は数えない） |
| K18-10 本番: 本節の版が出た後の、移行の段が動く本番反映で、start の行が `poll=5s streak=3 limit=600s xact>5s long_active>60s` で、FAKE の行が無い | 本番反映の記録。本節の版が出た後、移行の段が動く本番反映の最初の1回で見る（K18-4 の残りの回と同じ記録） |

#### 18-14-3. 変更前 → 変更後
deploy.yml の変更（表の中では区切り記号を逃がしているので、正本はこのかたまり）。1行足し、台本を流す行を1行置き換える:

```sh
unset $(env | sed -n 's/^\(DB_PRECHECK_[A-Za-z0-9_]*\)=.*/\1/p')
env -u BASH_ENV bash "$TMP"
```

| 場所 | 変更前 | 変更後 |
|---|---|---|
| `.github/workflows/deploy.yml` 点検の段の script（:222） | `bash "$TMP"` | 上のかたまりの2行にする。名前を並べず頭の文字で外すので、台本に新しい設定を足しても書き足しは要らない。sed・unset・`env -u` は ssh の先の殻が bash でも dash でも動く（審査で bash・dash とも `set -e` の下で終了コード0、値に `=` や改行を含む変数も全部消えた。変数が1つも無いときも終了コード0）。ssh の先の殻が何かは appleboy/ssh-action の公式の説明に書かれていない（未確認）ため、どちらでも動く形にする |
| `scripts/deploy-db-precheck.sh` finish の定義（:44〜:46）の直後、start の行（:145）より前 | 確かめなし | 5つの設定（POLL_SEC・CLEAN_STREAK・WAIT_LIMIT_SEC・XACT_SEC・LONG_ACTIVE_SEC）を、数字だけ（`case ... in '' \| *[!0-9]*)`）か確かめる。外れたら `>>> [precheck] invalid setting <環境変数の名前>=<値> (must be a whole number) - stopping` を1行書き、finish を書いて exit 1。次に CLEAN_STREAK が1未満なら `>>> [precheck] invalid setting DB_PRECHECK_STREAK=<値> (must be 1 or more) - stopping` を書き、finish を書いて exit 1。確かめは start の行より前で、DB にはつながない。Discord には送らない。知らせは本番反映の失敗の記録（GitHub の実行の赤）だけになる（18-14-5） |
| `scripts/deploy-db-precheck.sh` start の行（:145） | `start: poll=… streak=… limit=… xact>…` | 後ろに ` long_active>${LONG_ACTIVE_SEC}s` を足す（5つの設定がすべて記録に出る） |
| `scripts/deploy-db-precheck.sh` 頭の説明（:21〜:22） | 「本番の deploy.yml はこの変数を渡さない（試験 P8）」 | 「本番の deploy.yml は台本を流す前に DB_PRECHECK_ で始まる変数を全部外す（試験 P8・P9）」に直す |
| `backend/tests/ops/test_deploy_precheck_wiring.py` | P4a〜P4c・P7・P8 | P4d・P4e・P9 を足す（18-14-4）。頭の説明に P4d・P4e・P9 を足す |
| `.github/workflows/backup-script-test.yml` :100〜:101 | 注記「P1〜P8（design §18-4）」・段の名前「Run test-deploy-db-precheck.sh (P1-P8)」 | 「P1〜P3・P5・P6（design §18-4。P4a〜P4e・P7〜P9 は必須の pytest）」・「Run test-deploy-db-precheck.sh (P1-P3, P5, P6)」。段の名前は必須チェックの名前ではない（必須の確かめは job 単位）ので、変えても必須の確かめの名前は変わらない |
| `.github/workflows/backup-script-test.yml` :92〜:98（db-precheck の job の中だけ） | 注記「P7 が deploy.yml を読むのに使う」・setup-python・Install pyyaml | 3つとも消す（使う試験が無い。18-14-1）。:70〜:75 の別の job の setup-python・pyyaml は触らない |
| `docs/adr/ADR-1037-migration-lock-timeout.md` :94 | 「… の P1〜P8）」 | 「… の P1〜P3・P5・P6。DB が要らない P4a〜P4e・P7〜P9 は必須の pytest `backend/tests/ops/test_deploy_precheck_wiring.py`）。本番の点検の段は台本を流す前に DB_PRECHECK_ で始まる変数を全部外す」 |
| `scripts/tests/test-deploy-db-precheck.sh` :8（頭の説明だけ） | 「P4a〜P4c・P7・P8（DB が要らない）は必須の pytest に移した:」 | 「P4a〜P4e・P7〜P9（DB が要らない）は必須の pytest に移した:」 |

触らない範囲: 数える条件（:49〜:53 の WHERE_SQL）・待ちの数の既定値・握り手の記録・Discord の文面・段の `if:`・段の順番・command_timeout・`scripts/tests/test-deploy-db-precheck.sh` の試験の中身（頭の説明 :8 は表のとおり直す。試験は POLL・LIMIT・LONG_ACTIVE に数字だけを渡しているので、そのまま通る）。偽の数の並びの中身（数字以外が入った場合）は確かめない。数字以外は `-eq` が失敗して続けての数えが0に戻るだけで、通る向きには働かない（:161〜:165）。

#### 18-14-4. 試験（すべて必須の pytest `backend/tests/ops/test_deploy_precheck_wiring.py`）
- P4d `DB_PRECHECK_STREAK=0`・偽の数 `1`・間隔0秒・上限3秒 → exit 1。`invalid setting DB_PRECHECK_STREAK=0 (must be 1 or more)` の行が1行。`] clean:` の行が0行。`sample ` の行が0行。最後の行が `precheck finished at` で始まる。subprocess の時間切れは10秒（確かめを消した赤の実演では、続けての数え1回目で clean を書いて exit 0 になり、終了コードと clean・invalid の行の数で赤になる）。
- P4e 5つの変数それぞれに、値 `abc`・`-1`・`3 4`・`5s` を1つずつ入れる（5×4＝20通り。pytest.mark.parametrize）。偽の数 `0`・間隔0秒・上限3秒（入れる変数が POLL・LIMIT のときはそれだけを壊す）→ exit 1。`invalid setting <その変数の名前>=` で始まり `(must be a whole number)` を含む行が1行。`] clean:` の行が0行。`sample ` の行が0行。最後の行が `precheck finished at` で始まる。subprocess の時間切れは10秒。時間切れになったら、その通りは赤（例外を通す）。
- P9 deploy.yml の点検の段の script を YAML で読む。(a) `unset $(env | sed -n 's/^\(DB_PRECHECK_[A-Za-z0-9_]*\)=.*/\1/p')` の行があり、その後に `env -u BASH_ENV bash "$TMP"` の行がある。`bash "$TMP"` を含む行はこの1行だけ (b) 一時の場所に、python で `os.environ` を JSON で書き出す小さな bash の台本を置き、その場所を `TMP` に入れる。script から `unset ` で始まる行（0本でもよい）と `bash "$TMP"` を含む行を探して読み、書き写さずそのまま並べて（完全一致では探さない。`env -u BASH_ENV ` が消えたときに、行が見つからない例外ではなく、BASH_ENV から変数が入る動きで赤にするため）、`DB_PRECHECK_FAKE_COUNTS=0`・`DB_PRECHECK_STREAK=0`・`DB_PRECHECK_XACT_SEC=99999`・`DB_PRECHECK_NEW_ONE=1`・値に `=` と改行を含む `DB_PRECHECK_ODD`・`BASH_ENV=<存在するファイル>` を入れた環境で、`sh -c` で流す。python の `os.environ` に `DB_PRECHECK_` で始まる名前が0件・`BASH_ENV` が無い・終了コード0（`env` の出力を行で数えない。別の変数の値の改行で誤って赤になるため） (c) 変数が1つも無い環境で同じく流しても終了コード0。行の中身は試験に書き写さず、script から `unset ` で始まる行を探して読む（ただし (a) で中身が上の形と同じことは確かめる）。
- P8 は変えない（deploy.yml に偽の数の変数名が無い。新しい行は名前を書かないので P8 と両立する）。
- 赤の実演（PR に結果を貼る）: (1) deploy.yml の unset の行を消す → P9 が赤 (2) deploy.yml の `env -u BASH_ENV ` を消して `bash "$TMP"` に戻す → P9 が赤 (3) 台本の「1未満なら止める」を消す → P4d が赤 (4) 台本の「数字だけか」の確かめを消す → P4e の20通りがすべて赤（`STREAK=-1` は「1未満なら止める」で止まるが、行に `must be a whole number` が無いので赤）。

#### 18-14-5. 選ばなかった案
- STREAK と XACT を環境変数で変えられない定数にする: 2つの穴はふさげるが、偽の数の変数（試験に要る）は残るので、段で外す仕組みが別に要る。段で外せば全部をまとめてふさげるので、台本の読み込みの形は今のまま（§18-3 の動き5「試験は環境変数で短くして流す」を保つ）。
- 外す変数を名前で並べる（`env -u A -u B …`）: 台本に設定を足したとき書き足しを忘れると穴が開く。名前を並べると P8 とも食い違う。
- `env -i` で環境を空にして流す: docker の呼び出しに要る環境（HOME など）まで消える。何が要るかを本番で確かめていないので採らない。
- 確かめで止まったときに Discord に送る: K18-7 の後は、設定はサーバー側から入らず、台本の頭の値（PR で審査され、P4a〜P4c が通る値）だけになる。確かめで止まるのは試験の中だけで、本番では起きない道なので、知らせの文面を足さない。万一止まっても本番反映は GitHub で赤になり、入れ替えの前で止まる（本番は前の版のまま動く）。
- 書き出した関数（`BASH_FUNC_*`）や、サーバー側の docker・PATH の差し替えも外す: 範囲外。これらは人が意図してサーバーに入れない限り残らず、そこまでできる人は台本を通さずに何でもできる。本節は「試しで入れた変数の消し忘れ」で点検が素通りする道をふさぐことが目的。
- 数字だけでなく値の上限・下限も確かめる（例 XACT_SEC=99999 を止める）: K18-7 の後は値が台本の頭からしか来ないので、範囲の確かめは試験の中の値を縛るだけになる。足さない。

#### 18-14-6. 弊害・戻し方・継続
- 弊害: 試験で設定に数字以外を入れていた場所があれば止まる。今の試験は数字だけ（18-14-1）なので該当しない。サーバー側で意図して設定を変える道は無くなる（変えたいときは台本の頭を直して PR を出す。正本は台本の頭の1か所のまま）。
- 戻し方: PR を revert して main にマージ。台本は origin/main から読むので、次の本番反映から前の形に戻る。DB は変えない。
- 継続: P9 が段の unset の行を、P4d・P4e が台本の確かめを、必須の pytest で毎回見る。deploy.yml だけを変える PR でも走る（`.github/workflows/test.yml` の detect-changes の filters に deploy.yml がある。§18-3）。
- K18-4 の数え方は変えない。本節の版が出た後の回も、3回のうちに数える（点検の判定の形は同じため）。

#### 18-14-7. 外部の事例
不要。理由: 環境変数を外す・整数か確かめるのは本リポジトリの台本の中の直しで、判定は試験（18-14-4）と本番の記録（K18-10）だけで行う。sed・unset の動きは試験 P9 で実際に流して確かめる。

#### 18-14-8. 計画
審査の記録: 1回目（クラウドの Architect、2026-11-10 11:42Z〜11:45Z）は、試しの写しの置き直しで `rm -rf` を見張りに止められ、判定なしで終わった。止まる前の指摘（知らせの段の記述が実物と違う・BASH_ENV の抜け道・行番号のずれ・db-precheck の job の古い注記と使わない段・P9 の数え方・P4e の時間切れ）は本節に取り込んだ（第2稿）。
2回目（クラウドの Architect、2026-11-10 11:51Z〜11:56Z、審査対象 faa5e25e0、origin/main ae8def4d3 で照合）→ **REVISE**（中2・軽5）。写しで deploy.yml の2行は bash・dash とも変数と BASH_ENV が消えて終了コード0、P4a〜P4e・P9 は29件すべて通り、赤の実演4つも赤になった。指摘（K18-9 が新しい注記の「P7〜P9」で必ず×になる・確かめの置き場所が finish の定義より前・P9 (b) が流す行を試験が自分で書いている・P4d の赤の実演の動き・K18-10 の回数・台帳の状態が古い・18-14-1 の「:8 以外」）は第3稿で取り込んだ。台帳のファイルを commit しない、という指摘は採らない（`.gitignore` :67〜:71 が active-work.d の下の .md ファイルを残す決まりで、origin/main に同じ形のファイルが439件ある）。状態の行だけ直した。軽7 の後半は記録の切れで読めていない（3回目の審査で確かめる）。
3回目（クラウドの Architect、2026-11-10 12:04Z〜12:07Z、審査対象 22e158ee0、origin/main d06f150c7 で照合）→ **APPROVE**。2回目の指摘は軽6 を除き直っており、軽6 を採らない理由も正しいと判定（`.gitignore` :67〜:71、origin/main に439件）。写しで pytest 29件が通り、赤の実演4つがすべて赤（(2) は P9 (b) も BASH_ENV から変数が入る動きで赤）。新しい軽3件（P9 (b) の行の探し方・赤の実演(4) で `STREAK=-1` の1通りが緑のまま・`scripts/tests/test-deploy-db-precheck.sh` :8 の古い説明）は第3.1稿で取り込んだ。軽7 の後半は前の記録が無く、同じ内容かは確かめられないとされ、3件目として言い直された。

(1) 本節をクラウドの Architect（新しく起動・読むだけ）で審査 (2) APPROVE の後、同じ枝でクラウドの Sonnet が 18-14-3 を実装し、試験と赤の実演 (3) reviewer（opus・手元で新しく起動）→ PR 本文に GO 記録（POの委任に基づくClaude Opus発行。deploy.yml・scripts を含む）→ マージ → 本番反映 (4) 移行の段が動く本番反映で K18-10 と K18-4 の残りを見る。

## 19. 段7 設計 — 試しと本番反映が重なっても移行が止まらないようにする（第3.5版、2026-11-14）
状態: 第1版・第2版はクラウドの Architect（opus）審査で REVISE、第3版で APPROVE（19-14）。第3.1版で第3版の推奨5件を入れた。第3.1版はマージ前審査で REVISE、第3.2版で直した（19-14）。(c) の1回目の実装（077a2e388）の確かめで、GitHub の呼び出し回数の上限に当たる作りだと分かり、第3.3版で呼び出しを減らす決まり（19-4 の 2b.）を足した（19-14）。
PO の依頼（2026-11-13）: 「試作や本番反映が被っても止まらないようには出来る？」。説明の後の PO の選択は「1」（3つの直し方をまとめて設計し、作って試すのは1つずつにして効果を数えながら進める）。
3つの直し方: (c) 本番反映が止まった回数を毎週機械が数えて知らせる／(a) 済んだ移行は流さない／(b) 試しの道具に長く表を押さえさせない。
番号の (a)〜(c) は PO に説明した順。作る順は 19-3 のとおり (c)→(a)→(b)。

### 19-1. 事実（2026-11-13 調べ。行番号は origin/main 11694eaf6）
- 2026-11-13 の本番反映（run 43372532867）の1回目は、移行の段でロック待ちの上限（40/40）に達して失敗した。2回目で成功した。
  - 1回目の記録で `lock conflict; retry [0-9]` の行は40行、`lock conflict; retry limit reached` は1行（`gh api .../actions/jobs/131711407349/logs` を `grep -a -c` で数えた。記録は社内の作業メモ）。
  - この PR #5491 は試験と docs/handoff だけの変更だった。それでも backend 以下を変えたので移行の段が動き、401段を全部流し直した（`.github/workflows/deploy.yml` :38〜:43 の filters、`scripts/run_all_migrations.sh` に適用済みの記録を読む行は無い）。
- 握り手は、本番に向けて流した試しの道具 `docs/handoff/single-set-category/data/bin3/rejudge_single_set.py`（MODE=dryrun）の接続だった。
  - 握り手は salesanchor_app・application_name 空・idle in transaction。移行の記録に出た5回の取引の始まりが、試しの記録の仕入元の始まりと5回とも1秒以内で一致した（記録は社内の作業メモ）。
  - 道具は仕入元1件を1つの取引で流す（:8 の説明・:171〜:193 の trial）。最長の取引は1169.6秒だった。
  - 道具は lock_timeout だけを確かめ（:30・:204〜:207）、application_name と idle_in_transaction_session_timeout を置かない。
- 移行の前の点検（`scripts/deploy-db-precheck.sh`、§18）は 05:34:03Z に clean で通った。
  - 点検は「idle in transaction かつ取引5秒超」を5秒おきに数え、3回続けて0なら通る（:69〜:73・:186〜:189）。
  - 3回の0は、試しの10.0秒の短い仕入元の間だった。34秒後に128.7秒の取引が始まり、05:35:50Z からの移行と重なった。§18-6 で書いた「点検の後に来た握り手」の隙が本番で起きた。
- 本番反映の一覧（`gh run list`・runs の API）は、各 run の最後の回の結論しか出さない。
  - 11/1 以降で2回目以上の回がある run は6本（43372532867・42805522437・42612168629・42596881194・42331938658・41950091268）。前の回の失敗は一覧に出ない。
  - 回ごとの記録は `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{n}/jobs` で job を引き、`GET .../actions/jobs/{job_id}/logs` で読める（上の1回目で実際に読めた）。記録には文字以外のバイトが混じるので、grep は `-a` が要る（`-a` なしでは数が出なかった）。
- 止まった回の数え（§18 の K18-5）は手作業で、決まった日に自動で数える仕組みは無い（`.github/workflows/` の schedule を持つ18本に該当なし）。
- 毎週の見張りの前例は `.github/workflows/weekly-stale-pr.yml`（cron・workflow_dispatch・`scripts/notify/discord-owner-ping.sh` と secret DISCORD_WEBHOOK_SCHEDULED_REPORT で Discord に送る）。
- 済んだ移行を流さない作り（ADR-1005）は、`docs/handoff/migration-runner-redesign/design.md` §5（第7版、設計審査 APPROVE 2026-10-30）にある。5-0 の前調査（読むだけ）から始まる。5-0 は手つかず。
- アプリの接続に名前を付ける段4a（§17）は、設計審査済みで実装されていない（`git grep SA_PROCESS_ROLE` が設計書の行だけ）。
  - 試しの道具とアプリの抽出の仕事は、同じ名前なしの `_engine` を使う（`backend/app/tasks/tcg_extraction.py` :94・:97）。
- 試しの道具の取引を守る仕組みは `backend/app/tools/_tx_guard.py`（30秒の上限）と、それを呼ばない道具を赤にする試験 `backend/tests/test_tools_tx_guard_required.py`（§18 の C6'）。
  - 試験が見るのは `backend/app/tools/` の下だけ（:11〜:13）。backend の外にある、DB を使う Python の道具は7本: `docs/handoff/s1-rls-stage5/pool_reset_measure.py`、`docs/handoff/single-set-category/data/bin3/ref/rejudge_pika30.py`、`docs/handoff/single-set-category/data/bin3/rejudge_single_set.py`、`scripts/accuracy/condition_words/replay_words.py`、`scripts/accuracy/llm_compare/fhd_snapshot.py`、`scripts/check_priority_scoring_state.py`、`scripts/check_public_tenant_rls.py`（`git grep -lE '_get_sync_session|create_engine\(|psycopg|asyncpg\.connect'`）。
  - このうち `from app.` を読み込んで本番のアプリの入れ物で動く形は4本（rejudge の2本・replay_words・fhd_snapshot）。残り3本は psycopg2 で直接つなぐ（CI 用・使い捨ての DB 用・月次の点検）。
  - 必須の pytest が動くかを決める detect-changes の filters（`.github/workflows/test.yml` :45〜:54）と、push の paths（:20〜:29）に docs/ は無い。docs/ の下に道具を足すだけの PR では、守りの試験が走らない。
- 点検の段が exit 1 で止まる道は3つある: 600秒で0にならない（`scripts/deploy-db-precheck.sh` :199 `STOP:`・:207）、数えられない（:177 `could not count`・:179）、設定の誤り（:55・:57、:62・:64 `invalid setting`）。
- 移行の段は `command_timeout: 10m`（`.github/workflows/deploy.yml` :848）、点検の段は 12m（:205）で切れる。切れたときは台本の文言が出ない。2つの段とも continue-on-error は無い（:195〜:205・:840〜:848）。
- 握り手の行（`scripts/run_all_migrations.sh` :66〜:68）は、ロック待ちの1回目（:95・:125）と上限に達したとき（:104・:134）に出る。形は `>>> [段/全段]   pid | DB ユーザー | application_name | state | 待ち | 取引秒 | 命令 | 握る表`。11/13 の1回目の行は application_name が空だった（作業メモの記録 :3508）。

### 19-2. 目的と成功の条件（KGI）
目的: 試しが本番で動いていても、本番反映が移行のロック待ちで失敗しない。失敗した回は、人が数えなくても毎週知らせが届く。

| 成功の条件 | 判定 |
|---|---|
| KGI-7 移行の段がロック待ちの上限で失敗した回（同じ run の前の回を含む）が、(a)・(b) の本番反映の後の連続4週で毎週0回 | (c) の毎週の数え（4回分の Discord と job の記録）。基準: 10/29〜11/9 は移行の段が動いた34回中6回（§18-1）、11/13 に1回 |
| KGI-7b 点検の段で止まった回も数え、毎週の記録に出る（止まるのは「入れ替えの前に安全に止まった」形で、失敗には数えない。ただし多ければ (b) の続きを考える材料にする） | (c) の毎週の記録 |

### 19-3. 作る順と理由（一度に1つ）
1. (c) 毎週の数え — 先に作る。直す前の基準の数を、後の数と同じ数え方で取るため（測る前に基準値を取る）。本番のアプリは触らない。
2. (a) 済んだ移行は流さない — 次に作る。11/13 のように新しい移行が無い本番反映では、移行の段が表を押さえに行かなくなる。最も効く。設計は migration-runner-redesign §5 のまま進める（本節で書き直さない）。
3. (b) 試しの道具に名前と上限を付け、守りの試験を backend の外へ広げる — 最後に作る。(a) の後も新しい移行がある回は表を押さえるので、そのときの握り手を減らし、試しかアプリかを名前で分けられるようにする。b1 は段4a（§17）を使うので、§17 の前提（段2の K2-5〜K2-7 がそろった後に本番へ）を守る。

各段は、前の段の本番反映の後に (c) の数えを1回以上読んでから始める。

### 19-4. (c) 毎週の数え（詳細）
変更するファイル（実装 PR の全部）:
| 場所 | 変更前 | 変更後 |
|---|---|---|
| scripts/ops/count-deploy-lock-failures.sh（新規） | 無い | 本番反映の記録を回ごとに読み、数を出す台本 |
| .github/workflows/weekly-deploy-lock-count.yml（新規） | 無い | 毎週月曜 01:00 UTC（10:00 JST）と手動で、上の台本を流し、0でなければ Discord に送る |
| backend/tests/ops/test_deploy_lock_count.py（新規） | 無い | 台本と workflow の試験（必須の pytest の中で走る。置き場所は既にある `backend/tests/ops/test_deploy_precheck_wiring.py` と同じ並び） |
| `.github/workflows/test.yml` | filters（:45〜:54）と push の paths（:20〜:29）に新しい workflow が無い | 両方に .github/workflows/weekly-deploy-lock-count.yml を1行ずつ足す |

台本の動き:
1. 引数: `--days N`（既定 7）または `--since YYYY-MM-DD --until YYYY-MM-DD`、試験用に `--from-dir DIR`（API を呼ばずに DIR の記録を読む）。
   - `--from-dir` の形（第3.1版で決めた。API の返事をそのまま置く）: DIR/runs/<UTCの日付>.json（その日の一覧の返事。`total_count` と `workflow_runs` の各 run の `id`・`created_at`・`run_attempt`）、`DIR/attempts/<run id>-<回>.json`（`run_attempt`・`run_started_at`・`status`・`conclusion`）、`DIR/jobs/<run id>-<回>.json`（job の一覧の返事。steps の名前と結論）、`DIR/logs/<job id>.log`（記録の本文）。ファイルが無いものは「引けなかった」として扱う。
   - 台本は、一覧を引いた日（UTC の日付）を全部、出力に1行で出す（`fetched dates: ...`）。`--from-dir` のときも同じ。
2. 数える期間と週の境目（第3版で決めた）:
   - 期間は日本時間の 00:00 から 00:00 まで。`--since A --until B` は「A の 00:00 JST 以上、B の 00:00 JST 未満」。`--days N` は「今日の 00:00 JST から N 日前」〜「今日の 00:00 JST」。毎週月曜 10:00 JST の実行は、前の週の月曜 00:00 JST〜この月曜 00:00 JST を数える。週と週は重ならず、すき間も無い。
   - 回をどの週に入れるかは、その回の始まりの時刻（attempts の API の `run_started_at`）で決める。run を作った時刻ではない。やり直しの回は、やり直した時刻の週に入る（2026-11-13 に run 43372532867 の回1・回2 で `run_started_at` が別々に出ることを確かめた: 05:31:06Z と 05:47:51Z）。
   - run の一覧は、期間の始めの7日前（日本時間の日付で since−7 日）から終わりまでを引く（期間の前に作られ、期間の中でやり直された回を拾うため）。引いた回のうち、`run_started_at` が期間の外の回は数えない（出力にも出さない）。同じ (run id・回) は1回だけ数える。
   - 限界: 作ってから7日より後にやり直した回は数えない。11/1〜11/13 のやり直し6本は、どれも作ってから40分以内にやり直されていた（`gh api .../actions/runs/{id}` の created_at と最後の回の run_started_at、2026-11-13）。この限界は台本の頭の説明と job の要約に書く。
   - 数える時点でまだ終わっていない回（status が completed でない）は「読めなかった」に入れる。
   - run の一覧は1日ずつ引く（`GET .../actions/workflows/deploy.yml/runs?created=D..D&per_page=100` をページを送って全部。D は UTC の日付。引く日は、日本時間の日付で since−7 日から until−1 日までの各日を UTC の日付として並べ、日本時間との差を拾うため、始めを1日前・終わりを1日後に広げる。例: since 11/09・until 11/16 なら、日本時間の 11/02〜11/15 を広げて UTC の 11/01〜11/16 の16日分。第3.2版で決めた）。この API は created などの絞りを付けると1回の検索で1,000件までしか返さない（GitHub REST API の公式資料「List workflow runs for a workflow」、2026-11-13 に Context7 で確かめた）。1日の run は11/12〜11/13 の約22時間で40本なので、1日ずつなら上限に届かない。1日の結果が1,000件に達したら、読めなかったとして扱う（黙って切らない）。広げて引いた日の回も、`run_started_at` が期間の外なら数えない。
2b. 呼び出しを減らす（第3.3版で決めた）:
   - 事実（2026-11-14 に確かめた）: workflow の GITHUB_TOKEN で呼べる REST API は、1つのリポジトリで1時間に1,000回まで（GitHub の公式資料「Rate limits for the REST API」、Context7 で確かめた）。deploy.yml の run は、作られた日（UTC）で 10/21〜10/27 が239本、10/28〜11/14 が644本、11/06〜11/13 が311本、11/9〜11/12 は1日38〜49本（`gh api .../deploy.yml/runs?created=...` の total_count）。
   - 第3.2版の作り（077a2e388）は、引いた全部の回に回の API を1回ずつ呼ぶ。毎週の実行で約600回＋期間の中の job の一覧で約310回＝約900回、基準の数え（K19-4）で約880回＋約640回＝約1,500回になり、上限に近いか超える。超えると 7. のとおり終わりが2になるので、黙って少なく数えることはないが、毎週の数えが毎回失敗しうる。
   - 一覧の各 run には、最後の回の `run_started_at` と `status` が入っている（2026-11-14 に run 43372532867 で確かめた: 一覧の `run_started_at` は 05:47:51Z で、回2の始まりと同じ）。回は順に始まるので、最後の回の始まりが期間の始めより前なら、その run のどの回も期間の外にある。
   - 決まり (i): 一覧の `run_started_at` が期間の始め（since 00:00 JST）より前の run は、回の API も job の API も呼ばずに飛ばす（出力にも出さない）。一覧の `created_at` が期間の終わり（until 00:00 JST）以後の run も同じく飛ばす。
   - 決まり (ii): 最後の回（回の番号＝一覧の `run_attempt`）は、一覧の `run_started_at` と `status` を使い、回の API を呼ばない。回の API は、それより前の回（やり直しの前の回）だけに呼ぶ。
   - 決まり (iii): 一覧に `run_started_at` か `status` が無い run は、第3.2版のとおり回の API で読む（古い返事や作り物でも数えが変わらないように）。
   - 見込み: 毎週の実行は、期間の中の job の一覧（約310回）＋一覧（16回）＋やり直しの前の回（数回）＋記録（移行か点検の段が動いた job だけ、週に十数回）で、約350回。基準の数えは約720回。
3. 各 run について、回 1〜run_attempt を全部見る。各回の job を引き、段の一覧（job の steps）で「Run database migrations」か「Check open DB transactions before deploy」の結論が skipped でない job だけ記録を読む（2026-11-13 の1回目で、段の名前と結論が steps に出ることを確かめた。移行の段が動いた回は10/29〜11/9 で447回中34回）。
4. 回ごとの分け方（段ごとに分ける。19-1 の止まる道を全部数える）:
   | 段 | 分け | 判定 |
   |---|---|---|
   | 移行の段 | 上限失敗 | 段の結論が failure で、記録に `lock conflict; retry limit reached` がある |
   | 移行の段 | その他の失敗 | 段の結論が failure・cancelled・timed_out で、上の文言が無い（10分で切れた回を含む） |
   | 移行の段 | 待ちあり（別の印） | 記録に `lock conflict; retry [0-9]` がある（行数も出す。成功した回も数える）。他の分けと重なる別の印で、上限失敗の回は「上限失敗」と「待ちあり」の両方に入る |
   | 点検の段 | STOP停止 | 段の結論が failure で、記録に `[precheck] STOP:` がある |
   | 点検の段 | その他の停止 | 段の結論が failure・cancelled・timed_out で、STOP の文言が無い（`could not count`・`invalid setting`・12分で切れた回） |
   | どちらも | 読めなかった | job の一覧か記録を引けなかった、または 2. の1,000件に達した |
   1つの回の分けは、移行の段で「上限失敗・その他の失敗・失敗なし」のどれか1つ、点検の段で「STOP停止・その他の停止・停止なし」のどれか1つ、または「読めなかった」。待ちありは、それとは別に付く印。
   記録の文字は `grep -a` で読む（19-1）。数えるときも、`grep -c`・`grep -q` を使わず、`grep -a` で行を取り出してから台本の中で数える（`-c`・`-q` は `-a` なしでも数が出るので、`-a` の抜けを試験で捕まえられない。2026-11-13 の審査3で GNU grep 3.11 で確かめた）。決まった文字（`lock conflict; retry limit reached`・`[precheck] STOP:`・`lock holders (xact > 1s):`）は `grep -aF`（文字どおりに探す）で探す。`[precheck]` は `-F` が無いと「p・r・e…のどれか1文字」の意味になるため。`-E`（形で探す）は `lock conflict; retry [0-9]` の1つだけに使う（`grep -aE 'lock conflict; retry [0-9]'`）。
   記録の各行の頭には時刻が付いている（例: `2026-11-13T05:36:16.8953667Z >>> [40/401]   394774 | salesanchor_app |  | idle in transaction | ...`、11/13 の1回目の記録 :3508）。行を読む前に、頭の時刻（最初の空白までの1語と、その後の空白1つ）を外す。
5. 握り手: 失敗の回だけでなく、待ちのあった全部の回から取る（K19-7 で (b) の後に名前の空の行を数えるため。成功した回の待ちにも握り手の行が出る、19-1）。取り方: 頭の時刻を外した後で、`lock holders (xact > 1s):` の見出しの行に続き、先頭が `>>> [段/全段]   ` の行を、` | ` で8つに分けられるものだけ読む。2つ目の列が DB ユーザー、3つ目が application_name（空なら「名前なし」）。8つに分けられない行は数だけ出す。接続元の場所は SELECT に無い（`scripts/run_all_migrations.sh` :65 の注記）ので出さない。
6. 出力: 1行1回の表（run id・回・時刻・段・分け・待ち行数・握り手のユーザーと名前）と、合計（移行の段が動いた回数・点検の段が動いた回数・分けごとの回数・名前ごとの握り手の行数）。job の要約（`$GITHUB_STEP_SUMMARY`）にも同じものを書く。API を呼んだ回数も出す。
7. 終わり方: 全部数えられたら 0。API の呼び出しが失敗したか、読めなかった回が1つでもあれば 2（数えた分は出す）。
8. 知らせ: 上限失敗・その他の失敗・STOP停止・その他の停止・読めなかった の合計が0でなければ、合計と run id（最大10件、それより多ければ「ほか N 件」）を `scripts/notify/discord-owner-ping.sh` で送る（Discord の上限で本文が1,900字で切られるため、`scripts/notify/discord-owner-ping.sh` :45）。0なら「0回」の1行を job の要約に残す（Discord には送らない）。
9. workflow の失敗: 台本の終わりが0でないとき、または Discord への送信が失敗したとき（`scripts/notify/discord-owner-ping.sh` :61〜:63 が 200・204 以外で 1 を返す）は、job を失敗にする。知らせが届かないのを黙って緑にしない。
10. 鍵: 台本は数えるだけで、本番のサーバーと DB には触らない。GitHub は workflow の GITHUB_TOKEN（permissions は actions: read と contents: read だけ）。Discord は前例と同じ secret DISCORD_WEBHOOK_SCHEDULED_REPORT を env DISCORD_WEBHOOK_OWNER_PING に渡す（`.github/workflows/weekly-stale-pr.yml` :19。secret は登録済み）。

試験（backend/tests/ops/test_deploy_lock_count.py。§18 の P7・P8 と同じ必須の pytest で走る。scripts/ の変更で filters に当たる）:
- 作り物の記録は、本物と同じく全部の行の頭に時刻（`2026-11-13T05:36:16.8953667Z `）を付ける（D1・D2）。
- D1 `--from-dir` に作り物の記録を置き、4. の分けをそれぞれ1回ずつと、何も無い1回、文字以外のバイトを混ぜた1回で、数が合う。期待する数: 上限失敗1・その他の失敗1・STOP停止1・その他の停止1・読めなかった1、待ちあり2（上限失敗の回と、待ちのあった成功の回）。文字以外のバイト（NUL）は、上限失敗の回の記録の、数える文言の行と握り手の行の中に置く（文字以外のバイトを混ぜた1回＝上限失敗の1回）。
- D1c 引く範囲: `--since 2026-11-09 --until 2026-11-16` で、`fetched dates` が 2026-11-01〜2026-11-16（UTC。19-4 の 2. の決まりどおり、日本時間の日付で since−7＝11/02 から until−1＝11/15 までを、始めを1日前・終わりを1日後に広げる）の16日分と一致する。範囲を期間だけに縮めると赤になる。
- D1b 週の境目: `run_started_at` が期間の始めのちょうど 00:00 JST（UTC で前の日の 15:00:00Z）の回は入り、終わりのちょうど 00:00 JST の回は入らない。期間の前に作られ期間の中でやり直された回は、やり直しの回だけ入る。終わっていない回は「読めなかった」に入る。
- D2 握り手の取り方: 作り物の行の列の順が `scripts/run_all_migrations.sh` :68 の SELECT の列の順（pid・usename・application_name・…）と同じことを、台本の実物の SELECT の文から確かめる（列の順を変えた PR が赤になる）。名前が空の行が「名前なし」に、8つに分けられない行が数だけに入る。成功した回の待ちの握り手も数える。
- D3 読めなかった回・1日1,000件に達した日（作り物の runs/<日付>.json の `total_count` を1000にする）があると、終わりが2になり、知らせの対象になる（0扱いにしない）。
- D4 workflow に schedule と workflow_dispatch（入力 since・until。空なら `--days 7`）があり、台本を呼び、permissions が読みだけ、secret の渡し方が前例と同じ、台本か送信の失敗で job が失敗する形。
- D5 文言の守り: 4. の文言（`lock conflict; retry limit reached`・`lock conflict; retry `・`[precheck] STOP:`・`lock holders (xact > 1s):`）が `scripts/run_all_migrations.sh` と `scripts/deploy-db-precheck.sh` にあること。
- 赤の実演（実装 PR に貼る）: `-a` を外すと D1 が赤／読めなかった回を0にすると D3 が赤／握り手を失敗の回だけから取ると D2 が赤／頭の時刻を外す処理を消すと D2 が赤／`[precheck] STOP:` を `-F` なしで探すと D1 が赤（作り物に `STOP:` だけで `[precheck]` の無い行を1つ置く）／回を run を作った時刻で週に入れると D1b が赤／期間の外の run を飛ばす処理を消すと D6 が赤（第3.3版で足した7つ目）。
- workflow の job に `timeout-minutes: 30` を付ける（第3.3版。止まったまま6時間待たないため）。
- D6 呼び出しを減らす（第3.3版）: 作り物の一覧に、`run_started_at` が期間の始めより前の run と、`created_at` が期間の終わり以後の run を置き、その run の回・job・記録のファイルを置かない。期待: その run は出力に出ず、「読めなかった」にも入らない。また、`run_attempt` 1 で一覧に `run_started_at` と `status` がある期間の中の run に、回のファイルを置かず job と記録のファイルだけを置く。期待: その run は正しく分けられる（回の API を呼ばずに済む）。
- `.github/workflows/test.yml` の filters（:45〜:54）と push の paths（:20〜:29）に .github/workflows/weekly-deploy-lock-count.yml を足す。workflow だけを変える PR でも D4 が走るようにする。

基準の数え（実装 PR の後、手で1回）: workflow_dispatch で since 2026-10-29・until 2026-11-14 を数える（第3.3版: 見込みは約720回で上限の1,000回より少ないので1回で流す。呼び出しが上限で失敗して終わりが2になったときは、1時間空けて since 2026-10-29・until 2026-11-06 と since 2026-11-06・until 2026-11-14 の2回に分けて流し、2回の結果を合わせて判定する）（until は「その日の 00:00 JST 未満」なので、11/13 の止まりを入れるには 11/14 にする）。期待（第3.2版で直した）: 上限失敗の回が、次の回ごとの一覧と一致する。§18-1 の「11/7 1回・11/9 5回」は `gh run view --log`（最後の回だけ）での手数えで、前の回の失敗が抜けていた（19-1 で見つけた抜けと同じ）ので、期待には使わない。
   - 回ごとの一覧（2026-11-13 のマージ前審査で、回ごとの API と `grep -a 'lock conflict; retry limit reached'` で読んだ。11/4〜11/10（UTC の作られた日付。日本時間 11/4 00:00〜09:00 に作られた8本はすべて成功）に作られた run のうち、最後の結論が success でないものと回が2以上あるもの。11/13 は 43372532867 だけを読んだ。生の出力は社内の作業メモ）:
     - 11/5（日本時間）1回: 41950091268 の回1。
     - 11/7 2回: 42331938658 の回1、42345436125 の回1。
     - 11/9 10回: 42596881194 の回1・回2、42598520163・42602029599・42602282851・42605177885・42605474375・42607425106・42609226129・42612168629 の各回1。
     - 11/13 1回: 43372532867 の回1（19-1）。
   - 読んだ範囲から外れていた3本は、どれも上限失敗ではないとマージ前審査で確かめた: 42805522437 は点検の段の停止、42392587964・42346763000 は job の無い取り消し。
   - 一覧で読んでいない日（10/29〜11/3、11/11・11/12、11/13 の 43372532867 以外）に台本が上限失敗を出したら、その回ごとに回の記録を手で読んで、文言があれば○として一覧に書き足す。文言が無ければ×。
   - 一覧の回を台本が出さない、または読んだ日に一覧に無い回を台本が出したら×として止め、その回の記録を読んで、台本と一覧のどちらが違うかを確かめる。

### 19-5. (a) 済んだ移行は流さない
- 正本は `docs/handoff/migration-runner-redesign/design.md` §5（第7版）と ADR-1005・ADR-1007。本節では順番と測り方だけを決める。
- 始め方: §5-3 の 5-0（P1〜P13 の前調査、読むだけ）をクラウドの Sonnet に出す。そのあと 5-1・5-2・5-3・5-4 を §5 の順に進める。5-2 は PO の決定（1A/1B）、5-3 は PO 本人の GO が要る（§5 のまま）。
- 本節で足す測り方: 5-3 の本番反映の後、(c) の数えで「失敗」が0の週が続くか。§5 の K5-6（新しい手順が0本の回で流す本数が0）とあわせて読む。
- 注意: 毎回流す一覧（§5-7）の手順は (a) の後も流れる。その手順が表を押さえるかは 5-0 で確かめる。押さえるなら、(a) の後も新しい移行の無い回で待ちが出うる。

### 19-6. (b) 試しの道具に名前と上限を付ける（概要。(a) の本番測定の後に詳細を書く）
- b1 アプリの接続の名前（段4a、§17）を先に実装する。§17-2 の名前の表に役割 `tool`（試しの道具）を1行足す。名前は §17 の1つの関数で作る `salesanchor_tool_<道>` で、別の作り方を足さない。
  - 前提（§17・§3 の順番）: 4a を本番に出すのは、段2の K2-5〜K2-7 がそろった後。b1 はその前提を変えない。そろっていなければ b1 も待つ。
  - 試しの道具は本番のアプリの入れ物に、`docker exec -e SA_PROCESS_ROLE=tool ...` で流す。§17-2 のとおり役割は名前の関数が呼ばれたときに読むので、道具の process が import した `_engine`（`backend/app/tasks/tcg_extraction.py` :94・:97）は、その process の中で `salesanchor_tool_<道>` を名乗る。同じ入れ物の中のアプリ（backend）の接続は SA_PROCESS_ROLE が無いので今の名前のまま。これで、同じ入れ物・同じ `_engine` の作り方でも、握り手が試しかアプリかを名前で分けられる。
  - 名前で分かるのは「試しの道具か、アプリか」まで。どの道具か（rejudge か replay か）は名前では分からない（`<道>` は接続の道で、道具の名前ではない）。どの道具かは、握り手の取引の始まりの時刻と、道具の記録の時刻を突き合わせて調べる（11/13 と同じ）。K19-7 は「名前なしの行が0」で測り、道具の特定は求めない。
  - 道具が最初に開く接続も、engine を作るときの名前（connect_args）で名乗るので、connect の受け手を付ける前の接続に名前が無い、ということは起きない。
- b2 試しの道具の確かめ: `backend/app/tools/_tx_guard.py` の `set_idle_tx_limit`（:43〜:52）で、上限を置いた後に `current_setting('application_name')` を読み、`salesanchor_tool_` で始まらなければ止める（`-e SA_PROCESS_ROLE=tool` の付け忘れを、流し始めに見つける）。名前を SET で付け直す道は作らない（名前の作り方は §17 の1つだけにする）。
  - 影響（呼ぶ側を全部見た、2026-11-13 `git grep set_idle_tx_limit`）: 道具 `backend/app/tools/prompt_ab.py` :485、`backend/app/tools/prompt_ab_recompute.py` :99・:116、`backend/app/tools/v102_replay_diff.py` :120・:143。試験 `backend/tests/test_tx_guard.py` :24（呼ぶ順を確かめる試験。名前を読む1手が増えるので、期待する順を直す）と `backend/tests/test_tx_guard_pool.py` :60・:61（本物の DB で呼ぶ。試験の中で役割を tool にして接続を作る形に直す）。詳細設計では、この一覧を変更表に入れ、試験は役割 tool のときに通り、役割が無いときに止まることの両方を書く。`backend/tests/test_prompt_ab.py` :50 と `backend/tests/test_prompt_ab_recompute.py` :74 は `set_idle_tx_limit` を monkeypatch で差し替えているので、本体の変更の影響を受けない見込み。詳細設計の一覧に「影響なし（差し替え済み）」として載せ、試験を流して確かめる。
- b3 守りの試験を広げる: `backend/tests/test_tools_tx_guard_required.py` の対象に、`from app.` を読み込んで DB を使う scripts/ と docs/ の下の .py を足す。`.github/workflows/test.yml` の filters（:45〜:54）と push の paths（:20〜:29）に docs/**/*.py を足し、docs に道具を足す PR でも必須の pytest が走るようにする。
  - 対象の決まりは詳細設計で絞る。「`from app.` を読み込む」だけでは、psycopg2 で直接つなぐ台本（`scripts/check_public_tenant_rls.py` :20・:79 など）も入ってしまう。アプリの接続（`_get_sync_session`・`_engine`・`SessionLocal` など、今の試験の `_DB_PATTERNS`）を使う .py だけを対象にする形を候補にする。
  - 今ある4本（19-1）は直すか、理由つきの例外にする。例外の理由と、直すときの試しの作り（仕入元1件を1つの取引にするのをやめるか）は詳細設計で決める。
  - psycopg2 で直接つなぐ3本は対象外（CI 用・使い捨ての DB 用・月次の点検）。開いたままの取引は点検の段が見つける。
- b4 の候補（今は作らない）: 本番反映の移行の間だけ、試しの道具が新しい取引を始めずに待つ仕組み（例: DB の合図の鍵を、移行は独り占めで、道具は取引の初めに共有で取る）。(a)・b1〜b3 の後も (c) で失敗が出たときに設計する。

### 19-7. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K19-1 (c) の台本が作り物の記録で正しく数える | D1・D1b・D1c・D2・D3・D5・D6 PASS（必須の pytest） |
| K19-2 (c) の workflow が毎週と手動で動き、読みだけの権限 | D4 PASS |
| K19-3 試験が壊れた台本を捕まえる | 赤の実演7つ（19-4） |
| K19-4 基準の数えが回ごとの一覧と合う | workflow_dispatch（since 2026-10-29・until 2026-11-14）の1回の記録で、上限失敗の回が 19-4 の基準の数えの一覧（11/5 1回・11/7 2回・11/9 10回・11/13 1回、run id と回つき）と一致し、一覧で読んでいない日に出た回は全部、回の記録に文言がある。違えば×として止める |
| K19-5 毎週の実行が届く | 実装の後の最初の月曜 10:00 JST の run が success（＝全部数えられ、知らせが要るときは Discord への送信も成功した、19-4 の 9.）で、要約に数が出る |
| K19-6 (a) の効果 | 5-3 の本番反映の後の4週、(c) の「上限失敗」が毎週0（KGI-7）。数える週は、移行の段が5回以上動いた週だけ（基準は10/29〜11/9 の34回で週に約21回）。5回未満の週は「保留」として飛ばし、数える週が4つそろうまで続ける |
| K19-7 (b) の効果 | b1〜b3 の本番反映の後の4週、(c) の握り手（待ちのあった全部の回）に名前なしの行が0。数える週は K19-6 と同じ決まり。名前なしの行が出たら、その行ごとに取引の始まりの時刻を試しの道具の記録と突き合わせる。試しの道具のものが1行でもあれば×。b3 の対象外の3本（psycopg2 で直接つなぐ）など、試しの道具でないと分かった行は「範囲外の名前なし」として別に数えて記録し、×にはしない（その行が続くなら別の段で考える） |

### 19-8. 弊害・トレードオフ
- (c) は GitHub の API を週に1回、1日ごとの run の一覧・回ごとの job の一覧・移行か点検の段が動いた job の記録の分だけ呼ぶ。11/12〜11/13 の約22時間で40 run あった。run の一覧の1回の検索は1,000件まで（19-4 の 2.）なので1日ずつ引く。GITHUB_TOKEN の呼び出しの上限は1つのリポジトリで1時間に1,000回（第3.3版で確かめた。19-4 の 2b.）。第3.2版の作りは毎週約900回・基準の数えで約1,500回で上限に近いか超えるため、第3.3版で期間の外の run を飛ばし、最後の回の回の API を省いた（見込み: 毎週約350回、基準の数え約720回）。台本は呼んだ回数を出すので、基準の数え（K19-4）の実際の回数を本節に書き足す。同じリポジトリの他の workflow も同じ上限を使うので、毎週の実行は月曜 10:00 JST（他の重い定期実行と重ならない時刻か、K19-5 で回数と一緒に確かめる）。上限に当たって呼び出しが失敗したときは、19-4 の 7. のとおり終わりが2になり job が失敗するので、黙って少なく数えることはない。
- (c) は数えて知らせるだけで、止まりを防がない。防ぐのは (a)・(b)。
- (c) は作ってから7日より後のやり直しを数えない（19-4 の 2.）。11/1〜11/13 のやり直しは全部40分以内だった。
- run の一覧を期間の7日前から引くので、週の数えでは約2週分の run を見る。呼ぶ回数は増えるが、記録を読むのは期間の中の回で、移行か点検の段が動いた job だけ。
- 記録の文言（`lock conflict; ...`・`[precheck] STOP:`）が変わると数えが0になる。D5 で、その文字が `scripts/run_all_migrations.sh` と `scripts/deploy-db-precheck.sh` にあることを確かめる（文言を変えた PR が赤になる）。文言の無い失敗・停止は「その他」に入るので、文言が変わっても失敗の回は数から消えない。
- 移行の段が少ない週（5回未満）は効果の判定に使わない（K19-6）。判定が延びることがある。
- (a) の弊害は migration-runner-redesign §5 の弊害の節のとおり。

### 19-9. 選ばなかった案
- 移行の前の点検（§18）をもっと厳しくする（3回続けての0を増やす・一時の入れ物が動いていたら待つ）: 11/13 の試しは45分動いた。待つ上限600秒を超えて本番反映が止まる回が増えるだけで、止まらないことにはならない。
- 試しを流してよい時間を人の決まりで決める: GoCardless は時間をずらす運用を人の決まりで続け、重く作る速さを妨げたと書いている（§18-10 の F3）。機械で守れない。
- K18-5 を手で数え続ける: 11/13 の止まりは一覧に出ない前の回で起き、手の数えでは見落としうる（19-1）。

### 19-10. 外部の事例（2026-11-13 に読んだもの。方向が合うことの裏付けで、成功の証明ではない）
| 事例 | いつ・どこ | 数値 | この設計との関係 |
|---|---|---|---|
| GitLab.com 本番の障害票 #20494 | 2025-09-08、本番反映の後の移行 | 移行を「実行済み」の印にするまで本番反映が全部止まった（時間の数値なし） | 適用の記録があるので印を付けて先へ進めた。当社には印を付ける場所が無い＝(a) |
| GitLab.com 本番の障害票 #22642 | 2026-08-05、DB の自動掃除が表を握った | 掃除の後もロック待ちで2回失敗、印を付けて通った | やり直しだけでは足りない日がある＝(a) |
| GoCardless の記事（zero-downtime-postgres-migrations-the-hard-parts） | 2015年1月、決済の API | API が約15秒停止。後に移行へ lock_timeout 750ms を既定で付けた | ADR-1037 と同じ形。今はある |
| postgres.ai（2021-09-23） | 手法の記事 | 数値なし | 短いロック待ち＋やり直しが標準。今はある |
- 見つからなかったもの: 試しと本番反映を重ねても止まらなくなった前後の回数を数値で出した事例。効果は (c) の自社の数で測る。

### 19-11. 戻し方・計画
- 戻し方: (c) は PR を revert して main にマージ。本番のアプリと DB は変わらない。(a) は §5 の戻し方（全件モード）。(b) は各 PR の revert。
- 計画: (1) 本節をクラウドの Architect（新しく起動・読むだけ）で審査 (2) 設計 PR → reviewer（opus）→ マージ (3) PO に結果を伝える (4) (c) の実装をクラウドの Sonnet に出す → reviewer（opus）→ マージ。scripts/ と workflow を足すが、本番の動き（deploy.yml）は変えない (5) 基準の数え（K19-4）と最初の月曜（K19-5） (6) migration-runner-redesign の 5-0 をクラウドの Sonnet に出す (7) 以後は §5 の順。(b) は (a) の本番測定の後に詳細を書く。
- 近い危険: rejudge_single_set.py の MODE=commit はまだ流していない。同じ仕入元ごとの長い取引で動くので、移行のある本番反映と重なると同じ止まりが起きうる。(a)・(b) が入るまでは、MODE=commit を流す前に本番反映が動いていないこと（`gh run list --workflow deploy.yml --status in_progress` が0件）を見てから流し、流している間は backend・scripts を変える PR をマージしない。

### 19-12. 継続（維持の仕組み）
- 守り手: .github/workflows/weekly-deploy-lock-count.yml（毎週月曜に数えて、0でなければ Discord）と backend/tests/ops/test_deploy_lock_count.py（数え方と記録の文言を必須の pytest で守る）。
- 数えた結果の記録は、毎週の job の要約と Discord に残る。KGI-7 の判定は (a)・(b) の本番反映のあと4週分を読む。
- 数えの文言の正本は `scripts/run_all_migrations.sh` と `scripts/deploy-db-precheck.sh` の echo の文。変えると D5 が赤になる。握り手の列の正本は `scripts/run_all_migrations.sh` :68 の SELECT。変えると D2 が赤になる。

### 19-13. 範囲外（記録のみ）
- アプリ（salesanchor_backend）が SET の後に取引を開いたまま置く件（§18-7）。
- 11/5・11/7 の止まりの握り手（K19-4 の基準の数えで名前の列だけは出る）。
- 毎週の数えをほかの workflow（失敗の数一般）へ広げること。

### 19-14. 審査の記録
- 第1版 REVISE（2026-11-13、クラウドの Architect（opus）新規起動・読むだけ）。指摘はすべて実物で確かめた（記録は社内の作業メモ）。
  - 必須1 test.yml の行番号の誤り（作業メモの行番号を書いていた）→ 19-1・19-6 を :45〜:54 と :20〜:29 に直した。recon.md も直した。
  - 必須2 文言だけの数えでは、点検の段の他の止まり方と時間切れを数えない → 19-4 の 4. を段ごとの6つの分けにした。19-1 に止まる道を足した。
  - 必須3 握り手を失敗の回からだけ取ると K19-7 が測れない → 19-4 の 5. で待ちのあった全部の回から取る。
  - 必須4 毎週の判定に分母が無い → K19-6・K19-7 に「移行の段が5回以上の週だけ数える」を足した。19-4 の 6. で動いた回数を出す。
  - 必須5 Discord の secret と送信失敗の扱いが無い → 19-4 の 8.〜10.。
  - 必須6 b1 で試しとアプリを分けられない（同じ入れ物）・b2 の SET の道が §17 の1つの関数と食い違う → 19-6 で役割 tool を §17 の表に足し、`-e SA_PROCESS_ROLE=tool` で名乗る形にした。SET の道はやめた。
  - 推奨7 最初の接続が受け手を通らない → 19-6 の b1（engine を作るときに名乗る）で解消。
  - 推奨8 握り手の行の取り方が無い・D2 が何も守っていない → 19-4 の 5. と D2 を書き直した。
  - 推奨9 一覧の1,000件の上限 → 公式資料で確かめ、1日ずつ引く形にした（19-4 の 2.）。
  - 推奨10 workflow だけの PR で D4 が走らない・Discord の1,900字 → test.yml に足す行（19-4 の表）と、run id を最大10件にする（19-4 の 8.）。
- 第2版 REVISE（2026-11-13、クラウドの Architect（opus）新規起動・読むだけ、審査対象 a521432bd）。必須2・推奨3。指摘は実物で確かめた（記録は社内の作業メモ）。第3版で全件を直した。
  - 必須1 記録の行の頭に時刻があり、「先頭が `>>> [段/全段]`」の決まりでは握り手の行を1つも読めず、K19-7 が見かけで通る（11/13 の1回目の記録 :3507・:3508 で確かめた）→ 19-4 の 4.・5. で頭の時刻を外してから読む。作り物の記録に時刻を付け、赤の実演を足した。
  - 必須2 週の境目が無く、週をまたいで重ねて数えうる → 19-4 の 2. で、日本時間の月曜 00:00 区切り・回の始まりの時刻で週に入れる・7日前から引いて期間の外は数えない・7日より後のやり直しは数えない限界、を決めた。D1b を足した。
  - 推奨3 `[precheck]` が grep の形の中で文字の組になる → 決まった文字は `grep -aF`、`-aE` は `retry [0-9]` だけ（19-4 の 4.）。
  - 推奨4 b2 の影響（呼ぶ側3本と試験2本）が書かれていない → 19-6 の b2 に一覧と試験の直し方を書いた。
  - 推奨5 名前は道具までは分けない・§17 の前提 → 19-6 の b1 と 19-3 に書いた。
- 第3版 APPROVE（2026-11-13、クラウドの Architect（opus）新規起動・読むだけ、審査対象 c6040aae4）。必須0・推奨5。第2版の5件の直しと b2 の file:line 9か所が実物と合うこと、週の決まりが一義であることを確かめた。推奨5件は実装の前に第3.1版で設計書に入れた。
  - 推奨1 `-a` を外す赤の実演は、`grep -c`・`grep -q` で数える作りでは赤にならない（GNU grep 3.11 で試した）→ 19-4 の 4. で行を取り出してから数える形にし、D1 で NUL を数える行と握り手の行の中に置く。
  - 推奨2 `--from-dir` の形が無く、引く範囲を試験で守れない → 19-4 の 1. に形と `fetched dates` の出力、D1c を足した。D3 の1,000件の作り方も書いた。
  - 推奨3 1つの回が2つの分けに入る → 待ちありを別の印にし、D1 の期待する数を書いた。
  - 推奨4 基準の数えの入力・11/13 が入らない・run id が無い → workflow_dispatch の入力を D4 に足し、until を 11/14 にし、K19-4 を日付ごとの回数で判定する形にした。
  - 推奨5 対象外の3本の接続で K19-7 が×になりうる → K19-7 で、試しの道具のものと範囲外の名前なしを分けて数える形にした。
- 第3.1版: 推奨5件の反映だけ。審査の結論（APPROVE）を変える直しは無い。マージ前の審査（reviewer、opus）で確かめる。
- 第3.1版 マージ前審査 REVISE（2026-11-13、reviewer（opus）新規起動・読むだけ、審査対象 91460c59a）。必須2・推奨4。file:line は全部実物と合っていた。
  - 必須1 K19-4 の期待（11/7 1回・11/9 5回）は最後の回だけの手数えで、回ごとに読むと 11/5 1回・11/7 2回・11/9 10回ある。正しく作った台本が×になる → 19-4 の基準の数えと K19-4 を、回ごとの一覧（run id と回つき）との照合に変えた。
  - 必須2 D1c の範囲とかっこ内の計算が始めの側で食い違い、「7日前」を日本時間で取るか UTC で取るかが決まっていない → 19-4 の 2. に「日本時間の日付で since−7〜until−1、UTC の日付として両端を1日広げる」と例を書き、D1c のかっこ内を合わせた（16日分のまま）。
  - 推奨1 b3 の対象の決まりだと psycopg2 の台本も入る → b3 に、対象を絞る候補を書いた。推奨2 b2 の影響一覧に差し替え済みの試験2本 → b2 に足した。推奨3 照合の版が古い → 対象ファイルは変わっていないと審査で確かめたので直さない。推奨4 D1 の文字以外のバイトを混ぜる回 → 上限失敗の回と書いた。
- 第3.2版: 上の必須2・推奨3件の反映。マージ前の審査（reviewer、opus、新規起動）でもう一度確かめる。
- 第3.3版（2026-11-14、Opus）: (c) の1回目の実装（077a2e388、試験15件合格・赤の実演6つ○）の確かめで、Opus が呼び出し回数を数え直した。deploy.yml の run 数（10/28〜11/14 で644本）から、第3.2版の作りは基準の数えで上限（1時間1,000回）を超えると分かった → 19-4 の 2b.（期間の外の run を飛ばす・最後の回は一覧の値を使う・一覧に値が無いときは今の読み方）、D6、赤の実演7つ目、timeout-minutes、K19-4 の分けて流す手順、19-8 を足した。KGI と分け方は変えない。実装の直しはクラウドの Sonnet、審査はマージ前の reviewer（opus、新規起動）で確かめる。

### 19-15. 第3.4版（2026-11-14、Opus）— 読めなかった理由を残す（(c) の直し・調べるための一歩）
事実（Opus が実物で確かめた。生の記録は社内の作業メモ）:
- PR #5501 のマージ（6bc263b42、2026-11-14 22:00 JST）の後、基準の数え（workflow_dispatch、since 2026-10-29・until 2026-11-14、run 43597593003）は「読めなかった 209」「移行の段が動いた回数 0」「API呼び出し回数 886」「終わり 2」で job が失敗した。知らせは Discord に1通出た（HTTP 204）。
- 209行はすべて時刻が入り、段が `-`。台本で時刻つきの「読めなかった」を出すのは、回が completed でないとき・job 一覧を引けないとき・job の記録を引けないときの3か所（`scripts/ops/count-deploy-lock-failures.sh` の process_attempt）。呼び出し回数 886 ≒ 一覧25日＋job 一覧約650＋記録209 で、記録を引く段で失敗したと読むのが数に合う（推測。理由の文は `fetch` が `2>/dev/null` で捨てているため、まだ確かめていない）。
- 同じ job（124476850185）の job 一覧と記録は、Opus の手元の gh（PO のアカウント）では引けた（記録 645,903 バイト）。公式資料（Context7 /websites/github_en_rest「Download job logs for a workflow run」）は「リポジトリを読める者は使える。302 で1分だけ有効な場所へ送る」。workflow の権限は actions: read・contents: read で、資料の条件は満たしている。リポジトリ内に、workflow の鍵で job の記録を引く前例は無い（git grep で0件）。
- 試験（D1〜D6）は `--from-dir` の作り物で読むため、GitHub の中での引き方の違いは試験で見えなかった（設計の抜け）。

決め（第3.4版で作るのはここだけ。原因の直しは理由を見てから別に決める）:
1. `fetch` で gh の失敗の文を捨てず、作業用の置き場のファイルに受ける。失敗したら、その文の最初の空でない行を「理由」とする。理由は `?` から後ろを消し（送り先の URL の署名を出さない）、160字で切る。文が空なら `理由なし`。`--from-dir` で作り物のファイルが無いときの理由は `作り物なし`。
2. 「読めなかった」を数える所（`mark_unreadable` を呼ぶ所すべて）で、理由と「どの段で引けなかったか」（`回`・`job一覧`・`記録`・`一覧`、回が completed でないときは `未完了`、時刻が無いときは `時刻なし`）を組にして数える。
3. 出力の「読めなかった: N」の次に「読めなかった理由:」の見出しと、`  <段> / <理由>: <件数>` の行を並べる（並びは sort）。Discord の本文にも同じ行を最大5行足す（1,900字の切りは今のまま）。
4. 表の行（7列）は変えない（試験の読み方を変えない）。

試験 D7（`--from-dir`）: job の記録のファイルだけ置かない回と、job 一覧のファイルだけ置かない回を作り、「読めなかった理由:」の下に `記録 / 作り物なし: 1` と `job一覧 / 作り物なし: 1` が出ること、知らせの本文に同じ行が出ることを確かめる。理由の `?` から後ろを消すことは、gh の代わりに失敗の文を返す偽の gh を PATH の先頭に置く試験で確かめる（文 `HTTP 403: x (https://a.example/b?sig=SECRET)` → 出力に `SECRET` が無く `https://a.example/b` が有る）。
赤の実演8: 写しの台本で理由の組を数える行を消す → D7 が赤。
受け入れ: 試験 D1〜D7 が全部合格・赤の実演8が赤・マージ後に基準の数えを流し直し、「読めなかった理由:」に理由の行が出る（K19-8。理由が出たら Opus が原因の直しを設計する）。
弊害: 出力が数行増える。理由の文に署名つき URL が混ざる恐れ → 決め1で `?` から後ろを消す。
戻し方: この直しのマージを revert する（数えは第3.3版の形に戻る）。

### 19-16. 第3.5版（2026-11-14、Opus）— job の記録を引けるようにする（(c) の原因の直し）
事実（Opus が実物で確かめた。生の記録は社内の作業メモ）:
- PR #5505 のマージ（180710bff、2026-11-14 23:08 JST）の後、基準の数えを同じ期間で流し直した（workflow_dispatch、run 43603442048）。結果は「読めなかった 209」「API呼び出し回数 886」「終わり 2」で前と同じ。理由の行は1種類だけだった: `記録 / the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway: 209`。
- つまり 209件すべて、job の記録を引く段で gh が「返事に端末の制御文字（色の指定など）が入っている」として出力を断っていた。GitHub への問い合わせ自体は通っている（権限の問題ではない）。§19-15 の「302 で失敗」の推測は外れ。
- 公式資料（Context7 /websites/cli_github_manual「gh api」、https://cli.github.com/manual/gh_api）: `gh api` には `--allow-escape-sequences`（「端末の制御文字を出してよい」）がある。同じ資料の `gh repo read-file` の項は「既定では制御文字を含む中身の出力を断る。端末を操られうるため。読むには `--allow-escape-sequences`」と書く。
- Opus の手元の gh は 2.85.0 で、`gh api --help` にこの指定が無い（手元で引けたのはこのため）。GitHub の実行機の gh は断る版である（上の理由の文が実物）。
- 台本は記録を `grep -aF` / `grep -aE` で読み、握り手の行は出力と Discord の本文に載る。記録に制御文字が残ると、載せた行に制御文字が混ざりうる。

決め（第3.5版で作るのはここだけ）:
1. `fetch` で、引く先が job の記録（API のパスが `/logs` で終わる）のときだけ `gh api` に `--allow-escape-sequences` を付ける。ほかの引き方（一覧・回・job 一覧。中身は JSON）は変えない。
2. 記録を引けた直後（`--from-dir` で写したときも同じ）に、記録のファイルから制御文字を消す: まず `ESC [ 数字と ; の並び 英字1つ`（色などの指定）をまとめて消し、残った ESC（8進 033）を `tr -d` で消す。sed は `LC_ALL=C` で、ESC は `printf '\033'` で作って式に入れる（GNU と BSD のどちらの sed でも動く形）。消したあとの中身を、今までと同じ grep で読む。
3. 数える文言（`lock conflict; retry limit reached` など）・表の7列・出力の形・知らせの形は変えない。

試験 D8（`--from-dir`）:
- D8-1: job の記録の作り物で、`lock conflict; retry limit reached` の行の前後と途中に色の指定（`ESC[31m` と `ESC[0m`）を入れる。上限失敗として 1件数え、出力全体と知らせの本文に ESC（8進 033）が1つも無いことを確かめる。
- D8-2: 偽の gh（PATH の先頭）が受け取った引数をファイルに書く。`--from-dir` なしで流し、`/logs` で終わる呼び出しにだけ `--allow-escape-sequences` が付き、ほかの呼び出しには付かないことを確かめる。
赤の実演9: 写しの台本で制御文字を消す行を消す → D8-1 が赤。赤の実演10: 写しの台本で `--allow-escape-sequences` を付ける所を消す → D8-2 が赤。
受け入れ（K19-9）: 試験 D1〜D8 が全部合格・赤の実演9と10が赤・マージ後に基準の数え（since 2026-10-29・until 2026-11-14）を流し直し、「読めなかった」が 0、上限失敗の回が §19 K19-4 の一覧（11/5 1回・11/7 2回・11/9 10回・11/13 1回）と run id・回の番号まで一致する。API呼び出し回数を §19-8 に書く。
弊害: 記録の中の制御文字は消えるので、数えの出力は元の記録の色を持たない（数えに色は要らない）。手元の古い gh（2.85.0 など）で `--from-dir` なしに流すと、知らない指定として失敗し「読めなかった」とその理由が出る（数えは GitHub の中で流すもので、手元では `--from-dir` を使う）。
選ばなかった案: (1) 全部の `gh api` に付ける — JSON の引き方は困っておらず、古い gh で一覧まで引けなくなる。(2) `gh run view --log` に替える — 出力の形が変わり、時刻の外し方・試験の作り物を作り直すことになる。(3) curl で直接引く — 鍵の扱いを台本に持ち込むことになる。
戻し方: この直しのマージを revert する（数えは第3.4版の形に戻る。数えは本番のサーバー・DB に触れない）。
外部の事例: 該当なし（gh の仕様の確かめで足りる。公式資料は上の事実に記した）。
