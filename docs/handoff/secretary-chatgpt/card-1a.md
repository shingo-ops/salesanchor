# 実装カード 1a: AI の担当の表3つと使用の記録の列を足す（migration だけ・コードは変えない）

設計者: Opus（2026-11-03）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-1・§4-2-1・§7 の段1a。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が「この設計で決める」に「1」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md・guards/07-migration.md（照合: 新しいファイルは丸ごと書く／run_all_migrations.sh に run_sql を登録する／直近の migration の名前を実物で確かめてから名前を決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが release/ai-roster-1a-migration で、HEAD に docs/handoff/secretary-chatgpt/card-1a.md があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・SQL の名前・値はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が ready で作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: migration と分類表と試験だけ。コード・画面・容器は入れない ○
- 5 起点: ブランチ `release/ai-roster-1a-migration` は手元の Opus が origin/main 起点で作って渡す（クラウドは作らない） ○
- 6 書式の実例: PR 本文は手元の Opus が書くので、このカードには載せない（該当なし） ○
- 7 合格基準: 終了コードだけでなく、ruff の出力の文言・main との差分のファイルと削除行の数まで書いた。DB の試験の PASSED は CI で手元の Opus が確かめる ○
- 8 名前を出す: 件数で止める所は、該当の表名・列名を出す手順を対にした ○
- 9 出力の上限: 一覧は `--json` と `grep` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 1a の実行結果である」、止まった時は手順番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 行番号ではなく前後の文字で場所を決める。数は実物から数える ○

## 禁止（名指し）
- `backend/app/`・`frontend/`・`secretary-agent/`・`deploy.yml`・compose のファイルを変えない（この便はコードを変えない）。`.github/workflows/` は `migration-guard.yml` の `PUBLIC_TABLES` の1行（3-2）だけ変えてよい。ほかのワークフローは変えない。
- `docs/handoff/cloud-case-ai/stage1-column-class.tsv` は変えない（分類の正本は migration の SQL。この表を読む試験や台本は無い）。
- 本番に繋がない。本番の鍵を使わない。VPS に入らない。
- PR を作らない・マージしない。GO 記録を書かない。`docs/ai-agents/evidence-registry.md` に書かない。
- `/review` を実行しない。rebase・force push をしない。
- 全部の試験を流さない（流すのは「5. 確かめ方」に書いたものだけ。DB の試験は GitHub の CI で回る）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 0. 着手前の確かめ（読むだけ。前提が違えば NEEDS_DECISION で止まる）
- 0-1 `git show origin/main:docs/handoff/secretary-chatgpt/design.md | head -3` で設計書が main にあること。無ければ止まる（設計の PR がまだ合流していない）。
- 0-2 `git ls-tree --name-only origin/main migrations/ | tail -3` で一番新しい migration の名前を出す。`20261103_120000` より新しい名前があれば、この便のファイル名の時刻をそれより後に直して続ける（名前は報告に書く。以下のカードの中の `20261103_120000_create_ai_job_assignments.sql` もすべてその名前に読み替える）。
- 0-3 `git show origin/main:migrations/20260930_150000_create_llm_usage_events.sql` の `llm_usage_events_purpose_check` と `llm_usage_events_sdk_check` の中身を報告に写す。今の値は purpose が `line_extraction`・`line_extraction_shadow`・`inventory_parse_fallback`・`translation_inbound`・`translation_inbound_escalation`・`translation_outbound`、sdk が `google-genai`・`google-generativeai`。ほかの migration がこの2つを作り直していないことを `git grep -n 'llm_usage_events_purpose_check\|llm_usage_events_sdk_check' origin/main -- migrations` で確かめる（出てくるのは `20260930_150000` と `20261024_100300` の2つだけのはず）。違えば止まる。
- 0-4 `git show origin/main:migrations/20261024_100300_create_ai_cloud_views.sql | sed -n '1,5p'` と `git show origin/main:backend/tests/ops/test_ai_cloud_views.py | grep -n '== n0 =='` で、分類表の今の行数（今は 1057）を出す。以下ではこの数を N と書く。
- 0-5 `python3 scripts/check-migration-value-writes.py repo` を流し、今の main で通ることを報告に写す（通らなければ止まる）。

