# recon — 試しの道具が取引を開いたまま計算し、本番反映の移行を止める件

- 調べた日: 2026-11-10（JST）。行番号は origin/main 96a63df05。
- 調べた人: Claude Opus（設計担当）。本番は読むだけ（ssh prod1 の cat・ls・pg_settings の SELECT）。
- 生出力: /tmp/CC報告ファイル/dockerd-bin0/deploy/（replay_words.py.txt・remote_replay.sh.txt・v102_replay_diff.py・v102_svc.py・tcg_extraction.py）、/tmp/CC報告ファイル/deploy-lock-1109/summary.md（別セッションの同じ件の調べ）

## 0. 既存 ADR・設計の検索

- `git grep -il "idle in transaction\|idle_in_transaction" origin/main -- docs/adr` → ADR-1070 だけ（接続の返却時の後始末。この件の道具の取引の長さは扱わない）。
- ADR-1037（docs/adr/ADR-1037-migration-lock-timeout.md）: 移行の鍵待ちは 1 秒・3 秒あけて再試行・1 回の実行で合計 40 回まで。
- docs/handoff/deploy-db-stall/design.md §17（段4）: 全接続に名前を付ける。名前の正本は 1 つの表（17-2）。手で流す道具の名前は範囲外（17-7）。idle_in_transaction_session_timeout はアプリの動きを変えるので段4に入れない（17-7）。
- docs/handoff/migration-runner-redesign/design.md §5（段5）: 全件の流し直しをやめる。設計審査済み・実装前。

## 1. 起きたこと（事実）

| 時刻（UTC） | 出来事 | 根拠 |
|---|---|---|
| 2026-11-09 09:18:33 | prod1 で remote_replay.sh が起動。condwords-replay の箱で 6 回（base1・base2・A・B・C・ALL）を順に流す | /home/ubuntu/fhd-test/condwords/remote.log・base1.stderr 先頭 |
| 10:07〜11:42 | Deploy to VPS が 7 回続けて failure（42598520163〜42609226129） | `gh run list --workflow deploy.yml` |
| 12:02 | 6 回目 ALL が終わる。run.out は 6 回とも exit=0 | /home/ubuntu/fhd-test/condwords/run.out |
| 12:37:51 | 42612168629 の 2 回目が success（移行のロック待ち 0 件） | 同上の run 一覧・memory deploy_db_stall |

- 失敗した回はどれも `scripts/migrate_inventory_sprint1.py` の `DROP TRIGGER … ON public.suppliers` でロック待ちの総数 40/40（/tmp/CC報告ファイル/deploy-lock-1109/summary.md A 節）。
- 握っていたのは接続元 172.19.0.12＝condwords-replay の箱。state は idle in transaction、最後の文は投稿日を読む SELECT（同 summary・memory deploy_db_stall 11/9 22:3x の裏取り）。
- 再生 1 回は投稿 134 件で約 25 分（base1.stderr 09:18:53〜09:43:37、base1.stdout `{'posts': 134, 'items': 6513, 'errors': 0}`）。1 投稿あたり約 11 秒。

## 2. 仕組み（事実・行番号つき）

### 2-1. 再生の道具（v102_replay_diff）

- `backend/app/tools/v102_replay_diff.py:100-129` replay(): 投稿ごとに replay_post を呼び、finally で `session.rollback()`（:120）。取引を閉じるのは 1 投稿の処理が全部終わった後だけ。
- `backend/app/tools/v102_replay_diff.py:77-97` replay_post(): DB を読む（:82 文脈・:85 投稿・:86 件・:90 人の判断・:93 直前の投稿・:93 〆の参照・:94 投稿日）→ 読み終わった後に :96 `svc.run_v102_pipeline(...)`（DB を使わない計算）。
- つまり :94 の後から :120 まで、計算の間ずっと「取引を開いたまま待つ」状態になる。最後の文が投稿日の SELECT（`backend/app/services/line_analysis_v102_svc.py:1509-1513` `_POSTED_AT_SQL`）なのはこのため。
- 取引の中で読んだ表（public.suppliers・knowledge_rules など）の AccessShareLock は取引の終わりまで残る（PostgreSQL の表の鍵の決まり）。
- 再生の台本 replay_words.py（prod1 /home/ubuntu/fhd-test/condwords/replay_words.py、別セッションの枝 origin/release/condition-abbr-trial の scripts/accuracy/condition_words/replay_words.py）は :99 で `v102_replay_diff.replay` を呼ぶだけ。取引の扱いは v102_replay_diff の作りがそのまま効く。:97-98 で `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` を commit で確定させている。

