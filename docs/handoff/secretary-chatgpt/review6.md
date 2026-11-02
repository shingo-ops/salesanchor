# 設計審査 6回目（secretary-chatgpt design v6）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head d2495986f の `docs/handoff/secretary-chatgpt/design.md`（v6）・`recon.md`・`kgi.md`、前回の指摘 `origin/review/secretary-chatgpt-r5` の `review5.md`
- 根拠: `git show origin/main:<path>`（origin/main c60ea6eb3。design が照合に使った commit と同じ）
- 製品のファイルは変えていない。この枝で足したのはこのファイルだけ

## 5回目の10件の確かめ（1件ずつ）

| # | 結果 | 根拠（origin/main） |
|---|---|---|
| N1 sdk の集合 | 直った | 翻訳は `message_translator.py:495` で `sdk="google-generativeai"`、解析は `line_analysis_v102_svc.py:114`・`tcg_extraction_record_svc.py:219,258` で `google-genai`。design §6 の①で gemini→{google-genai, google-generativeai} の集合にし、`USAGE_SDKS`（`llm_budget.py:171`）の隣の1か所に置いて `sdk = ANY(:sdks)` で引く形になった。§6-1 の数え方も同じ対応表を使う。段2に属し先の試験が入った |
| N2 分類の試験 | 直った（ただし前提が抜けている。新しい指摘 P2） | 前例 `test_ai_cloud_views.py:570-625` と同じ形の試験が §7 1a に入った。T10（`:523-563`）は bootstrap の表しか作らないことも書かれた |
| N3 SAVEPOINT の順番 | 直った | §4-2-3 で `record_usage_failure_sync` は飲み込まない（`record_usage_event_sync`、`llm_budget.py:281-304` と同じ）・`try:`→`with s.begin_nested():`→INSERT 1つ・except は with の外、の順になった。`fail` の流れ（`tcg_extraction_record_svc.py:224-270`）と合う。試験で本物の DB の失敗を使うことも書かれた |
| N4 REVOKE が効く条件 | 直った（REVOKE をやめてトリガーにした） | §4-1 で履歴の表に `BEFORE UPDATE OR DELETE` のトリガーを置き、changed_by だけが NULL になる UPDATE は通す形になった。繋ぐ役を問わず効く。毎回流れる GRANT（`20260605_030000_create_salesanchor_app_role.sql:16-17`、`run_all_migrations.sh:530`）とぶつからない。細部は新しい指摘 P5 |
| N5 2行の見方 | 旧エンジンの見方は直った。v102 の見方は穴が残る（新しい指摘 P3） | 旧エンジンは「同じ extraction_attempt_id に ok と failed の両方がある組が0件」になった（`tcg_extraction_record_svc.py:214-222`）。v102 は extraction_attempt_id ではなく source_ref で数える形のまま |
| N6 import の置き場 | 直った | `gemini_extraction_svc.py:26` が頭で llm_budget を読むので、関数の中で import する。前例は `line_analysis_v102_svc.py:532`。`_classify_error` を呼ぶ（書き写さない）こと、4つの値の写り先の試験も書かれた |
| N7 担当を読む時と取引 | 直った（ただし読めない時の扱いが無い。新しい指摘 P4） | §5-3 で `assistant.py:139` の commit より前に読む形になった |
| N8 Dockerfile の細部 | 直った | §5-1 は `prompt.txt` に直った（`secretary-agent/Dockerfile:6`）。根に `.dockerignore` は無いので、`secretary-codex/Dockerfile.dockerignore` に許す一覧を置き、§5-4 の build を `DOCKER_BUILDKIT=1` で流す形になった。VPS の Docker の版が Dockerfile ごとの除外に対応しているかは【未確認】（§5-2 で記録する Docker の版に含めれば足りる） |
| N9 翻訳の行の中身 | 直った | §4-2-3 で tenant_id・source_ref・sdk は同じ場所の成功の行と同じ値（`message_translator.py:495-496` 等）にし、§4-2-2 に空の応答の ok の行だけ新しく数に入ることが書かれた |
| N10 backend だけ戻した時 | 直った | §10 で、容器の段が警告で終わったら秘書の容器も前の版で作り直す（PO に `!` で頼む）、と書かれた（`deploy.yml:670-699` は `continue-on-error: true`） |