## 1. 新しい migration `migrations/20261103_120000_create_ai_job_assignments.sql`（1つのファイル）
頭に、何をするか・流し直しても壊れない理由・戻し方（PO が流す。下の「戻し方」）をコメントで書く。前例の書き方は `migrations/20261020_110000_line_conditions_value_group_add_supply.sql` の頭のコメント。

1-1 表 `public.ai_job_choices`（`CREATE TABLE IF NOT EXISTS`）
- 列: `id SERIAL PRIMARY KEY`・`job_key TEXT NOT NULL`・`provider TEXT NOT NULL`・`model TEXT NOT NULL`・`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- 制約（表を作る文の中で名前を付けて作る）:
  - `CONSTRAINT ai_job_choices_job_key_check CHECK (job_key IN ('line_extraction','translation_inbound','translation_inbound_escalation','translation_outbound','secretary_intent'))`
  - `CONSTRAINT ai_job_choices_provider_check CHECK (provider IN ('gemini','codex','claude'))`
  - `CONSTRAINT ai_job_choices_job_provider_model_key UNIQUE (job_key, provider, model)`
  - `CONSTRAINT ai_job_choices_id_job_key_key UNIQUE (id, job_key)`

1-2 表 `public.ai_job_assignments`（`CREATE TABLE IF NOT EXISTS`）
- 列: `job_key TEXT PRIMARY KEY`・`choice_id INTEGER NOT NULL`・`updated_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL`・`updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- 制約: `CONSTRAINT ai_job_assignments_job_key_check CHECK (job_key IN (...1-1 と同じ5つ...))`・`CONSTRAINT ai_job_assignments_choice_fkey FOREIGN KEY (choice_id, job_key) REFERENCES public.ai_job_choices (id, job_key)`

