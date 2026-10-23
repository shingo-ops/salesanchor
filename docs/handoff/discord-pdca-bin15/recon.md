<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — discord-pdca-bin15（保守 API に Discord 発の件の入口を足す）

**仕事名**: discord-pdca-bin15  
**日付**: 2026-10-23  
**対象ADR**: ADR-1039（Discord の不具合報告を agent-console で受ける。Proposed）、ADR-1012（24時間保守・障害記録の表）  
**担当**: 調べ Sonnet・照合 Opus（設計パートナー）  
**基準**: origin/main cc000952f6d16a90f888ed8e3a0a460706bdf717（worktree で行番号を読み直した）  
**設計**: agent-console リポジトリ docs/handoff/discord-pdca/design.md 第13版 §4-9・§8 便1.5・§11（別リポジトリのためバッククォートなし）

---

## 1. 既存 ADR の検索

- `docs/adr/ADR-1039-discord-pdca-agent-console.md`:33 … Decision 10「Discord 発の不具合の行は、段階6 より前から ADR-1012 の障害記録の表に入れ、`labels.source='discord'` で分ける」。
- `docs/adr/ADR-1012-ai-ops-247.md` … 障害記録の表と保守 API の親 ADR。
- `docs/adr/FEATURE-INDEX.md`:48 … 保守運用の索引。
- 表の形（列・制約）を変える ADR は無い。本便も migration を作らない。

## 2. file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/ops.py:43` | `_ANNOTATABLE_COLUMNS`（:43-54）。注記で書ける10列。`ai_started_at`・`detection_path`・`first_aid_*`・`review_note`・`human_noticed_at` を含む |
| `backend/app/routers/ops.py:57` | `_clear_operator`（:57-61）。読み書きは `set_operator_context` → 処理 → `finally: _clear_operator` の形。テナント文脈は使わない |
| `backend/app/routers/ops.py:102` | `require_ops_reader`（:102-117）。`OPS_API_TOKEN` なら `{"actor": "ops_token", "user_id": None}`、取り込み用の鍵は 401、super admin のログインなら `{"actor": "super_admin", ...}` |
| `backend/app/routers/ops.py:161` | `_UPSERT_INCIDENT_SQL`（:161-180）。`first_notified_at`・`last_notified_at` は `now()`、衝突時は `DO UPDATE` で `notify_count + 1`・`status` 上書き。`RETURNING id, (xmax = 0) AS inserted` |
| `backend/app/routers/ops.py:182` | `_INSERT_EVENT_SQL`（:182-185）。出来事は `incident_id, kind, actor, detail` の4つ |
| `backend/app/routers/ops.py:188` | `_dumps` は `json.dumps(value, ensure_ascii=False)` |
| `backend/app/routers/ops.py:213` | `ingest_alertmanager`（:213-267）。行を作る口は今これだけ |
| `backend/app/routers/ops.py:334` | `OpsIncidentFields`（:334-346）。`extra="forbid"`。`detection_path` は Literal alert/human/ai |
| `backend/app/routers/ops.py:349` | `OpsIncidentAnnotation`（:349-354）。`kind` は Literal annotated/first_aid/ai、`note` は 2000字まで |
| `backend/app/routers/ops.py:357` | `annotate_incident`（:357-403）。:361 `require_ops_reader`。:364-365 で `exclude_unset` の値から列を選ぶ。:368-385 で UPDATE か SELECT。:386-388 で無ければ 404。:395-397 で `detail = {"fields", "note", "user_id"}` |
| `backend/app/routers/ops.py:396` | `detail` の形はここ1か所で決まる |
| `backend/app/routers/ops.py:474` | `halt_all` の口。保守 API のどの書く口も `halt_all` を見ていない（:213-267・:357-403 に参照なし） |
| `backend/app/main.py:777` | `app.include_router(ops.router, prefix="/api/v1")`。口の前置きは `/api/v1` |
| `backend/app/realtime/topics.py:86` | `NO_SIGNAL_ROUTES` の始まり |
| `backend/app/realtime/topics.py:116` | 保守 API の4つの登録（:116-119）。理由の文は「保守 API ADR-1012: 運用者向けで画面更新の通知対象外」 |
| `backend/tests/test_realtime_topics.py:34` | 書く口はすべて表のどちらか1つに載る（:34-39）。足し忘れはここで落ちる |
| `backend/tests/test_realtime_topics.py:108` | 表に実在しない口があると落ちる（:108-111） |
| `backend/tests/test_ops_router.py:22` | 実 PostgreSQL が無いと全体が skip（:22-31） |
| `backend/tests/test_ops_router.py:84` | `env` の fixture（:84-141）。後片付けは `holder.fingerprints` に入れた指紋の行だけ消す（:121-139） |
| `backend/tests/test_ops_router.py:151` | `_incidents`・`_events` の助け（:151-162） |
| `backend/tests/test_ops_router.py:319` | `test_annotate_updates_allowed_fields_only`（:319-350）。注記の既存の試験 |
| `backend/tests/test_ops_router.py:396` | `test_ingest_continues_while_halted`（:396-412）。`ops_control_lock` と `_clear_control` の使い方 |
| `migrations/20261016_100000_create_ops_incident_tables.sql:14` | `first_notified_at`・`last_notified_at` は NOT NULL で既定値なし（:14-15） |
| `migrations/20261016_100000_create_ops_incident_tables.sql:19` | `detection_path` の既定値は 'alert' |
| `migrations/20261016_100000_create_ops_incident_tables.sql:31` | 一意の制約 `(fingerprint, starts_at)` |
| `migrations/20261016_100000_create_ops_incident_tables.sql:37` | `labels`・`annotations` は 4096 バイトまで（:37-38） |
| `migrations/20261016_100000_create_ops_incident_tables.sql:55` | 出来事の `kind` は notified/resolved/annotated/first_aid/ai/halt |
| `migrations/20261016_100000_create_ops_incident_tables.sql:57` | 出来事の `actor` は alertmanager/ops_token/super_admin だけ |
| `migrations/20261016_100000_create_ops_incident_tables.sql:58` | `octet_length(detail::text) <= 8192` |
| `.github/workflows/test.yml:207` | 「Run pytest (full suite + PostgreSQL RLS)」。:223・:225 で `RLS_TEST_DATABASE_URL`・`RLS_ADMIN_DATABASE_URL` を渡すので、CI では `backend/tests/test_ops_router.py` が skip されずに走る |
| `.github/workflows/test.yml:252` | 必須 Check 名「pytest (SQLite + PostgreSQL RLS)」 |
| `.github/workflows/api-contract-check.yml:31` | openapi の書き出し（:31-35、`ENVIRONMENT=test`）と :50-55 の `git diff --exit-code -- frontend/api-contract/` |
| `frontend/package.json:10` | `generate:api-types`。出力の `frontend/src/api/generated/` は `.gitignore`:128 で追跡外 |
| `nginx/nginx.conf:480` | 送り元を絞る location は `/api/v1/ops/alertmanager` だけ。ほかの `/api/v1/ops/...` は通常の API と同じ道 |

