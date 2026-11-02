# 設計審査 5回目（secretary-chatgpt design v5）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head 32e5fdcd2 の `docs/handoff/secretary-chatgpt/design.md`（v5）・`recon.md`・`kgi.md`、前回の指摘 `origin/review/secretary-chatgpt-r4` の `review4.md`
- 根拠: `git show origin/main:<path>`（origin/main c60ea6e。design の照合基準 90ee0c15f はこれの祖先で、引用したパス〔backend/app・migrations・secretary-agent・deploy.yml・compose・run_all_migrations.sh・backend/tests/ops・super-admin の画面〕には 90ee0c15f からの差分が無い）
- 製品のファイルは変えていない。この枝はこのファイルだけ

## 4回目の13件の確かめ（件ごと）

| # | 結果 | 根拠 |
|---|---|---|
| 1 SAVEPOINT | 直った（ただし新しい指摘 N3） | §4-2-3 の表の「取引」の列に `s.begin_nested()` で台帳の INSERT（今の ok の行 `tcg_extraction_record_svc.py:253-261` と新しい failed の行）だけを囲み、`:262-265` を進める形が書かれた。§7 1b の合格に「台帳の INSERT が失敗しても extraction_jobs が error になる」試験がある |
| 2 翻訳 | 直った | 使用量の読み取り（`message_translator.py:390-391`）を空の判定（`:387-388`）より前に移す・except は `_call_gemini(...)` の1行だけ（`:492`・`:513`・`:646`）・try の外（`:367-369`）の印の無い例外は書かない、の3点が §4-2-1・§4-2-3 に書かれた |
| 3 鍵切れ | 直った（ただし①の読み方は新しい指摘 N1） | §4-2-1 に `gemini_ledger_error_code` を足し、`_classify_error`（`gemini_extraction_svc.py:213-222`）より先に 401・403・API_KEY_INVALID・PERMISSION_DENIED を auth_failed にする形になった。`_classify_error` は変えない |
| 4 段1b の K5 | 直った | §4-3 最後と §7 1b に、assistant.py が担当を読み model を送る・server.mjs の `"sonnet"`（`server.mjs:70`）を消し無ければ 400・秘書の台帳の行、が入った。今の容器は `server.mjs:136` で text・now だけ読むので backend が先でも壊れない、の順番も書かれた。main で K5 の型に当たるのは `gemini_extraction_svc.py:283`・`llm_budget.py:57-89`・`message_translator.py:10-12,49-50`・`server.mjs:70` だけで、§4-3 の「消すもの」と除外の塊で全部扱われている |
| 5 build context | 直った（細部は新しい指摘 N8） | §5-1・§5-4 とも根を context に、`-f secretary-codex/Dockerfile .` に揃った |
| 6 分類表 | 書く内容は直った（合格の見方は新しい指摘 N2） | §7 1a に7列（llm_usage_events の outcome・error_code、ai_job_choices の job_key・provider・model、ai_job_assignments の job_key、ai_job_assignment_history の job_key）・`test_ai_cloud_views.py:481` の数・`run_all_migrations.sh` への追加が入った。7列の数え方は合っている |
| 7 戻すと集計がずれる | 直った | §7 に段 1a-2（集計の `outcome='ok'` だけを 1b より先の別 PR）、§10 に 1b のあと 1a-2 を戻さない、が入った |
| 8 秘書の ok の意味 | 直った | §4-2-3 に「AI の呼び出しが成功した」の意味・ログとの一致を求めない・tenant_id と source_ref=NULL が書かれた（`assistant.py:164-169,205` と合う） |
| 9 /health・回数 | 直った | §6-1 に2秒で打ち切り→ not_ready、`count_24h` は ok だけ・`failed_24h` を別の欄 |
| 10 履歴の REVOKE・SET NULL | 書く内容は直った（効くかどうかは新しい指摘 N4） | §4-1 に3表の REVOKE と changed_by・updated_by の ON DELETE SET NULL、画面の「ID 不明」が入った。`models.py:26` の CASCADE と合う |
| 11 K8 | 直った（数値の記入は §13-6 で段3の前に残る） | ①が docker stats の最大 400MB 以下に替わり、必ず通る形ではなくなった。基準値は【未確認】と明記され、段3の前の作業として §13-6 にある |
| 12 容器の細部 | 直った | §5-1 に環境変数3つ・標準入力・auth.json が無い時の 503・標準エラーは見分けにだけ、の4点（今の作り `server.mjs:74-83,117,133` と対応） |
| 13 inventory_parse_fallback | 直った | §2 に「書き手が無いので仕事に入れない」（`llm_budget.py:163`・`LlmUsageSection.tsx:154`・CHECK `20260930_150000:46-50`） |

