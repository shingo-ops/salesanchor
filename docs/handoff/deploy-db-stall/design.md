<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 本番反映の移行が仕入元の表を2時間止めた件の再発防止

**対象ADR**: ADR-1037（拡張。新規 ADR は作らない）。関連 ADR-1005・ADR-1003・ADR-135・ADR-136  
**日付**: 2026-10-29  
**担当**: Planner（Opus）。状態: 設計審査済み（第7版 APPROVE、§12）・段1実装未着手  
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
| 1 | Python の移行（run_py）にもロック待ち1秒と再試行を付ける（§4） | 本番 scripts・deploy.yml の db_migrations・CI（委任 GO。ADR-1003 の例外7種に当たらない） | 本書で詳細設計 |
| 2 | 本番反映が時間切れのとき、サーバー側の移行・バックアップも止める。開始時に取り残しを片付ける | deploy.yml | 段1の測定後に詳細設計 |
| 3 | `scripts/backup.sh` :27-29 の pg_dump にロック待ちの上限を付ける | 本番 scripts | 同上 |
| 4 | アプリの同期接続に名前を付ける。ロック待ちログを有効にする | backend・DB 設定 | 同上 |
| 5 | 056 など、流し直しのたびに排他ロックを取る書き方をやめる（存在を確かめてから DROP、または適用済みの記録） | migrations/（PO 本人の GO の要否を確認） | 同上 |

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
| run_py の標準エラー | そのまま流れる | そのまま流しつつ一時ファイルにも写す（tee）。実行中のログは今までどおり入れ替えの画面に出る |
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
- run_py の標準エラーは `2> >(tee "${errlog}" >&2)` の形で出しながら写す。判定の前に tee の終了を待つ（プロセス置換を作った直後に `$!` を変数へ取り、その番号を wait する。bash 公式の wait の節）。本番の bash は 5.0 以上と確認済み（本番反映の read-probe が EPOCHREALTIME〔bash 5.0〜〕で値を取れており invalid=0。プロセス置換の `$!` を wait できるのは 4.4〜）。
- `scripts/run_all_migrations.sh` は set -e なので、docker exec と wait の終了コードは `cmd || rc=$?`・`wait "${pid}" || true` の形で受け、再試行の判定より前にスクリプトが終わらないようにする（run_sql :76-105 の受け方に揃える）。
- 触らない範囲: run_py の開始行の echo の文面（今の :52-53。`>>> [N/NN] python <本物のパス> ` のまま。K9 の突き合わせがこの行のファイル名に頼るため）、値4つ（:65-68）、log_lock_holders の中身、run_sql の外から見た動き、:107-171 の read-probe、:194-215 の EXIT trap、移行の登録行、migrations/ と移行21本の中身。

### 4-3. 試験
試験の置き場所は、PR で自動に走る `.github/workflows/migration-test.yml`（:41-48 の条件で、`scripts/run_all_migrations.sh` と scripts/migrate_*.py の変更で起動）と、既存の sandbox 試験2本（`tests/sandbox/migration-run-sql-retry.sh`・`tests/sandbox/migration-read-probe.sh`）に分ける。新しい試験用コンテナは作らない。

起動条件の追加:
- `.github/workflows/migration-test.yml` :41-48 の paths-filter に scripts/migration_py_entry.py を足す（ファイル名が migrate_ で始まらず今の条件に当たらないため。入口だけを直す PR でも S1・S2・P1〜P3 を走らせる）。
- `.github/workflows/deploy.yml` :56-59 の db_migrations にも足す。理由: 移行の段は scripts 配下すべて で入口の変更でも走るのに、本番反映前のバックアップ（:196）は db_migrations でしか走らない。入口は全部の Python 移行の接続を変えるので、変えた回は控えを取ってから流す。

`.github/workflows/migration-test.yml`（PR ごとに自動）。S1・S2・P1〜P3 はすべて migration-test-run ジョブ（:964 の段があるジョブ、DATABASE_URL あり）に置く。migration-full-dryrun（:1112）には置かない:
- S1 付け忘れ・差し替え漏れの静的点検: `^run_py[[:space:]]` の呼び先全部について、(a) `sqlalchemy.ext.asyncio.engine` の出現が0件、(b) create_async_engine を取り込む行がすべて `from sqlalchemy.ext.asyncio import` の形（1行でも別の形があれば赤。「正しい形が1行ある」では判定しない）、(c) 同期の `create_engine(` が0件。`asyncpg.connect(`・psycopg の直接使用も無いこと（差し替えを通らない接続のため）。違えば赤。`モジュール.create_async_engine(` の書き方は差し替えが効くので止めない。手本は :1666- の静的点検。新しい移行が別の書き方で足されたらここで止まる。
- S2 run_py が入口を通ること: run_py の定義の中に `migration_py_entry.py` と `MIGRATION_LOCK_TIMEOUT` があること（grep）。
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
- run_py 試験用の偽コマンドの差し込み方（関数の上書きか変数か）は実装役が決めてよい。本物の run_py の文面は写さず抜き出す。

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

## 13. 継続（維持の仕組み）
- 付け忘れ・差し替え漏れ: 守り手: `.github/workflows/migration-test.yml`（S1・S2。PR で `scripts/run_all_migrations.sh`・scripts/migrate_*.py・入口が変わると走る）。
- 抜き出し範囲（`^SQL_LOCK_TIMEOUT=` 〜 run_sql の閉じ括弧）: 守り手: `tests/sandbox/migration-run-sql-retry.sh` と `tests/sandbox/migration-read-probe.sh`（どちらも抜き出しに失敗すると止まる）。
- 値の正本: `scripts/run_all_migrations.sh` の SQL_LOCK_TIMEOUT だけ。
- 移行の範囲（db_migrations と MIGRATION_PATH_PATTERNS）を揃えること: 人手で守る（`scripts/check-process-artifacts.js` :68-73 のコメントが両者を揃えると定めている）。
- run_sql と run_py の再試行の動き: 守り手: `tests/sandbox/migration-run-sql-retry.sh`（手で起動。run_all_migrations.sh の再試行部分を変える PR で実行し、結果を PR に貼る）。
