# design: CI の試験どうしのぶつかりで main が赤になるのを 0 回にする

状態: 便1は合流・本番反映済み（PR 5790・2026-11-27）。便2〜5は設計案作成済み・設計審査済み（Opus 自己審査・§12）。PO の指示 2026-11-27「1」（便1を実装し、ほかの種類も並べて調べる）と、最初の指示（合流・反映まで完走）に基づいて実装へ進める。
参照: docs/handoff/ci-test-shared-collisions/recon.md（以下 recon）。関係する ADR: ADR-1024（共通の役割 `ai_reader` を定める。本番の戻し方 :80 だけが `DROP ROLE` を書く。試験の後片付けの決まりは無いので、本書は ADR-1024 を変えない）。区分: 試験コードだけを変える。製品コード・本番・CI 設定には触らない。

## 1. 目的（KGI）
main の試験が赤になるのは、今は試験どうしのぶつかりだけが理由である（recon §1。直近60回中9回）。赤が出るたびに、本当の不具合かどうかを確かめる手間がかかっている。
**KGI: 全便の合流後、main の Backend Tests が「試験どうしのぶつかり」で落ちる回数を、続けて30回のあいだ 0 回にする（今は60回中9回）。** PO 承認 2026-11-26「1」。

## 2. 進め方（1便1種類・変更→反映→測定）
| 便 | 種類 | 状態 |
|---|---|---|
| 便1 | D 役割が消える | 本書 §3。PR 5790 で合流・本番反映済み |
| 便2 | A 調べたが無い | 本書 §7（recon §6-3）。PR は甲 |
| 便3 | B 請求書の表 | PR 5669 で直っている（recon §6-1）。§8 で数えるだけ |
| 便4 | C カルテ | カルテは PR 5669 で直っている。同じ形の2ファイルを §9 で直す。PR は乙 |
| 便5 | E テナント998 | 本書 §9（recon §6-4）。PR は乙 |

便4と便5は、どちらも「札の外の後片付けを札で包む」同じ型なので、1つの PR（乙）にまとめる。効果は KGI の30回でまとめて数える。

## 3. 便1: 共通の役割を試験の後片付けで消さない

### 3-1. 変更前後
recon §2 の6ファイルについて、後片付けの中の共通の役割を消す部分だけを外す。使い捨ての DB を消す行（`DROP DATABASE ... WITH (FORCE)`）と、接続を閉じる行は残す。

| ファイル | 変更前 | 変更後 |
|---|---|---|
| `backend/tests/ops/test_ai_cloud_views.py:84-96` | `_Cluster` が始めの有無を覚え、`cleanup()` で無かった役割を消す | `_Cluster.cleanup()` は何もしない。中身を消し、理由のコメント1行を残す |
| `backend/tests/ops/test_ai_job_assignments_db.py:70-82` | 同上 | 同上 |
| `backend/tests/ops/test_ops_case_db.py:87-105` | 同上（`_ROLES` 7つ） | 同上 |
| `backend/tests/ops/test_ops_case_report_kind_migration.py:104-108` | `for r in _ROLES: if not existed[r]: DROP ROLE` | この for 文を外す |
| `backend/tests/test_ops_case_router.py:187-192` | 同上 | 同上 |
| `backend/tests/ops/test_ai_ro_views.py:98-99` | `if not role_existed: DROP ROLE IF EXISTS ai_reader` | この2行を外す |

- 追加（2026-11-27・K3 の不合格を受けて）: `backend/tests/ops/test_ai_cloud_views.py:224-240` の `test_meta_migration_without_ai_reader` は、`ai_reader` があると skip する。役割を消さなくなると、ほかのファイルが先に作った `ai_reader` が残り、この試験が毎回 skip になる（PR の run 45857839276・45858440452 は skipped 80、main の直近6回は全部 79）。
  - 変更前: `pg_roles` に `ai_reader` があれば `pytest.skip`。無ければ meta の migration をそのまま2回流す。
  - 変更後: skip をやめる。meta の migration の文の役割の名前 `ai_reader` を、`re.sub(r"\bai_reader\b", absent, ...)` で確実に無い名前 `absent = f"ai_reader_absent_{uuid.uuid4().hex[:8]}"` に置き換えて2回流す。流す前に、`absent` が文に入ったこと（`assert absent in sql`）と、`pg_roles` に `absent` が無いこと（`assert` で確かめる）を確かめる。`\b` なので `ai_reader_cloud` は置き換わらない（`migrations/20261024_100000_create_ai_cloud_meta.sql` で `ai_reader` が出るのは :5-6 のコメントと :190-194 だけ）。
  - これで「役割が無い DB でも migration が2回通る」を毎回確かめられる。共通の役割には触らない。