## 新しい指摘

### P1. 重さ: 中 — §4-1・§7 1a（migration は毎回の deploy で流れ直す。初めの行の入れ方が決まっていない）
- 根拠（origin/main）: `scripts/run_all_migrations.sh:110-118`（`run_sql` は済んだかどうかを記録せず、毎回 psql に流す）。一覧は毎回の実行で頭から終わりまで流れる（`:527-533`・`:1059`・`:1209-1211`。適用済みを記録する表を探したが見当たらない）。前例の新しい表 `migrations/20261101_130000_add_new_device_approval.sql:6,25,41` は `IF NOT EXISTS` で書かれ、流れ直しても大丈夫な形になっている。
- 足りない所: 本便の migration も毎回の deploy で流れ直すが、design に「冪等に書く」と、初めの行の入れ方が書かれていない。
  - `ai_job_assignments` の初めの5行を `ON CONFLICT DO UPDATE`（または DELETE して入れ直す形）で書くと、毎回の deploy で画面から変えた担当が初めの値に戻る。K9（切り替えが効き続ける）が deploy のたびに壊れ、しかも履歴の表には戻した記録が残らない。
  - 何も付けない INSERT と `CREATE TRIGGER` にすると、2回目の deploy で migration が失敗する。
  - 段3の codex の選択肢3行の migration も同じ。
  - CHECK の作り直し（purpose・sdk・outcome/error_code）も、2回目に流れて失敗しない形にする必要がある。
- 直し方: §4-1 に1行足す。「本便の migration はすべて毎回流れ直す前提で書く。表・列・索引は `IF NOT EXISTS`。初めの行（ai_job_choices・ai_job_assignments）は `ON CONFLICT DO NOTHING` にし、担当の行は流れ直しで上書きしない。トリガーは `CREATE OR REPLACE FUNCTION` と `CREATE OR REPLACE TRIGGER`（PostgreSQL 14 以上。本番は 16）。CHECK は名前を付け、`DROP CONSTRAINT IF EXISTS`→`ADD` の順にする」。§7 1a の試験には「migration を2回流しても通る。2回目の後も、画面で変えたのと同じ形で UPDATE した担当の行がそのまま残る」の1本を足す（前例 `test_ai_cloud_views.py:618` の「冪等」の2回流し）。

### P2. 重さ: 中 — §7 1a（分類の試験の DB で `20260930_150000` がそのままでは流れない）
- 根拠（origin/main）: `migrations/20260930_150000_create_llm_usage_events.sql:40`（`extraction_attempt_id UUID REFERENCES public.extraction_attempts(id)`）。`backend/tests/rls_bootstrap.py:14-34` の `_PG_BOOTSTRAP_MIGRATIONS` には extraction_attempts を作るファイル（`20260921_110000_pipeline_tables_public.sql:112`）が入っていない。前例の試験 `test_ai_cloud_views.py:609-610` は、先に要る物（`001_create_auth_events.sql`・`20261013_160000_...`）も本物の migration で流している。
- 足りない所: §7 1a の試験は「bootstrap の DB に `20260930_150000` と本便の migration を本物のまま流す」としているが、bootstrap の DB には `public.extraction_attempts` が無い。そのため `20260930_150000` は外部キーの所で失敗し、試験が書けない。実装の人が試験だけのために表の形を写すと、design の「表の形をテストに写さない」という前例の方針（`test_ai_cloud_views.py:587-588`）とずれる。
- 直し方: §7 1a の試験に、流す順番を書く。`20260921_110000_pipeline_tables_public.sql` →`20260930_150000` →本便の migration →`_CREATE_SQL`。bootstrap の DB で `20260921_110000` が通るか（中で public.suppliers〔`056_...` が作る〕などを参照する）は【未確認】。通らない場合は、どの表を最小の定義で足すかを design に書く。CI の `migration-test.yml` の基準の表には extraction_attempts と llm_usage_events がもう入っている（`.github/workflows/migration-test.yml:828,879-905`）ので、そちらの心配は無い。