1-3 表 `public.ai_job_assignment_history`（`CREATE TABLE IF NOT EXISTS`）
- 列: `id SERIAL PRIMARY KEY`・`job_key TEXT NOT NULL`・`old_choice_id INTEGER NOT NULL REFERENCES public.ai_job_choices(id)`・`new_choice_id INTEGER NOT NULL REFERENCES public.ai_job_choices(id)`・`changed_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL`・`changed_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- 制約: `CONSTRAINT ai_job_assignment_history_job_key_check CHECK (job_key IN (...1-1 と同じ5つ...))`
- 索引: `CREATE INDEX IF NOT EXISTS ix_ai_job_assignment_history_job_key_changed_at ON public.ai_job_assignment_history (job_key, changed_at)`

1-4 履歴の書き換え・消しを止めるトリガー
- `CREATE OR REPLACE FUNCTION public.ai_job_assignment_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$ ... $$`
  - `TG_OP = 'UPDATE'` で、`NEW.changed_by IS NULL` かつ `OLD.changed_by IS NOT NULL` かつ ほかの列（id・job_key・old_choice_id・new_choice_id・changed_at）が `OLD` と全部同じ（`IS NOT DISTINCT FROM`）なら `RETURN NEW`（users を消した時の SET NULL を通すため）。
  - それ以外（UPDATE・DELETE・TRUNCATE）は `RAISE EXCEPTION 'ai_job_assignment_history is append-only'`。
- `CREATE OR REPLACE TRIGGER ai_job_assignment_history_no_change BEFORE UPDATE OR DELETE ON public.ai_job_assignment_history FOR EACH ROW EXECUTE FUNCTION public.ai_job_assignment_history_guard()`
- `CREATE OR REPLACE TRIGGER ai_job_assignment_history_no_truncate BEFORE TRUNCATE ON public.ai_job_assignment_history FOR EACH STATEMENT EXECUTE FUNCTION public.ai_job_assignment_history_guard()`

1-5 初めの行（`INSERT ... ON CONFLICT DO NOTHING`。流し直しで上書きしない）
- `ai_job_choices` に 17 行:
  - `line_extraction` / `gemini` / `gemini-3.1-flash-lite`
  - `translation_inbound`・`translation_inbound_escalation`・`translation_outbound` のそれぞれに `gemini` / `gemini-2.5-flash`・`gemini-2.5-pro`・`gemini-2.5-flash-lite`・`gemini-3.1-flash-lite`・`gemini-3.5-flash-lite`（3 × 5 = 15 行）
  - `secretary_intent` / `claude` / `sonnet`
  - codex の行は入れない（段3で足す）。
  - 5つのモデル名は、書く前に `git show origin/main:backend/app/services/llm_budget.py` の `LLM_PRICING` の見出しの名前と1字ずつ同じか確かめ、違えば止まる。
- `ai_job_assignments` に 5 行。choice_id は `id` を書かず、`(SELECT id FROM public.ai_job_choices WHERE job_key = ... AND provider = ... AND model = ...)` で引く:
  - `line_extraction` → `gemini` / `gemini-3.1-flash-lite`
  - `translation_inbound`・`translation_inbound_escalation`・`translation_outbound` → `gemini` / `gemini-3.5-flash-lite`
  - `secretary_intent` → `claude` / `sonnet`
  - `updated_by` は NULL。`ON CONFLICT (job_key) DO NOTHING`。

1-6 使用の記録 `public.llm_usage_events` の列を足す
- `ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS outcome TEXT NOT NULL DEFAULT 'ok' CONSTRAINT llm_usage_events_outcome_check CHECK (outcome IN ('ok','failed'))`
- `ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS error_code TEXT NULL CONSTRAINT llm_usage_events_error_code_check CHECK (error_code IS NULL OR error_code IN ('auth_failed','timeout','rate_limited','http_error','unreadable','tool_used','not_ready','busy','other'))`
- 2つの列にまたがる決まりは表の制約にする（設計 §4-1 の「受け付けない時」の形を最初から使う。列の制約の形は使わない）。DO の塊の中で、`pg_constraint` に `conrelid = 'public.llm_usage_events'::regclass` かつ `conname = 'llm_usage_events_outcome_error_code_check'` が無い時だけ、`ALTER TABLE public.llm_usage_events ADD CONSTRAINT llm_usage_events_outcome_error_code_check CHECK ((outcome = 'ok' AND error_code IS NULL) OR (outcome = 'failed' AND error_code IS NOT NULL))`

1-7 今ある CHECK を広げる（前例 `20261020_110000_line_conditions_value_group_add_supply.sql` の DO の塊と同じ形。DROP と ADD は1つの DO の文の中に入れる）
- purpose: `pg_get_constraintdef` が `secretary_intent` を含めば何もしない。含まない時だけ、`DROP CONSTRAINT llm_usage_events_purpose_check` → `ADD CONSTRAINT llm_usage_events_purpose_check CHECK (purpose IN ('line_extraction','line_extraction_shadow','inventory_parse_fallback','translation_inbound','translation_inbound_escalation','translation_outbound','secretary_intent'))`。
- sdk: `pg_get_constraintdef` が `codex-cli` と `claude-code` の両方を含めば何もしない。どちらかが無い時だけ `DROP` → `ADD CONSTRAINT llm_usage_events_sdk_check CHECK (sdk IN ('google-genai','google-generativeai','codex-cli','claude-code'))`。
- 一度流れた後は `secretary_intent`・`codex-cli`・`claude-code` が定義に入っているので、流し直しでは何もしない。後の migration が値をさらに足していても、足した値は消えない（4-2 の (c) で確かめる）。

1-8 権限（前例 `migrations/20261101_130000_add_new_device_approval.sql` の `pg_roles` の塊と同じ形）
- `salesanchor_app` がある時だけ: 3表に `SELECT, INSERT, UPDATE, DELETE`、`public.ai_job_choices_id_seq`・`public.ai_job_assignment_history_id_seq` に `USAGE, SELECT`。

戻し方（コメントに書く。流すのは PO）: トリガー2つと関数を DROP → 3表を `ai_job_assignment_history`・`ai_job_assignments`・`ai_job_choices` の順に DROP → `llm_usage_events_outcome_error_code_check` を DROP → 列 `error_code`・`outcome` を DROP → purpose と sdk の CHECK を 0-3 の値に戻す（`secretary_intent`・`codex-cli`・`claude-code` の行が残っていれば先に止まる、と書く）。

## 2. 登録 `scripts/run_all_migrations.sh`
最後の `run_sql migrations/...` の行の後に、説明のコメント1行と `run_sql migrations/20261103_120000_create_ai_job_assignments.sql` の2行を足す。コメントの例（前の行と同じ形）:
`# ADR-1058 段1a: AI の担当の表3つ（選択肢・今の担当・変えた記録）と使用の記録の outcome・error_code（追加と CHECK を広げるだけ・冪等）`