- 使わなくなった変数（`existed`・`role_existed`・`_ROLES`・`self.existed` など）は、ほかで使っていなければ外す。使っていれば残す。lint（ruff）の指摘が 0 件になる形にそろえる。
- 理由のコメントの文: `# 共通の役割はクラスタ全体で1つ。別の係が使っている途中で消すと落ちるため、試験では消さない（docs/handoff/ci-test-shared-collisions/design.md 便1）`
- 触らない範囲: 役割を作る行、属性を一時的に変える試験（`backend/tests/ops/test_ai_cloud_views.py:460-468`・`backend/tests/ops/test_ops_case_db.py:621-627`）、`backend/tests/test_tenant_isolation_daily_check.py`（自分で作った名前の役割だけを消すため）、migration、製品コード、CI 設定。

### 3-2. 代替案と選んだ理由
- A（採用）共通の役割を消さない: 消すことが原因なので、消さなければ起きない。役割を作る migration は冪等なので、残っていても次の試験は困らない（recon §2）。CI の DB は回ごとの使い捨てで、残りは次の回に持ち越されない。
- B 役割の出入りを札で順番にする: 6ファイルのモジュール全体で札を持つことになる。同じ係の中で札を待ち合う危険があり、試験の時間も延びる（上限15分まであと約2分）。不採用。
- C 試験ごとに別の名前の役割を作る: migration は名前が決まっているので、名前を変えると migration の形を確かめられない。不採用。

### 3-3. リスクと対処
- 手元の DB に役割が残る。パスワードの無い役割なので、ログインには使えない（`migrations/20261024_100100_create_ai_reader_cloud_role.sql:2`）。手元で消したいときは手で消す。
- 属性を一時的に変える2か所の重なり（recon §2「未観測の近い危険」）は、便1では直さない。1便1種類の決まりに従う。便1の受け入れ基準 K4 で見張り、出たら次の便に入れる。

### 3-4. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1: 差分は §3-1 の6ファイルと、本書類（recon・design・review-opus）・台帳だけ | `gh pr diff --name-only`（審査役） |
| K2: 6ファイルに、共通の役割を消す `DROP ROLE` が1つも残らない | `git grep -n "DROP ROLE" -- backend/tests` で、`backend/tests/test_tenant_isolation_daily_check.py` 以外が0件（Opus） |
| K3: PR の必須チェック pytest が pass。6ファイルの試験は数が減らず、skip も増えない | `gh pr checks` と、PR の run の記録で6ファイルの passed 数を main の直近の回と比べる（Opus） |
| K4: 合流後の main の Backend Tests 30回で、`role "..." does not exist` と `already exists with unexpected attributes` が0件 | 30回分の失敗の記録を `--log-failed` で保存して数える（Opus・合流から約1〜2週） |

## 4. 外部・過去事例の参照と我々への応用
- PostgreSQL 16 公式（Context7 /websites/postgresql）: ALTER TABLE は明記が無ければ ACCESS EXCLUSIVE を取る。ACCESS EXCLUSIVE はほかのすべての札とぶつかる（explicit-locking.html）。便2以降で、巻き戻す DDL を長く持つ危険の根拠に使う。
- 過去の自分たちの例: 2026-11-05 と 11-06 に、札の外で DROP していた試験を札の中に入れて、デッドロックを0件にした（覚え書き test_lock_collisions・PR 5179）。便3〜5は同じ型で直せるかを先に確かめる。
- 数値の外部事例は使わない。直す対象はこのリポジトリの試験だけで、効果は自分たちの main の回数で測るため。

## 5. 維持の仕組み
- 守り手: docs/handoff/ci-test-shared-collisions/design.md §3-4 の K2 の `git grep` を、便の受け入れのときに Opus が流す。
- 将来の新しい試験が共通の役割を消す形を持ち込むのを、機械で止める見張りは便1には入れない。便2〜5で同じ型の見張りがまとまって要るかを判断して、最後の便で1つにまとめる（覚え書き no_repeat_mistake_rule）。
- KGI の数え方: 全便の合流後、main の Backend Tests 30回分の失敗の記録を Opus が読み、ぶつかりの種類ごとに数える。