### P3. 重さ: 軽 — §7 1b（v102 の「2行出ていない」の見方が、正しい送り直しでも×になりうる）
- 根拠（origin/main）: v102 の台帳の行は `source_ref=extraction_job:<id>` と、`extraction_attempt_id=recorder.id` を持つ（`line_analysis_v102_svc.py:454,551`）。celery のタスクは失敗すると最大2回まで送り直す（`backend/app/tasks/tcg_extraction.py:819,838`・`:843,856`）。
- 足りない所: 合格の見方は「同じ source_ref の failed の数が3以下」。しかし同じ extraction_job が celery の送り直し・人が直した後の解析し直し（`:843` の v102_reanalyze）で何度も呼ばれると、正しい動きでも1つの source_ref に failed が4行以上たまる。送り直しで同じ extraction_job_id を使い回すかは【未確認】。
- 直し方: v102 も「同じ extraction_attempt_id（recorder がある時。`:551`）の failed の数が3以下」で数える。recorder が無い道（再抽出の道具。extraction_attempt_id が NULL）は数えない、と書く。

### P4. 重さ: 軽 — §5-3・§4-2-3（秘書で担当を読めない時の返事と記録が決まっていない）
- 根拠（origin/main）: `backend/app/routers/assistant.py:139`（commit）・`:143-166`（try。except は `HTTPException` だけ）。design §4-3 は「行が無ければ例外で止める」、§5-3 は「`:139` の commit より前に読む」。
- 足りない所: 担当を読む所は `:143` の try の外にある。読めない時（行が無い・DB の失敗）は、`_log` も台帳の行も無いまま 500 になる。§4-2-3 の秘書の行の決まり（「それ以外すべて failed」）とも、ログの code の一覧とも合わない。読めないと provider と model も分からないので、台帳の行の sdk・model も埋められない。
- 直し方: §5-3 に書く。「担当の読み取りが例外になったら `_fail(503, "not_ready")` を返し、`_log(..., "not_ready")` を出す。台帳の行は書かない（provider が分からないため。理由も書く）」。または「try の中に入れる」でもよいが、その時は commit より前に置く条件（N7）と両立する形を書く。

### P5. 重さ: 軽 — §4-1（履歴の表のトリガーの抜け・新しい表の権限）
- 根拠（origin/main）: `BEFORE UPDATE OR DELETE` の行のトリガーは TRUNCATE では動かない（PostgreSQL の決まり。TRUNCATE には文ごとのトリガーが別に要る）。新しい表の権限の前例は、`migrations/20261101_130000_add_new_device_approval.sql:128-130`・`20261102_090000_add_user_push_subscriptions.sql:35-37` で、salesanchor_app に表と順番の数（sequence）を、明示して GRANT している。`20260605_030000_create_salesanchor_app_role.sql:21-24` の ALTER DEFAULT PRIVILEGES は、jarvis が作る表にだけ効く（migration は `psql -U jarvis` で流れる、`run_all_migrations.sh:25`）。
- 足りない所: ①履歴の表は TRUNCATE で丸ごと消せる。②3表と SERIAL の順番の数（ai_job_choices・ai_job_assignment_history）を salesanchor_app に GRANT するかが書かれていない。今は既定の権限で付くが、前例とずれる。
- 直し方: ①`BEFORE TRUNCATE ... FOR EACH STATEMENT` のトリガーも同じ関数で付け、§7 1a のトリガーの試験に TRUNCATE が例外になることを足す。②前例どおり、`IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app')` の中で3表と順番の数に GRANT する、と §4-1 に書く。

## そのほかに確かめたこと（指摘なし）
- K5 の検査の型で今当たる所（`git grep` を origin/main の `backend/app`・`secretary-agent` で実行）は、`gemini_extraction_svc.py:283`・`llm_budget.py:57-89`・`message_translator.py:10-12,49-50`・`server.mjs:70` の4か所だけ。§4-3 の「消すもの」と除外の塊で全部扱われている。
- 分類の7列は、名前の見張り（`test_ai_cloud_views.py:41-44` の `_NAME_RE`）に当たらない。changed_by・updated_by は整数の型で、型だけで通る。
- `assistant.py:77-116` の `_call_agent` は、httpx の失敗をすべて HTTPException に直している。そのため try（`:143-166`）の中で HTTPException 以外の例外が出る道は、P4 の読み取りのほかには見当たらない。

VERDICT: REVISE
