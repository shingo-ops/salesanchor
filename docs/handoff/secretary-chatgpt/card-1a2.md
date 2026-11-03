# 実装カード 1a-2: 使用の記録の集計で失敗の行を数えない（`outcome = 'ok'` の条件だけ）

設計者: Opus（2026-11-03）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-2-2・§4-2-3 の終わり「失敗の行で数がずれる集計」・§7 の段1a-2・§10。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が「この設計で決める」に「1」。2026-11-03 PO が「画面ができるまで審査と本番反映まで進める」に「1」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/ai-roster-1a2-outcome-filter` で、HEAD に `docs/handoff/secretary-chatgpt/card-1a2.md` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・SQL・値はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が ready で作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: 集計の条件と、それを確かめる試験だけ。書く側（失敗の行を書く処理）・担当表を読む処理・画面は入れない ○
- 5 起点: ブランチ `release/ai-roster-1a2-outcome-filter` は手元の Opus が origin/main 起点で作って渡す ○
- 6 書式の実例: PR 本文は手元の Opus が書くので載せない（該当なし） ○
- 7 合格基準: ruff の出力の文言・main との差分のファイルの一覧・削除行の数まで書いた。DB の試験の PASSED は CI で手元の Opus が確かめる ○
- 8 名前を出す: 差分の数が違う時は、そのファイルの削除行を出す手順を対にした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 1a-2 の実行結果である」、止まった時は節の番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 場所は前後の文字で決める。数は実物から数える ○

## なぜ（短く）
段1a で使用の記録 `public.llm_usage_events` に `outcome`（`ok`/`failed`）が入った。段1b から失敗の行（`outcome = 'failed'`・費用は NULL）が書かれ始める。今の集計は outcome を見ないので、そのままだと失敗の行を回数に数え、再抽出の道具は「費用が NULL の行がある」で止まってしまう。先に集計へ `outcome = 'ok'` を足しておく。今は失敗の行が0件なので、画面の数は変わらない。

## 禁止（名指し）
- 下の「触るファイル」の7つ以外を変えない。`migrations/`・`scripts/`・`frontend/`・`secretary-agent/`・`.github/`・`deploy.yml`・compose は変えない。
- 書く側（`backend/app/services/llm_budget.py`・`line_analysis_v102_svc.py`・`message_translator.py`・`tcg_extraction_record_svc.py`・`assistant.py`）は変えない（段1b の仕事）。
- `scripts/accuracy/llm_compare/vps_run_gemini.sh` の集計は変えない（`prompt_ab:llmcmp-` の行だけを数え、試験の道具 `prompt_ab` は失敗の行を書かない設計。design.md §4-2-3 の表の「試験の道具」の行）。
- `backend/app/routers/tcg_analysis_dashboard.py` の `daily_requests`・`daily_errors` の集計は変えない（`extraction_attempts` を読んでいて、使用の記録を読まない）。
- 本番に繋がない。本番の鍵を使わない。VPS に入らない。
- PR を作らない・マージしない。GO 記録を書かない。`/review` を実行しない。rebase・force push をしない。`git stash` を使わない。`rm -rf` を使わない。
- 全部の試験を流さない。使い捨ての PostgreSQL・venv を作らない（DB の試験は GitHub の CI で回る）。
- 試験のファイル（`.py`）を書く・直すときは、Write と Edit の道具だけを使う。Bash の python やヒアドキュメントで書き換えない。試験の共有の道具には使い捨て DB を消す後始末の文があり、Bash の命令に入るとクラウドの見張りが止めるため。Bash の命令の文にもその語を書かない。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この7つだけ。ほかに docs/ のこのカード）
1. `backend/app/routers/tcg_analysis_dashboard.py`
2. `backend/app/tools/prompt_ab.py`
3. `backend/app/tools/reextract_v6_with_v102.py`
4. `backend/tests/test_tcg_work_matching_integration.py`（共有の試験 DB に段1a の migration を足す）
5. `backend/tests/test_tcg_analysis_dashboard_cost_summary.py`（1本足す）
6. `backend/tests/test_tcg_analysis_dashboard_llm_usage.py`（1本足す）
7. `backend/tests/test_llm_usage_outcome_filter_pg.py`（新しいファイル）

## 0. 着手前の確かめ（読むだけ。前提が違えば NEEDS_DECISION で止まる）
- 0-1 `git grep -n "llm_usage_events" origin/main -- backend/app ':!*.sql'` を全文報告に写す。集計（SELECT）をしている所が、1 の3つの SQL・2・3 と、`_EVENT_FX_CTE` の中の1つ（`FROM public.llm_usage_events e`）だけであること（ほかはコメント・INSERT・定義）。新しい集計が増えていたら止まる。
- 0-2 `git show origin/main:migrations/20261103_120000_create_ai_job_assignments.sql | grep -n "outcome"` で、`outcome` の列が段1a で作られていること。
- 0-3 `grep -n "_LLM_USAGE_WHERE" backend/app/routers/tcg_analysis_dashboard.py` で、使われている所が定義と `_EVENT_FX_CTE` の中の2か所だけであること。違えば止まる。
- 0-4 `grep -n "LEFT JOIN public.llm_usage_events ue ON ue.extraction_attempt_id = ea.id" backend/app/routers/tcg_analysis_dashboard.py` が3行（`get_cost_summary` の daily・by_supplier・total）。違えば止まる。

## 1. `backend/app/routers/tcg_analysis_dashboard.py`
- 1-1 `async def get_cost_summary(` の直前の `@router.get(` のさらに前（モジュールの定数の位置。前後に空行2つ）に定数を1つ足す:
  ```python
  # ADR-1058 段1a-2: 使用の記録は成功の行（outcome='ok'）だけを結ぶ。失敗の行（段1b から書かれる）は
  # 回数・費用に入れない。条件は WHERE ではなく ON に置く（LEFT JOIN の左の試行の行を落とさないため）。
  _LEDGER_OK_JOIN = "ue.extraction_attempt_id = ea.id AND ue.outcome = 'ok'"
  ```
- 1-2 0-4 の3行の `ON ue.extraction_attempt_id = ea.id` を、それぞれ `ON {_LEDGER_OK_JOIN}` に変える（3つの SQL はすでに `f"""` の文字列。変えるのは ON の後ろだけ）。
- 1-3 `_LLM_USAGE_WHERE = "occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()"` を次にする:
  ```python
  # ADR-1058 段1a-2: 成功の行（outcome='ok'）だけを数える。失敗の行は新しい「AI の担当」画面だけが読む。
  _LLM_USAGE_WHERE = "occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW() AND outcome = 'ok'"
  ```
- ほかの行は変えない。

## 2. `backend/app/tools/prompt_ab.py`
- `_LEDGER_TOTALS_SQL` の `    WHERE source_ref = :source_ref` の行を `    WHERE source_ref = :source_ref AND outcome = 'ok'` に変える。その上のコメント `# 費用は source_ref で絞って合計する（時刻や purpose では絞らない）` の次の行に `# ADR-1058 段1a-2: 成功の行（outcome='ok'）だけ。失敗の行は費用が NULL なので数えると止まる。` を足す。

## 3. `backend/app/tools/reextract_v6_with_v102.py`
- `total_cost` の SQL の `"FROM public.llm_usage_events WHERE source_ref = ANY(:refs) AND occurred_at >= :since"` を `"FROM public.llm_usage_events WHERE source_ref = ANY(:refs) AND occurred_at >= :since AND outcome = 'ok'"` に変える。docstring の最後に `成功の行（outcome='ok'）だけを数える（ADR-1058 段1a-2）。` を足す。

## 4. 共有の試験 DB に段1a の migration を足す `backend/tests/test_tcg_work_matching_integration.py`
今の共有の試験 DB（`pg` fixture）は `20260930_150000_create_llm_usage_events.sql` までしか流さず、`outcome` の列が無い。2・3 の SQL を本物の DB で流す今の試験（`backend/tests/test_prompt_ab.py` の `test_ledger_totals_sum_by_source_ref_on_real_postgres`、`backend/tests/test_reextract_v6_with_v102_pg.py` の `total_cost` を通る試験）が `outcome` の列が無くて落ちるため、段1a の migration を流す。
段1a の migration は `public.users` を外部キーで指すが、共有の試験 DB には `public.users` が無い。表の形を試験に写さず、既にある道具 `tests.rls_bootstrap._ensure_public_users`（閲覧ページの試験 7 ファイルが同じ DB で使っている。`CREATE TABLE IF NOT EXISTS`・`ON CONFLICT` で何度呼んでも同じ）で作る。
- 4-1 `pg` fixture の `migrate(cursor)` の直後（`for module in (analyzer, ...` の前）に、次の順で足す:
  1. 非同期のエンジンを `create_async_engine(url.set(database=name, drivername="postgresql+asyncpg"))` で作り、`async with engine.begin() as aconn: await _ensure_public_users(aconn)` を `asyncio.run` で流し、`finally` で `await engine.dispose()`。前例は `backend/tests/test_viewer_api.py` の `test_pg_login_records_events_in_real_table` の `_prepare`。
  2. `cursor.execute((MIGRATIONS / "20261103_120000_create_ai_job_assignments.sql").read_text())`。
  3. コメント: `# ADR-1058 段1a: 使用の記録の outcome・error_code の列（段1a-2 の集計が読む）。段1a の migration は public.users を指すので、閲覧ページの試験と同じ道具で先に作る。`
- import が足りなければ足す（`asyncio`・`create_async_engine`・`_ensure_public_users`）。ファイルの頭の import の並びに入れる。
- `migrate()` の中身・ほかの fixture は変えない。

## 5. 試験
- 5-1 `backend/tests/test_tcg_analysis_dashboard_cost_summary.py` に1本足す。名前 `test_cost_summary_joins_only_ok_ledger_rows`。今の `test_cost_summary_reads_llm_usage_events_not_input_bytes_estimate` と同じ作りの mock で `get_cost_summary` を呼び、`llm_usage_events` を含む SQL が3つで、3つとも `_LEDGER_OK_JOIN` の文字列そのものを含むこと（`_LEDGER_OK_JOIN in sql` を3つとも満たす）。
- 5-2 `backend/tests/test_tcg_analysis_dashboard_llm_usage.py` に1本足す。名前 `test_llm_usage_ledger_queries_count_only_ok_rows`。今の `test_llm_usage_reads_only_ledger_and_propagates_null` と同じ mock の作りで `get_llm_usage` を呼び、`llm_usage_events` を含む SQL がすべて `outcome = 'ok'` を含むこと（数は実物から数えて assert に書く。0 でないこと）。
- 5-3 新しいファイル `backend/tests/test_llm_usage_outcome_filter_pg.py`。本物の DB は共有の `pg` fixture（`from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture`）。前例は `backend/tests/test_prompt_ab.py` の `test_ledger_totals_sum_by_source_ref_on_real_postgres`。行は `INSERT INTO public.llm_usage_events (purpose, model, sdk, cost_usd, source_ref, extraction_attempt_id, outcome, error_code) VALUES (...)` で入れ、入れた後に commit し、集計は別の取引で流す（`NOW()` は取引の始まりの時刻なので、同じ取引だと `BETWEEN ... AND NOW()` に入らないことがある）。失敗の行は本番と同じく `outcome='failed'`・`error_code='timeout'`・`cost_usd` NULL。成功の行は `outcome='ok'`・`error_code` NULL・`cost_usd` 2。試験は次の4本:
  - (a) `_EVENT_FX_CTE`（`from app.routers.tcg_analysis_dashboard import _EVENT_FX_CTE`）: 成功1行・失敗1行を入れ、`WITH event_fx AS (<_EVENT_FX_CTE>) SELECT count(*), sum(cost_usd) FROM event_fx`（`days=1`）が `(1, 2)`。
  - (b) `_LEDGER_OK_JOIN`: 同じ `extraction_attempt_id`（新しい uuid。共有 DB は試行への外部キーを外してある）で成功1行・失敗1行を入れ、`SELECT count(*), count(ue.id), coalesce(sum(ue.cost_usd), 0) FROM (SELECT CAST(:aid AS uuid) AS id) AS ea LEFT JOIN public.llm_usage_events ue ON <_LEDGER_OK_JOIN>` が `(1, 1, 2)`（試行1つが2行に増えない）。もう1つの uuid で失敗1行だけを入れた時は `(1, 0, 0)`（試行は落ちない）。
  - (c) `prompt_ab.fetch_ledger_totals`: `source_ref='prompt_ab:F'` に成功1行・失敗1行 → `rows == 1`・`null_cost_rows == 0`・`cost_usd == 2`。
  - (d) `reextract_v6_with_v102.total_cost`: `source_ref='extraction_job:<uuid>'` に成功1行・失敗1行 → `(Decimal("2"), 0)`（失敗の行の NULL を数えない＝道具が止まらない）。`since` は入れる前の時刻。
  - purpose は `line_extraction`、sdk は `google-genai`、model は `gemini-3.1-flash-lite`。

## 6. 確かめ方
- `uvx ruff check backend/app/routers/tcg_analysis_dashboard.py backend/app/tools/prompt_ab.py backend/app/tools/reextract_v6_with_v102.py backend/tests/test_tcg_work_matching_integration.py backend/tests/test_tcg_analysis_dashboard_cost_summary.py backend/tests/test_tcg_analysis_dashboard_llm_usage.py backend/tests/test_llm_usage_outcome_filter_pg.py` の出力が `All checks passed!`。
- 新しいファイルは `uvx ruff format --check backend/tests/test_llm_usage_outcome_filter_pg.py` が `1 file already formatted`。ほかのファイルは整形し直さない。各ファイルについて `uvx ruff format --diff` の結果の `^@@` の行の数（`grep -c`）を、変える前（origin/main の写し）と変えた後で比べ、増えていないこと（増えたら足した行を直す）。前と後の数を報告に書く。
- mock の試験（DB 不要）だけ流す: `cd backend && uv run --no-project --with-requirements requirements.txt --with pytest --with pytest-asyncio python -m pytest tests/test_tcg_analysis_dashboard_cost_summary.py tests/test_tcg_analysis_dashboard_llm_usage.py -q`。この形で依存が入らない時は流さずに「mock の試験はクラウドで流せなかった」と書き、CI に任せる（venv は作らない）。流した時は出力を全文写す。
- DB の試験（5-3・今の `pg` を使う試験）はクラウドでは流さない。報告に「DB の試験はクラウドでは流さず CI に任せた」と書く。流していない試験を合格と書かない。
- `bash scripts/dev/check-before-submit.sh` があれば流し、出力の最後の20行と終了コードを写す（無ければ「無い」と書く）。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の7つと `docs/handoff/secretary-chatgpt/card-1a2.md`・`docs/handoff/secretary-chatgpt/design.md` だけ（ほかがあれば止まる）。
- `git diff origin/main...HEAD --numstat` の削除の数（2列目）が、1 は 4（ON の3行と `_LLM_USAGE_WHERE` の1行）、2 は 1、3 は 2 以下（SQL の1行と docstring の閉じの行）、4〜7 は 0。違えば そのファイルを指定した `git diff origin/main...HEAD --` の `^-` の行（`grep` と `head -20`）を出して止まる。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 7. 想定される分岐と止まる条件
- 0 の前提が違う → 止まり、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- 4-1 で `_ensure_public_users` の import や呼び出しが今の形で書けない（名前が違う・同期の関数になっている等） → 止まり、NEEDS_DECISION: で返す。`public.users` を試験の中で自分で CREATE しない（閲覧ページの試験が使う表の形とずれるため）。
- 1・2・3 の文字列が見つからない（カードの前後の文字と違う） → 止まり、NEEDS_DECISION: で返す。
- 5-1・5-2 の mock の作りで SQL の数が実物と違う → 実物の数を assert に書く（0 でないこと）。数は報告に書く。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/ai-roster-1a2-outcome-filter` → `git log origin/release/ai-roster-1a2-outcome-filter -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| 失敗の行を集計に入れない | CI の pytest で 5-3 の4本が PASSED（DB の記録で実行の跡も見る） |
| 今の数が変わらない | CI の pytest で今の dashboard・prompt_ab・reextract の試験がすべて通る。本番は反映の前後で `outcome <> 'ok'` の行が0件（読み取りの道で数える）＝条件を足しても同じ行を数える |
| 差分が7ファイルだけ | `git diff origin/main...HEAD --name-only` |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 1a-2 の実行結果である」。
- 本文: 0-1〜0-4 の生出力、「6. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