## 6. 便1の実装カード（クラウドの担当へ渡す）
- 作業場所: 本書類と同じブランチ `release/ci-test-shared-collisions` に足す（1つの PR に設計と実装をまとめる）。`bash scripts/new-worktree.sh release/ci-test-shared-collisions` で場所を作り、`git switch -C release/ci-test-shared-collisions origin/release/ci-test-shared-collisions` で合わせる。
- 変更: §3-1 の表のとおり。触らない範囲は §3-1 の最後の項。
- 確かめ（手元で試験は回さない。試験は GitHub の CI で回す）:
  1. `git -C <wt> diff --stat` が6ファイルだけであること。
  2. `git -C <wt> grep -n "DROP ROLE" -- backend/tests` が `backend/tests/test_tenant_isolation_daily_check.py` の2行だけであること。
  3. `cd <wt>/backend && ruff check tests/ops/test_ai_cloud_views.py tests/ops/test_ai_job_assignments_db.py tests/ops/test_ops_case_db.py tests/ops/test_ops_case_report_kind_migration.py tests/test_ops_case_router.py tests/ops/test_ai_ro_views.py` が0件であること。
- 想定の分かれ道:
  - 消す対象の変数がほかの試験で使われていた → 変数は残し、消す行だけを外す。
  - 表の行番号が今の main とずれていた → 中身（`DROP ROLE` の for 文）で場所を決める。中身も違っていたら止めて報告する。
- commit して push する。PR は作らない（Opus が作る）。

## 審査（Opus 自己審査・2026-11-27）
- 便1は、原因（recon §2 の起きる順番）と直し方（消す行を外す）が1対1に対応している。既存 ADR との食い違いは無い（recon §5）。
- 受け入れ基準は、どれも記録や差分で ○× を決められる。
- 判定: 便1は APPROVE。便2〜5は REVISE（調べが要る。recon §3・§4 の未確認）。
- 未解決: 便2〜5の仕組み。属性を一時的に変える2か所の重なり（未観測）。

## 7. 便2: 調べたが無い（A）— 商品一覧の試験の public の DDL を、巻き戻さず1回だけ確定させる
根拠: recon §6-3。手本は `ensure_product_packagings`（`backend/tests/rls_bootstrap.py:111-150`）。

### 7-1. 変更前後（変えるのは `backend/tests/test_tcg_product_list_pg.py` と、見張りの分類1件）
| 場所 | 変更前 | 変更後 |
|---|---|---|
| `backend/tests/test_tcg_product_list_pg.py` 新しい関数 `ensure_product_list_public(engine)` | 無い | 下の 7-2 の形で足す |
| `product_db`（:103） | `await ensure_product_packagings(engine)` | `await ensure_product_list_public(engine)`（中で `ensure_product_packagings` を先に呼ぶ） |
| `create_product_schema`（:47-92） | 使い捨てスキーマの表と public の DDL を両方流す | 使い捨てスキーマの分だけにする: `CREATE SCHEMA`（:49）、t004 の3本（:56-62）、`_rewire_keyword_fks(schema)`（:78）。この順は変えない |
| phase3（:80-84） | 巻き戻す transaction の中で流す | どこでも流さない（使い捨てスキーマには何もしないため。recon §6-3） |
| `backend/tests/test_tenant_loop_migration_guard.py:284-287` | `backend/tests/test_tcg_product_list_pg.py` を `own_database` で phase3 と登録 | この登録を消す。消した後も見張りの試験が通ること（phase3 の名前がこのファイルに無くなるので、登録は要らなくなる） |

触らない範囲: 試験の本体（:123 以降）、`product_db` の共有の xact 札（:108-113）と rollback（:118）、ほかの試験ファイル、`backend/tests/rls_bootstrap.py`、migrations、製品コード。

### 7-2. `ensure_product_list_public(engine)` の形
1. `await ensure_product_packagings(engine)`（products を本番の形で用意する。試験用の少列版の products を確定させない決まりを守る）。
2. 札を取らずに揃っているかを確かめる関数 `_product_list_public_ready(engine)`。次がすべて真なら何もしないで戻る:
   - `to_regclass` が NULL でない: `public.product_kinds`・`public.type_master`・`public.conditions`・`public.units`・`public.product_format_game_links`・`public.product_blank_confirmations`、それに `_PUBLIC_PRODUCTS_DDL` が作る表のすべて（実装役が DDL を読んで列挙する）。
   - `public.products` に `product_kind_id` 列がある（information_schema.columns）。
   - `public.product_kinds` に code が TCG・FIGURE・GOODS の行が3件ある。