## 3. 相談係の分類表 `migrations/20261024_100300_create_ai_cloud_views.sql`
- 行を7つ足す（今の行と同じ形 下の7行の形（表・列・class・理由）。並びは表の名前の順の場所に入れる）:
  - `('public','ai_job_assignment_history',ARRAY['job_key'],'allow','値の決まり ai_job_assignment_history_job_key_check で値が限られる')`
  - `('public','ai_job_assignments',ARRAY['job_key'],'allow','値の決まり ai_job_assignments_job_key_check で値が限られる')`
  - `('public','ai_job_choices',ARRAY['job_key'],'allow','値の決まり ai_job_choices_job_key_check で値が限られる')`
  - `('public','ai_job_choices',ARRAY['provider'],'allow','値の決まり ai_job_choices_provider_check で値が限られる')`
  - `('public','ai_job_choices',ARRAY['model'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）')`
  - `('public','llm_usage_events',ARRAY['outcome'],'allow','値の決まり llm_usage_events_outcome_check で値が限られる')`
  - `('public','llm_usage_events',ARRAY['error_code'],'allow','値の決まり llm_usage_events_error_code_check で値が限られる')`
- 頭のコメントの「N 行」と、`backend/tests/ops/test_ai_cloud_views.py` の `== n0 == N` を、N+7 に直す。

## 3-2. migration の守りの登録（2つ。前例は ADR-1055 段W の commit 77e5df4fc）
- `scripts/migration-guard/reference-allowlist.tsv`: `migrations/20261024_100300_create_ai_cloud_views.sql` の行の sha256 を、3 を直した後の `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値に直す。同じ行の decision_ref の最後に ` / ADR-1058 段1a（分類7行追加）` を足す。ほかの行は変えない。直した後に `python3 scripts/check-migration-value-writes.py repo` が通ること。
- `.github/workflows/migration-guard.yml`: `PUBLIC_TABLES="..."` の1行の最後（閉じる `"` の前）に、半角空白で区切って `ai_job_choices ai_job_assignments ai_job_assignment_history` を足す。ほかの行は変えない。

## 4. 試験
4-1 `backend/tests/ops/test_ai_cloud_views.py` に1本足す。前例は同じファイルの `test_t10_new_device_approval_columns_are_classified_on_bootstrapped_db`（ADR-1055 段A）と `test_t10_web_push_columns_are_classified_on_bootstrapped_db`。
- 名前: `test_t10_ai_job_assignment_columns_are_classified_on_bootstrapped_db`
- 定数 `_AI_JOB_SQL = "20261103_120000_create_ai_job_assignments.sql"`、`_PIPELINE_PUBLIC_SQL = "20260921_110000_pipeline_tables_public.sql"`、`_LLM_USAGE_SQL = "20260930_150000_create_llm_usage_events.sql"` をファイルの頭の定数の並びに足す。
- 流す順: 専用の DB → `_AI_READER_SQL`・`_ROLE_SQL`・`_META_SQL` → `bootstrap_tenant_schema` → `_PIPELINE_PUBLIC_SQL` → `_LLM_USAGE_SQL` → `_AI_JOB_SQL` を2回 → `_CREATE_SQL`。表の形を試験の中に写さない。この順で流れない時は止まる（設計の前提が違う）。
- 確かめること: column_class に3の7つが表名・列名で全部ある。`_classification_gaps` のうち表名が `ai_job_choices`・`ai_job_assignments`・`ai_job_assignment_history`・`llm_usage_events` のものが0件（0件でない時は、その表名・列名を assert の文に出す）。

