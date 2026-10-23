<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — ai-ro-restore-on-failure

**仕事名**: 入れ替えが途中で失敗しても AI 用の読み取りビュー（ai_ro）をその場で作り直す  
**日付**: 2026-10-21  
**対象ADR**: ADR-1024（ai_ro を決めた）、ADR-1037（移行の鍵待ち1秒）  
**担当**: Planner（Opus）。調べたのは Sonnet。基準は origin/main d7c5dc2e4

既存 ADR の検索: `git grep -n -i "ai_ro" origin/main -- docs/adr/` の結果は ADR-1024:6,31,80,89,92、ADR-1026:8,36、ADR-1028:8、ADR-1030:8、ADR-1037:42（2026-10-21 に流し直した）。ADR-1026:36 は「先頭で外し最後に作るので DROP COLUMN がビューに止められない」ことを根拠にしている。今回は外す・作る順番を変えないので影響は無い（その行が指す台本の行番号 :80,86-106 は今は古いが、本件の範囲外）。ADR-1028:8・ADR-1030:8 は関連欄に名前があるだけ。docs/adr/FEATURE-INDEX.md に ai_ro の行は無い。「失敗したら作り直さない」を決めた ADR・設計書の記述は無い（`git grep -n "fail-closed\|外したまま" origin/main -- docs/` で探した。ADR-1024:31 の fail-closed は「新しい表はビューを作るまで読めない」の意味）。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:20` | `set -e`。どこかの run_sql が 0 以外を返すと、その場でスクリプトが終わる |
| `scripts/run_all_migrations.sh:119` | 一覧の先頭でビューを外す（`run_sql migrations/20261017_125900_drop_ai_ro_views.sql`） |
| `scripts/run_all_migrations.sh:121` | :121-122 のコメント「スクリプトが正常終了（rc=0）したときだけ、常に最後に流す」 |
| `scripts/run_all_migrations.sh:123` | コメント「途中で失敗した場合はビューを外したままにする（fail-closed）」。理由はこの1行だけ |
| `scripts/run_all_migrations.sh:124` | コメント「作成に失敗したら exit 1」。実際は :136 と :141 で exit 0 になり、コメントと食い違う |
| `scripts/run_all_migrations.sh:129` | `if [ "${rc}" -ne 0 ]; then`。失敗のときはここで止まる |
| `scripts/run_all_migrations.sh:130` | `skip ai_ro views (script failed rc=${rc}; views stay dropped)` を出す |
| `scripts/run_all_migrations.sh:131` | `exit "${rc}"`。作成しないまま、元の終了コードで終わる |
| `scripts/run_all_migrations.sh:139` | 作成は `docker exec -i "${POSTGRES}" ${PSQL} < 作成SQL`。run_sql を通らないので、lock_timeout も流し直しも無い |
| `scripts/run_all_migrations.sh:145` | `trap _ai_ro_create_on_exit EXIT`。ビューを外した後（:119）に登録している |
| `scripts/run_all_migrations.sh:1037` | ai_reader ロールの作成は一覧の後ろの方 |
| `migrations/20261017_130100_create_ai_ro_views.sql:6` | `BEGIN;`。:81 の `COMMIT;` までトランザクション1つ |
| `migrations/20261017_130100_create_ai_ro_views.sql:8` | `DROP SCHEMA IF EXISTS ai_ro CASCADE;`。作成SQLだけで何度流しても同じ結果になる |
| `migrations/20261017_130100_create_ai_ro_views.sql:23` | 秘密列の拒否リストの正本（`deny` の正規表現） |
| `migrations/20261017_130100_create_ai_ro_views.sql:29` | :29-30。対象の表は、その時点の pg_class にある public と tenant_* の通常表・分割表 |
| `migrations/20261017_130100_create_ai_ro_views.sql:62` | 1本ずつの CREATE VIEW は EXCEPTION WHEN others で受ける。1本が失敗しても、その表だけ読めなくなる（:68-71） |
| `migrations/20261017_130100_create_ai_ro_views.sql:74` | `RAISE NOTICE 'ai_ro views created: %, columns excluded: %, failed: % [%]'` |
| `migrations/20261017_130100_create_ai_ro_views.sql:78` | `GRANT USAGE ON SCHEMA ai_ro TO ai_reader;`。ロールが無ければ全体がロールバックされる |
| `backend/app/ops/readonly_query.py:6` | ai_ro を読むのはこの台本（AI の読み取りの道）だけ。backend/app に ai_ro を読む箇所は他に無い |
| `docs/adr/ADR-1024-ai-readonly-db-path.md:31` | 「ビューは `scripts/run_all_migrations.sh` の最後で作り直す」 |
| `docs/adr/ADR-1037-migration-lock-timeout.md:42` | 便1の失敗のとき、ビューが外れて次の入れ替えで戻ったことの記録 |
| `tests/sandbox/migration-run-sql-retry.sh:1` | run_sql を抜き出して試す既存の試験。trap と作成は試していない |
| `.github/workflows/sandbox-test.yml:1` | 手動実行で tests/sandbox/<name>.sh を ubuntu-latest で流す |

## 観測した事実（本番・ログ・使い捨て DB）

- F1 直近300回の入れ替え（10/15〜10/21）: success 290、failure 9、cancelled 1。failure のうち8件は「Run database migrations」で落ちた。8件とも、ログに「skip ai_ro views」が出ている（落ちるたびに外れたまま）。生出力は /tmp/CC報告ファイル/ai-ro-restore/（リポジトリ外）。
- F2 10/21 の失敗回（run 39575250541）の流れ。
  - 09:16:49Z: ビューを外した。
  - 09:22:55Z: 上限で停止し、「skip ai_ro views (script failed rc=3; views stay dropped)」を出した。
  - 09:29:52Z: 次の成功回で戻った。外れていたのは約13分。
- F3 成功回（run 39584411250）の作成は 10:29:42.74Z〜10:29:43.40Z の約0.7秒。結果は「ai_ro views created: 511, columns excluded: 62, failed: 0 []」。
- F4 本番（reader の道、2026-10-21T11:52Z）: ai_ro のビューは511本で、ai_reader ロールはある。
- F5 使い捨て DB（PostgreSQL 16.15）での実測。台本と出力は /tmp/CC報告ファイル/ai-ro-restore/lab/（リポジトリ外）。
  - CREATE VIEW が元の表に取る鍵は AccessShareLock だけだった。新しいビュー自身には AccessExclusiveLock を取る。
  - DROP SCHEMA ai_ro CASCADE は、元の表に鍵を取らなかった。
  - ほかの接続が元の表を ACCESS SHARE（読み取り中）で持っていても、CREATE VIEW は待たずに309msで終わった。
  - ほかの接続が ACCESS EXCLUSIVE を持っていると、CREATE VIEW は待った（4064ms）。
- F6 PostgreSQL 16 の公式文書（https://www.postgresql.org/docs/16/explicit-locking.html、2026-10-21 に確認）。
  - ACCESS SHARE は「`ACCESS EXCLUSIVE` だけと衝突する」。
  - CREATE VIEW がどの鍵を取るかは、この頁に書いていない。そのため F5 で実測した。
  - Context7 は月の上限に達していて使えなかった。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 外したままにする理由は、秘密を守るためか | ADR・設計書を検索した（上記）。拒否リストは列名とカタログだけで決まり、いつ流しても同じ（create SQL :23,:29） | ✅ 解消済み（守りの理由は無い。コードのコメントだけ） |
| 2 | 失敗の後に作ると、在庫表を待たせるか | F5・F6。作成は元の表に ACCESS SHARE しか取らない。ACCESS SHARE は ACCESS EXCLUSIVE とだけ衝突する。作成が待つ場面では、後から来た読み取りも同じ ACCESS EXCLUSIVE を待つ。作成のせいで増える待ちは無い | ✅ 解消済み（試験 T5 で実測して確かめる） |
| 3 | ai_reader ロールが無いとき | create SQL :78。全体がロールバックされ、ビューは0本になる（今の失敗時と同じ結果）。本番にはロールがある（F4） | ✅ 解消済み |
| 4 | 他にビューを使う仕組み | readonly_query.py だけ（:6）。compose に ai_ro の文字は無い | ✅ 解消済み |
| 5 | 移行ステップが打ち切られた（10分）・信号で止まったときに trap が動くか | 設計審査の実測（macOS bash 3.2）: SIGTERM・SIGHUP で EXIT trap が rc=0 として動き、今の作りでも作成に進んだ。本番の bash 5 は未確認。ssh-action の打ち切りで遠隔の台本に信号が届くかも未確認 | 対象外（設計 §2）。試験 T8 で ubuntu の bash 5 の動きを記録だけする |

**未解決ゼロ確認**: 1〜4 は解消済み。5 は対象外として設計 §2 に事実と未確認を書いた