3. `async with public_bootstrap_lock(engine):` の中で2をもう一度確かめる。揃っていなければ `async with engine.begin() as conn:` で次を流す:
   - `SET LOCAL lock_timeout = '60s'`、続けて `LOCK TABLE public.products IN ACCESS EXCLUSIVE MODE`（`backend/tests/rls_bootstrap.py:137-139` と同じ順）。
   - 今の `create_product_schema` にある public の分を、今と同じ順で流す: `_PUBLIC_PRODUCTS_DDL`（2147483647 の札の取り外しも今のまま）、085、086、`20260921_060000`、product_kinds の3行、`20260921_120000`、`20260921_070000`、`type_master_seed_sql()`、`20260919_020000`、`20260922_030000`、`20261016_190000`。phase3 は入れない。
   - 流し方は今の `_exec_multi_stmt` をそのまま使う。

### 7-3. 代替案と選んだ理由
- 選んだ案: 確定させる形。理由: このリポジトリで同じ deadlock を直した手本（ADR-1028 便3）と同じ型で、docstring に理由が書いてある。巻き戻す transaction が持つのは、使い捨てスキーマの表と、外部キーを足すときの products の札だけになる。
- 採らない案1: xact 札を排他にして、相手の試験も札の中で書く。相手になりうる試験（public.products を書く試験すべて）を全部直す必要があり、範囲が分からない。
- 採らない案2: 最初に全部の表を LOCK する。この fixture の中で新しく作る表は先に LOCK できないので、穴が残る。

### 7-4. リスクと対処
- 確定させた public の表が、ほかの試験の前提を変える → 7-2 の表と行は、どれも既にほかの試験か準備が確定させている（recon §6-3）。受け入れ K3 で、全体の passed と skipped の数が main の直近の回と同じことを見る。
- 準備（bootstrap）が public の表を作り直すと、確かめと本番の間に表が消える → 今の荷姿の表と同じ残りの危険。K4 の30回で、A の文面で数える。
- 2147483647 の札は今と同じ使い方にして、変えない。

### 7-5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1: `create_product_schema` の中に public を書く文が残らない | `git diff` で 7-1 の表のとおりか。`create_product_schema` の中で `public.` を grep し、`_rewire_keyword_fks` 以外が0件（Opus） |
| K2: PR の必須チェック pytest が pass する | `gh pr checks` で pytest が pass（Opus）。試験は -q で動き、記録に試験ごとの結果は出ない（review-opus「K3 の確かめ」）ので、ファイルごとの数は K3 で代える |
| K3: 全体の数が変わらない | PR の run の pytest の最後の行が、main の直近の回と同じ passed・skipped の数（Opus）。public の表を確定させると「表が無ければ skip」の試験が変わりうるので、skipped が違ったら原因を探してから進める |
| K4: 合流後の main 30回で、`product_blank_confirmations` か `product_csv_test_` が出る deadlock が0件 | 30回分の失敗の記録を保存して数える（Opus・約1〜2週） |

## 8. 便3: 請求書の表（B）— 直すものは無い
- PR 5669 で直っている（recon §6-1）。合流後の main 25回で0回。
- 受け入れ: §7-5 の K4 と同じ30回で、`tenant_issuer_profiles` が出る deadlock を数える。0件なら済み。

## 9. 便4・便5: カルテと同じ形の2つ（C）と、テナント998（E）を札の中へ入れる
根拠: recon §6-2・§6-4。手本は cc649a9dc のカルテの直し方（札なしの `admin_engine.begin()` を `async with public_bootstrap_lock(admin_engine):` で包む）。