4-2 新しいファイル `backend/tests/ops/test_ai_job_assignments_db.py`。下準備（`ADMIN_PG_URL`・`pytestmark` の skipif・専用の DB を作って終わりに消す・`_read`）は `backend/tests/ops/test_ops_case_db.py` と `test_ai_cloud_views.py` の形を写す。DB は 4-1 と同じ順（`_CREATE_SQL` は不要）で作る。試験は次の5本:
- (a) 行の数: 流した後、`ai_job_choices` が17行、`ai_job_assignments` が5行、`ai_job_assignment_history` が0行。担当5行の provider と model が 1-5 のとおり。
- (b) 流し直しで値が戻らない: 1回流す → `UPDATE public.ai_job_assignments SET choice_id = (translation_outbound の gemini-2.5-flash の id) WHERE job_key = 'translation_outbound'` → もう1回流す → `translation_outbound` が gemini-2.5-flash のまま。行の数は (a) と同じ。
- (c) 後の migration が CHECK を広げていても壊れない: 1回流す → purpose の CHECK を DROP して、7つに `test_future_purpose` を足した CHECK を ADD → その purpose の行を1行 INSERT → もう1回流す → 例外なく通り、`pg_get_constraintdef` に `test_future_purpose` が残る。sdk にも同じ形で `test_future_sdk` を足して同じことを確かめる。
- (d) 履歴は足すだけ: 履歴に1行 INSERT した後、UPDATE（job_key を変える）・DELETE・`TRUNCATE` がそれぞれ例外になる。`users` の1行を消すと（その人を changed_by にした行を作っておく）例外にならず changed_by だけが NULL になる。
- (e) outcome と error_code: `outcome='ok'` かつ `error_code='timeout'`、`outcome='failed'` かつ `error_code` NULL、`error_code='bad_code'` の3つが例外になる。`outcome` を書かない INSERT は `ok` になる。

## 5. 確かめ方
- ruff は変えた試験ファイル2つだけ（`uvx ruff check` と `uvx ruff format --check`）。期待する出力は `All checks passed!` と `2 files already formatted`。
- 作業場所に PostgreSQL があれば `pytest backend/tests/ops/test_ai_job_assignments_db.py backend/tests/ops/test_ai_cloud_views.py -k "ai_job"` を流してよい。無ければ流さず「SKIPPED のため CI に任せた」と書く。SKIPPED を合格と書かない。
- `python3 scripts/check-migration-value-writes.py repo` をもう一度流し、3-2 の直しの後も通ること（終了コード 0。出力は全文を報告に写す。落ちたら止まり BLOCKED: で返す）。
- `git diff origin/main...HEAD --name-only` が次の7つだけであること（ほかがあれば止まる）: `migrations/20261103_120000_create_ai_job_assignments.sql`・`scripts/run_all_migrations.sh`・`migrations/20261024_100300_create_ai_cloud_views.sql`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/tests/ops/test_ai_job_assignments_db.py`・`scripts/migration-guard/reference-allowlist.tsv`・`.github/workflows/migration-guard.yml`（このカードと同じ commit に入っている docs/ の文書は除いて数える）。
- `git diff origin/main...HEAD --numstat` の削除の数（2列目）が、`migrations/20261024_100300_create_ai_cloud_views.sql` と `backend/tests/ops/test_ai_cloud_views.py` は各1（N の行だけ）、`scripts/migration-guard/reference-allowlist.tsv` と `.github/workflows/migration-guard.yml` は各1（直した1行だけ）、ほかは0であること。違えば、そのファイルの削除行を `git diff origin/main...HEAD -- migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py scripts/migration-guard/reference-allowlist.tsv .github/workflows/migration-guard.yml | grep '^-' | head -20` で出して止まる。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 6. 想定される分岐と止まる条件
- 0 の前提が違う → 止まり、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- 1-7 を前例と同じ形にできない → 止まり、NEEDS_DECISION: で返す。
- 4-1 の順で migration が流れない（表が無い等） → 止まり、BLOCKED: で生出力を返す。表の形を試験に写して回避しない。
- 2回流しで 1-6 の列に付けた名前付きの CHECK が `already exists` で落ちた → 1-6 の outcome・error_code の CHECK も、3つ目と同じ DO の塊（`pg_constraint` に名前が無い時だけ足す）に切り替えてよい。切り替えたことは報告に書く。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>）→ git log -1 で確かめる → git push origin release/ai-roster-1a-migration → git log origin/release/ai-roster-1a-migration -1 で確かめる。PR は作らない。

## 報告の型
- 1行目: 受領確認（上の「受領確認」の内容）。2行目: 「本報告はカード 1a の実行結果である」。
- 本文: 0-1〜0-5 の生出力、「5. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