### 2-2. 計算の前に取引を閉じても結果が変わらないか

- run_v102_pipeline は session を受け取らない（`backend/app/services/line_analysis_v102_svc.py:355` の定義、呼び出し :1570・`backend/app/tools/v102_replay_diff.py:96`）。
- 計算に渡る値はどれも DB の物ではなく、ただの値:
  - 文脈: `backend/app/tasks/tcg_extraction.py:256-264` ExtractionContext は NamedTuple、:267-316 で text() の行から組み立てる。
  - 人の判断: `backend/app/services/v102_human_decisions_svc.py:231-` text() の行から dict を作る。session.query・scalars・session.get は 0 件（grep -c）。
  - line_analysis_v102_svc.py の中も session.query・relationship は 0 件（grep -c）。
- よって rollback の後に計算しても、計算が DB を読み直すことは無い（ORM の物の期限切れの読み直しが起きない）。
- `SET SESSION CHARACTERISTICS … READ ONLY` は commit で確定した接続の設定なので、rollback では消えない。

### 2-3. 同じ型の道具（計算・外の呼び出しの間に取引を開いたまま）

| 道具 | 取引を開いたまま待つ所 | 根拠 |
|---|---|---|
| v102_replay_diff | 投稿日を読んだ後〜後処理の計算の終わり（約 11 秒/投稿） | `backend/app/tools/v102_replay_diff.py:94-120` |
| prompt_ab_recompute | 投稿日を読んだ後〜後処理の計算の終わり（1 行ごと） | `backend/app/tools/prompt_ab_recompute.py:87-90`。失敗のときだけ :111 で rollback。成功の行では rollback しないので、次の行の読み取りに取引が続く |
| prompt_ab | 文脈を読んだ後・費用の合計を読んだ後〜Gemini の呼び出しの終わり（数十秒/回） | `backend/app/tools/prompt_ab.py:537`（文脈）・:602（合計の SELECT の後に取引が残る）→ :549/:556（Gemini） |
| fhd_snapshot | 1 回の REPEATABLE READ・READ ONLY の取引で全部を判定（わざと 1 つの写しで読む・R5） | `scripts/accuracy/llm_compare/fhd_snapshot.py:148-149`・:228 |
| 本番の解析 run_v102_analysis | 読み取り〜計算〜書き込み〜commit（書き込みがあり、投稿ごとの鍵も取る） | `backend/app/services/line_analysis_v102_svc.py:1539-1572` |

### 2-4. DB の設定（本番）

- prod1 の PostgreSQL 16.13: `idle_in_transaction_session_timeout=0`（無効）・`lock_timeout=0`・`statement_timeout=0`（pg_settings、2026-11-10 01:2x JST）。
- `idle_in_transaction_session_timeout` と `application_name` の context は user＝接続ごとに SET で変えられる（同上）。
- PostgreSQL 公式: idle_in_transaction_session_timeout は「開いた取引の中で待っている時間が指定を超えた接続を終わらせる。0 で無効」（https://www.postgresql.org/docs/current/runtime-config-client.html 、Context7 /websites/postgresql で確認）。
- SQLAlchemy 2.0 公式: Session は最初の execute で自動で取引を始め（autobegin）、`Session.in_transaction()` で取引中かを返す。rollback は取引が無ければ何もしない（Context7 /websites/sqlalchemy_en_20_orm で確認）。

### 2-5. 本番反映の側（参考・この設計では変えない）

- `scripts/run_all_migrations.sh:56-60` 鍵待ち 1 秒・3 秒あけ・合計 40 回。:68 は待ちで失敗したとき、1 秒を超えて取引を持つ接続の application_name・握っている表をログに出す。
- 本番反映は前回の成功から sha が変わると移行を全件流し直す（summary.md A 節）。そのため DROP TRIGGER を毎回流し、毎回 suppliers の強い鍵を取りに行く。これは段5（migration-runner-redesign §5）の範囲。

## 3. 未確認

- [?] load_v102_masters（`backend/app/services/line_analysis_v102_svc.py:217-`）の文と文の間で、Python の処理のために取引を開いたまま待つ時間の最長。→ 設計 §5 の P1 で本番の基準値の回に測る。
- [?] 修正後の 1 投稿の読み取りにかかる時間（取引の長さ）。→ 同じく P1 と K2 で測る。
- [?] 11/9 18:53 JST（09:53Z）より前の失敗 42596881194 が再生と重なっていたか。再生の開始 09:18Z より後なので時刻は重なる。握り手が condwords-replay だったかは、その回のログを読んでいない。