### 9-1. 変更前後
| 場所 | 変更前 | 変更後 |
|---|---|---|
| `backend/tests/test_calendar_sync_tenant_reset_pg.py` `_cleanup`（:72-84） | 札なしの `admin_engine.begin()` | `async with public_bootstrap_lock(admin_engine):` で包む。中の文は変えない |
| 同 `_setup` の、migration の後の `admin_engine.begin()`（public.users の INSERT から tenant_google_calendar_config の INSERT まで） | 札の外 | :95 の札の塊の中へ移す（カルテと同じ） |
| `backend/tests/test_staff_join_discord.py` | 札なし | ファイルの中に小さな関数 `_public_lock(cur)`（contextmanager）を足す。`SELECT pg_advisory_lock(%s, %s)` を取り、finally で `pg_advisory_unlock` する。数は `tests.rls_bootstrap` の `_PUBLIC_BOOTSTRAP_LOCK_NAMESPACE`・`_PUBLIC_BOOTSTRAP_LOCK_KEY` を import して使う（数を直に書かない） |
| 同 `_cleanup_pg`（:582-594） | 札なし | 本体をすべて `with _public_lock(cur):` で包む |
| 同 `_prep_pg` の `public.permissions` と `public.users` の INSERT（:635-646） | 札なし | `with _public_lock(cur):` で包む |
| `backend/tests/test_rls_tenant_meta_config.py` | テナント 998・999 を使う。作る塊（:87-150）と消す塊（:155-157）は札なし | 998→946・999→947 にファイルの中ですべて置き換える（スキーマ名・数・`'page-998-1'` などの文字・SET LOCAL の値・docstring）。作る塊と消す塊を、それぞれ `async with public_bootstrap_lock(admin_engine):` で包む。`from tests.rls_bootstrap import public_bootstrap_lock` を足す |

触らない範囲: `backend/tests/test_countries_master.py`（作るだけで消さない。E の消す側が別の番号になれば、重なりは消える）、ほかの試験ファイル、`backend/tests/rls_bootstrap.py`、製品コード。

### 9-2. 札の順と二重取り
- 3つのファイルとも、テナントの札は取らない（自分専用の番号のため）。public の札だけを取るので、順の決まり（tenant → public）に反しない。
- advisory の札は接続ごとに数える。staff_join は同じ接続 `env.conn` で取るので、`_cleanup_pg` を `_prep_pg` から呼んでも詰まらない（同じ接続での二重取りは数が増えるだけ）。ただし `_prep_pg` で包むのは INSERT の塊だけにして、`_cleanup_pg` の呼び出し（:634）とは重ねない。
- calendar_sync の `_cleanup` を、ほかの札の塊の中から呼ぶ所は無い（呼び元は `_teardown` だけ・recon §6-2）。別の接続で札を二重に取ると自分を待つので、実装役は呼び元を grep で確かめる。

### 9-3. 代替案と選んだ理由
- 選んだ案: 札で包む。理由: 11-05・11-06（PR 5179）と 11-21（PR 5669）に同じ型で直し、直した種類は合流後0回（recon §6-1）。
- 採らない案: 試験ごとに使い捨て DB にする。各試験の作りを大きく変えるうえ、時間が延びる。
- E で番号も変える理由: 札で包むだけでは、countries_master が札なしで同じスキーマを作る形が残る。番号を分ければ、消す側と作る側が別のスキーマになる。

### 9-4. リスクと対処
- 札で包むと、その間ほかの worker の準備が待つ → 包む文は数本の短い DML・DDL なので、待ちは短い。K3 で全体の時間を見る。
- 946・947 がほかで使われていた → recon §6-4 で0件。実装役も `git grep -w -E "946|947"` を流してから変える。

### 9-5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K5: 3ファイルの、共有 DB を書く後片付けと作る塊が、どれも札の中にある | `git diff` が 9-1 の表のとおり（Opus） |
| K6: `backend/tests/test_rls_tenant_meta_config.py` に 998・999 が残らない | `git grep -n -w -E "998|999" -- backend/tests/test_rls_tenant_meta_config.py` が0件（Opus） |
| K7: PR の pytest が pass し、全体の passed・skipped の数が main の直近の回と同じ | `gh pr checks` と PR の run の pytest の最後の行（Opus） |
| K8: 合流後の main 30回で、`public.users` の DELETE・`tenant_946`・`tenant_947`・`tenant_973`・`tenant_978` が出る deadlock か teardown の ERROR が0件 | §7-5 の K4 と同じ記録で数える（Opus） |

## 10. 維持の仕組み（便2〜5）
- 守り手: §7-5 と §9-5 の grep を、受け入れのときに Opus が流す。
- 機械の見張り（札の外で共有 DB の後片付けをする関数を止める試験）は、このテーマでは作らない。試しに探すと53ファイル・76関数が当たり、使い捨て DB か共有 DB かを1つずつ分ける作業が要る（recon §6-5）。PO に次のテーマとして出す。
- KGI の数え方は §5 のとおり。便2〜5の合流がそろった後の main の30回で数える。