## 3. 観測事実（引用表の補足）

- 出来事の入口を呼ぶコードは、両リポジトリに無い（文書だけ。生出力 /tmp/CC報告ファイル/discord-pdca-bin15/80-ops-callers.txt）。`round` を足しても壊れる呼び出し元は無い。
- 表を変える後の migration は無い（同 21-grep-mig.txt）。
- `.github/workflows/deploy.yml` は main への push で動く（paths の絞りなし）。本便を main に入れると backend が本番に入る。

## 4. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 新しい口が書く出来事の `actor` に許される値か | `require_ops_reader` の戻り（`backend/app/routers/ops.py:111`・:117）と表の制約（mig :57）を照合。`ops_token`・`super_admin` はどちらも許される | ✅ 解消済み（migration 不要） |
| 2 | `round` を書く出来事の `kind` | 設計 §4-9「この入口では `kind='ai'`」。`ai` は既存の Literal（ops.py:352）と制約（mig :55）の両方にある | ✅ 解消済み |
| 3 | 人の報告の行を作るのに `_UPSERT_INCIDENT_SQL` を使えるか | 衝突時に `notify_count` を増やし `status` を上書きし（ops.py:172-177）、時刻は `now()` で `human_noticed_at` を入れない。設計の「既存の行を返す」と合わない | ✅ 解消済み（新しい SQL を足す。design.md §4-3） |
| 4 | Discord 発の行の見分け方 | ADR-1039 Decision 10 の `labels.source='discord'`。`labels` を書き換える口は無い（ops.py 全体） | ✅ 解消済み |
| 5 | 試験を走らせる CI の名前（設計 §15 の【未確認】） | `.github/workflows/test.yml`:207・:252 | ✅ 解消済み |
| 6 | 8000 バイトの測り方が DB の測り方と合うか | DB は `octet_length(detail::text)`（jsonb の文字表現）。Python の `_dumps` も区切りに空白を入れ非 ASCII を生で出すので近い値になる。差は 192 バイトの余白で吸う。境の試験で確かめる（design.md §4-6 T12） | ✅ 解消済み（試験で確かめる） |

**未解決ゼロ確認**: 全て解消済み