## 指摘（v5 で新しく足した所の穴）

### N1. 重さ: 重 — §6（ログイン ○× の①）・§6-1（数え方）
- origin/main: `backend/app/services/message_translator.py:495,517,649`（`sdk="google-generativeai"`）、`backend/app/services/line_analysis_v102_svc.py:114`・`tcg_extraction_record_svc.py:219,258`（`sdk="google-genai"`）、CHECK `migrations/20260930_150000_create_llm_usage_events.sql:51-52`
- 足りない所: §6 の①と §6-1 の数え方は「sdk が今の provider のもの〔gemini→google-genai …〕」で行を引くが、翻訳3つの行は sdk=`google-generativeai` で書かれている（失敗の行も同じ書き手の層なので同じ値になる）。書いてあるとおり作ると、翻訳3行は `count_24h`・`failed_24h` が常に0、`last_ok_at`・`last_error_code` が常に null、鍵切れでも①が×にならない。K3（5行の各項目）と K6 相当の判定が5行中3行で測れない。
- 直し方: provider→sdk の対応を「gemini→{google-genai, google-generativeai}・codex→{codex-cli}・claude→{claude-code}」の集合にし、①と数え方を `sdk = ANY(:sdks)` で引く、と §6・§6-1 に書く。対応表は1か所（`llm_budget.py` の USAGE_SDKS の隣）に置き、「USAGE_SDKS のどの値もどれか1つの provider に属する」試験を段2に1本足す。

### N2. 重さ: 中 — §7 段1a（分類表の合格の見方）
- origin/main: `backend/tests/ops/test_ai_cloud_views.py:523-545`（T10 は新しい DB に `tests/rls_bootstrap.py` の表だけを作る）、`backend/tests/rls_bootstrap.py:14-34,284-289`（`_PG_BOOTSTRAP_MIGRATIONS` に llm_usage_events も ai_job_* も無い）、前例 `backend/tests/ops/test_ai_cloud_views.py:570-620`（ADR-1055 段A の専用の試験）、`migrations/20261024_100000_create_ai_cloud_meta.sql:128-129`（分類が無い列は mask に倒れる）
- 足りない所: §7 1a の合格に「CI の T10（分類漏れの見張り）が緑」とあるが、T10 の DB には llm_usage_events も新しい3表も作られないので、7列の行を足し忘れても T10 は緑のまま。合格の見方が何も測っていない（本番は分類が無い列を mask にするので漏れはしないが、allow の7行が入ったかは誰も確かめない）。
- 直し方: ADR-1055 段A の前例（`:570-620`）と同じ形の試験を 1a に1本足す: bootstrap の DB に `20260930_150000` と本便の migration を本物のまま流し、`ai_cloud_meta.column_class` に7列の行があること（名前で7件）と、新しい3表・llm_usage_events について `_classification_gaps` が0件であることを確かめる。§7 1a の合格の見方を「この試験が緑」に替える。