## 11. 便2〜5の実装カード（クラウドの担当へ渡す）
共通: 手元で試験は回さない（試験は GitHub の CI で回す）。commit して push する。PR は作らない（Opus が作る）。`git add` するのは本カードに書いたファイルだけ。

### 11-1. カード甲（便2）
- 作業場所: `bash scripts/new-worktree.sh release/ci-test-shared-collisions-design2` で場所を作り、`git switch -C release/ci-test-shared-collisions-design2 origin/release/ci-test-shared-collisions-design2` で合わせる。
- 変更: §7-1・§7-2 のとおり。
- 確かめ:
  1. `git diff --stat origin/main...HEAD -- backend` が `backend/tests/test_tcg_product_list_pg.py` と `backend/tests/test_tenant_loop_migration_guard.py` の2つだけ。
  2. `create_product_schema` の本体で `public.` を grep し、出てくるのが `_rewire_keyword_fks` の呼び出しだけ。
  3. `cd backend && ruff check tests/test_tcg_product_list_pg.py tests/test_tenant_loop_migration_guard.py` が0件。
  4. `cd backend && python -m pytest tests/test_tenant_loop_migration_guard.py -q`（DB を使わない静的な見張り）が pass。
- 想定の分かれ道:
  - 行番号が今の main とずれていた → 中身で場所を決める。中身も違っていたら止めて報告する。
  - 見張りの試験が「phase3 を流すのに登録が無い」などで落ちた → 登録を消した理由（このファイルが phase3 を流さなくなった）を確かめ、落ちる理由が別なら止めて報告する。
  - `_PUBLIC_PRODUCTS_DDL` の表を確定させると products の少列版が作られる形だった → 止めて報告する（ensure_product_packagings が先に本番の形の products を作るので、起きない見込み）。

### 11-2. カード乙（便4・便5）
- 作業場所: `bash scripts/new-worktree.sh release/ci-test-shared-collisions-bin45`（origin/main から）。
- 変更: §9-1 のとおり。
- 確かめ:
  1. `git diff --stat origin/main...HEAD` が3ファイルだけ。
  2. `git grep -n -w -E "998|999" -- backend/tests/test_rls_tenant_meta_config.py` が0件。`git grep -n -w -E "946|947" -- backend migrations scripts .github` が `backend/tests/test_rls_tenant_meta_config.py` だけ。
  3. `cd backend && ruff check tests/test_calendar_sync_tenant_reset_pg.py tests/test_staff_join_discord.py tests/test_rls_tenant_meta_config.py` が0件。
  4. `git grep -n "_cleanup(" -- backend/tests/test_calendar_sync_tenant_reset_pg.py` の呼び元が、札の塊の中に無い。
- 想定の分かれ道:
  - `_PUBLIC_BOOTSTRAP_LOCK_NAMESPACE` などの名前が rls_bootstrap に無かった → 止めて報告する。
  - meta_config の 998・999 が、ほかのファイルの試験と値で結びついていた → 止めて報告する。

## 12. 審査（便2〜5・Opus 自己審査・2026-11-27）
同じ AI による審査で、独立した第二者の審査ではない。
- 便2: 待ち合いの輪（recon §6-3）は「巻き戻す transaction が public の表の ACCESS EXCLUSIVE を持ち続け、さらに別の表の ACCESS EXCLUSIVE を待つ」ことで閉じる。§7 の後、transaction の中で public に取る札は、`_rewire_keyword_fks` が外部キーを足すときの products の SHARE ROW EXCLUSIVE だけになる。これは相手が外部キーの確かめで取る ROW SHARE とぶつからない（PostgreSQL 16 の札の表・explicit-locking.html）。このため、記録で見た輪は閉じない。
- 便2: 確定させる表と行は、どれもほかの試験か準備が既に確定させている（recon §6-3）。数の変化は K3 で見る。
- 便3: 直すものは無い。根拠は合流前後の回数（recon §6-1）。
- 便4・便5: 直し方は、合流後0回になった PR 5179・PR 5669 と同じ型である。札の順の決まり（tenant → public）に反しない（§9-2）。
- 受け入れ基準 K1〜K8 は、どれも差分・grep・CI の記録で ○× を決められる。
- 判定: 便2〜5は APPROVE。
- 未解決: 準備が public の表を作り直す場合の残りの危険（§7-4）。これは K4 の30回で数える。見張りの試験は次のテーマ（§10）。