### N3. 重さ: 中 — §4-2-3（旧エンジンの SAVEPOINT と書く関数の「飲み込む」）
- origin/main: `backend/app/services/tcg_extraction_record_svc.py:253-270`、`backend/app/services/llm_budget.py:281-304`（`record_usage_event_sync` は例外を飲み込まない）
- 足りない所: §4-2-3 の書く関数の段は「`record_usage_failure_sync` は自分の失敗をログに出して飲み込む」「旧エンジンでは呼び手が SAVEPOINT で囲む」。飲み込みが `with s.begin_nested():` の内側で起きると、`with` は正常に抜けて RELEASE SAVEPOINT を出すが、PostgreSQL は失敗した文の後の取引を受け付けないので RELEASE が失敗し、その例外が `:268` の except に落ちて全部巻き戻る（4回目①と同じ結果に戻る）。SAVEPOINT の中では飲み込んではいけない。
- 直し方: §4-2-3 に順番を書く: `record_usage_failure_sync` は例外を上げる（飲み込まない）。旧エンジンの fail では `try: with s.begin_nested(): <ok か failed の INSERT> / except Exception: ログに種類だけ` の形で、except は SAVEPOINT の外に置く（`begin_nested` の with が例外で抜ける時に ROLLBACK TO SAVEPOINT が出る）。v102 の `_record_usage_failure` は今の `_record_usage`（`line_analysis_v102_svc.py:449-459`）と同じく関数の中で try/commit/rollback する、と分けて書く。1b の試験は「INSERT を失敗させる」を CHECK 違反などの本物の DB の失敗で起こす（Python の例外の差し替えでは取引が壊れないので、この穴を捕まえない）。

### N4. 重さ: 中 — §4-1（REVOKE が効く条件）
- origin/main: `migrations/20260605_030000_create_salesanchor_app_role.sql:16-24`、`scripts/run_all_migrations.sh:530`（毎回の実行で全ファイルを順に流す、`:110-118`）、`.github/workflows/deploy.yml:418-430`（`SA18_PHASE2_ENABLED=1` が無ければ DATABASE_URL を jarvis に戻す）
- 足りない所: ①REVOKE は salesanchor_app に対してだけ効く。本番のアプリが jarvis（表の持ち主）で繋いでいるなら、REVOKE があっても履歴の UPDATE・DELETE も選択肢の INSERT も止まらない。本番がどちらで繋いでいるかが design・recon に無い。②`20260605_030000` は毎回の実行で `GRANT ... ON ALL TABLES IN SCHEMA public` を流す（`:530`）ので、REVOKE は本便の migration の中に冪等な形で置き、毎回その後に流れることが条件になる。これも書かれていない。
- 直し方: §13 に「本番の backend と celery の接続のロールを読み取りの道で確かめる（`pg_stat_activity` の usename、application_name ごと）」を足す。jarvis なら REVOKE ではなく `BEFORE UPDATE OR DELETE` で例外を上げるトリガーを履歴の表に付ける（持ち主にも効く。ON DELETE SET NULL は users 側の削除で changed_by を書き換えるので、トリガーは「changed_by だけが NULL になる UPDATE」は通す）。salesanchor_app なら REVOKE を本便の migration に置き、`run_all_migrations.sh` で `:530` より後に流れることを §4-1 に書く。§7 1a の合格に `has_table_privilege('salesanchor_app', ..., 'UPDATE')` 等の確認を足す。

### N5. 重さ: 軽 — §7 段1b（2行出ていないかの見方）
- origin/main: `backend/app/services/tcg_extraction_record_svc.py:214-222,253-261`（旧エンジンの行は source_ref を渡さない＝NULL、extraction_attempt_id を持つ）、`backend/app/services/line_analysis_v102_svc.py:115,454,493-519`（v102 は source_ref=`extraction_job:<id>`、送り直しで同じ source_ref の failed と ok が正しく並ぶ）
- 足りない所: 合格の見方「同じ source_ref・同じ秒の ok と failed の組が0件」は、二重書きが起きうる旧エンジン（source_ref NULL）を見ておらず、v102 では送り直しの正しい組（failed の後に ok）と区別できない。
- 直し方: 旧エンジンは「同じ extraction_attempt_id に ok と failed の両方がある組が0件」、v102 は「同じ extraction_attempt_id の failed の数 ≤ その場の送り直しの上限＋1（`_IMMEDIATE_RETRY_DELAYS` の長さ＋1＝3）」に替える。

### N6. 重さ: 軽 — §4-2-1（`gemini_ledger_error_code` の置き場）
- origin/main: `backend/app/services/gemini_extraction_svc.py:26`（`from app.services import llm_budget` をモジュールの頭で読む）、`backend/app/services/llm_budget.py:35-45`（今は app の中の物を読まない）、`backend/app/services/llm_errors.py`
- 足りない所: `llm_budget.py` に置いた関数が `_classify_error` を頭で import すると、gemini_extraction_svc ↔ llm_budget の循環 import になる。「値を写す」が「呼ぶ」か「同じ規則を書き写す」かも決まっていない（書き写すと分け方が2か所になり、片方だけ直る）。
- 直し方: 関数は `llm_budget.py` に置き、`_classify_error` は関数の中で import して呼ぶ（ほかの所の前例 `line_analysis_v102_svc.py:532` の関数の中の import）、と書く。試験に「`_classify_error` の4つの値すべてが9つの error_code のどれかに写る」を1本足す。

### N7. 重さ: 軽 — §4-3・§5-3（秘書が担当を読む時と取引）
- origin/main: `backend/app/routers/assistant.py:138-144`（`:139` で取引を閉じてから AI を待つ）
- 足りない所: 「呼ぶ前に `get_ai_assignment("secretary_intent")` を読む」とあるが、`:139` の後に同じ `db` で読むと新しい取引が始まり、AI を待つ最大85秒（`:51`）の間 DB の取引を開いたままにする（`:138` の決まりに反する）。
- 直し方: 担当の読み取りを `:139` の commit より前に置く、と §5-3 に書く（または読んだ後にもう一度 commit）。

### N8. 重さ: 軽 — §5-1（Dockerfile の細部）
- origin/main: `secretary-agent/Dockerfile:6`（ファイル名は `prompt.txt`）、リポジトリの根に `.dockerignore` は無い（`git ls-tree` で `backend/.dockerignore`・`frontend/.dockerignore` だけ）
- 足りない所: ①§5-1 の COPY の例が `secretary-agent/prompt.md` で、実物は `prompt.txt`。②「根の `.dockerignore` が secretary-agent と secretary-codex を外していないかを確かめる」とあるが、根の `.dockerignore` は無い。根を context にすると VPS の `/home/ubuntu/salesanchor` の全部（`.env` を含む）が build の入力になる（BuildKit なら COPY した物しか送らないが、古い builder では全部送る）。
- 直し方: ①を `prompt.txt` に直す。②`secretary-codex/Dockerfile.dockerignore`（Dockerfile ごとの除外。BuildKit で効く）に「全部を外し、使うファイル〔`secretary-agent/prompt.txt`・`secretary-agent/schema.json`・`secretary-agent/probe.mjs` と `secretary-codex/` の中で COPY する物〕だけ戻す」許す一覧を置き、§5-4 の build を `DOCKER_BUILDKIT=1` で流す、と今決める。

### N9. 重さ: 軽 — §4-2-1・§4-2-3（翻訳の行の中身と §4-2-2 の「数字は変わらない」）
- origin/main: `backend/app/services/message_translator.py:387-388,494-497,515-519,648-652`
- 足りない所: ①翻訳の failed の行と空の応答の ok の行に入れる tenant_id・source_ref が書かれていない（成功の行は tenant_id と message_id・lead_id を入れている）。②空の応答の ok の行は今は書かれていない行なので、§4-2-2 の「今の数字は変わらない」は空の応答の分だけ成り立たない（使用量画面の回数と費用が増える。予算 `record_cost` は今どおり呼ばれないので画面と予算がずれる）。
- 直し方: ①「成功の行と同じ tenant_id・source_ref を入れる」と書く。②§4-2-2 に「空の応答の ok の行だけは新しく数に入る（費用は usage から計算、予算には足さない）」と1行書く。

### N10. 重さ: 軽 — §10（段1b の戻し方・容器が新しいまま backend だけ戻る時）
- origin/main: `.github/workflows/deploy.yml:670-699`（秘書の容器の段は `continue-on-error: true`、build 失敗は警告で exit 0）、`backend/app/routers/assistant.py:116`
- 足りない所: 1b の後に backend を前の版に戻した便で秘書の容器の段が失敗すると、新しい server.mjs（model が無いと 400）と model を送らない前の backend が並び、秘書の頼みが全部 400→unreadable になる。§10 は逆の組（容器だけ前の版）しか書いていない。
- 直し方: §10 に「backend を戻した便で秘書の容器の段が警告で終わったら、秘書の容器も前の版で作り直す（`docker build` を手で）」か、server.mjs は model が無い時に 400 ではなく今の値で動く期間を1便置く、のどちらかを書く（後者は K5 の検査と食い違うので前者を勧める）。

VERDICT: REVISE
