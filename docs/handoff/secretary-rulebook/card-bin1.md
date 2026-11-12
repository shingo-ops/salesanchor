# 実装カード 便1: 決まり帳の表 2 つ・会社ごとの鍵（RLS）・使いみち 1 つを足す migration

- 設計: [design.md](design.md) §4・§6 の①・§12 便1（審査 9 回目 APPROVE）。目標: [kgi.md](kgi.md) R5・R7・R9。調査: [recon.md](recon.md)。ADR: `docs/adr/ADR-1077-secretary-rulebook.md`（Proposed のまま）。
- 状態: 手順書の案（Opus 作成・2026-11-12）。**PO の実装承認あり（2026-11-12「1」）。** 2026-11-12 に今の本体（origin/main b6b444eff）と照らし、古くなった数字（分類の列数・登録の最後の行・最後の T10 の試験）を直した。同じ日に、提出前の確認で落ちた点（分類のファイルの照合の印＝sha256 を例外の一覧で直す手順が無かった）を受けて、やること 5b・5c を足した（origin/main e2addb796 で照合）。
- ブランチ: `release/secretary-rulebook-bin1`（実装役が origin/main から作る）。PR は作らない（Opus が作る・危険 PR＝`migrations/` を含む）。
- 行番号は origin/main b55dcc0af（2026-11-12）で読んだもの。
- 試験は Mac で流さない（PG の試験は CI の使い捨ての DB だけで動く）。

## 読んだ節（設計パートナーの照合）

- docs/handoff/design-partner-card-ops/guards/00-common.md: 置き換えの印を残さない（ファイル名・表名・値をすべて実名で書いた）・報告に無い出力を成功と扱わない。○
- docs/handoff/design-partner-card-ops/guards/07-migration.md: 置くだけでは MIGRATION GUARD が落ちる → `scripts/run_all_migrations.sh` に登録（やること 4）・採番は直近を実測（直近は `20261112_170000`）・migrations は CODEOWNERS で shingo-ops の承認が要る（Opus が PR で扱う）。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 迷ったら補わずに停止して報告する（分かれ道に書いた）。○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-bin1 を読んだ」と書く。

## この便で決めたこと（Opus・設計からの細部）

| 決めたこと | 理由・出典 |
|---|---|
| 便1 で直す使いみちの場所は、設計 §6 の①（DB の CHECK）だけ。②〜⑥（`backend/app/services/llm_budget.py:159-169` の一覧・照合試験・`backend/app/routers/assistant.py:135`・画面の一覧と翻訳キー）は便2 で、`secretary_regression` を書くコードと同じ PR に入れる | 便1 は migration だけの危険 PR にする（設計 §12）。DB が先に値を 1 つ多く許しても、書くコードがまだ無いので行は増えない。逆（コードが先）だと書き込みが CHECK で落ちる。DB の集合とコードの集合を突き合わせる試験は無い（`grep -rn "purpose_check" backend/tests` は `backend/tests/test_llm_usage_events_migration_pg.py:57` の名前の有無だけ） |
| 2 表の鍵（RLS）は、読む・書く・直す・消すの全部に 1 つの方針（FOR ALL）で「自社の会社文脈 OR 運営文脈」 | 設計 §4。型 C（`migrations/20261107_140000_add_discord_config_rls.sql:10-22`）の書く側の式を使い、読む側の `USING (true)`（同 :8）は使わない。1 方針にまとめる形は `migrations/20261112_150000_create_viewer_contract_public_tables.sql:183-185` と同じ |
| アプリの役割に付けるのは SELECT・INSERT・UPDATE だけ（DELETE は付けない） | 決まりは消さず status を変える（設計 §4 の status）。試しの行も消さない（「やり直しても前の数が消えない」設計 §4）。付け方の形は `migrations/20261112_150000_create_viewer_contract_public_tables.sql:259-269` |
| 会社の行は `public.tenants(id) ON DELETE RESTRICT`、人は `public.users(id)`（作った人は NOT NULL・決めた人は NULL 可）。作った人は RESTRICT（人を消すと止まる）、決めた人と測り始めた人は `ON DELETE SET NULL`（人を消すと空になる） | 会社を消すと決まりが黙って消える形を避ける（先例 `migrations/20261112_150000_create_viewer_contract_public_tables.sql:25`）。人の列の先例は `migrations/20261107_120000_create_staff_join_invites.sql:17`（NOT NULL・指定なし＝RESTRICT 相当）と `migrations/20261103_120000_create_ai_job_assignments.sql:54`（NULL 可・SET NULL） |
| 試しの表の sdk・model は値の一覧の CHECK を付けず、長さだけ決める | 一覧は `backend/app/services/llm_budget.py:173`（USAGE_SDKS）と `llm_usage_events_sdk_check` にある。3 か所目の写しを作らない（設計の「データを 1 か所」）。model の先例: `public.ai_job_choices.model` も一覧の決まりが無い（`migrations/20261024_100300_create_ai_cloud_views.sql` の分類行「値の決まりが無く自由に入る列」） |
| 2 表の全部の列（25 列）と表に日本語の説明（COMMENT）を付ける | `backend/AGENTS.md:66`「新テーブル作成時は全カラムに `COMMENT ON COLUMN`」。先例 `migrations/20261107_120000_create_staff_join_invites.sql`（16 個） |
| 決まりの文の制御文字は DB で断らない | 設計 §3「大きさ」で backend が断る（便2）。決まりを 2 か所に書かない |
| 相談係の読み取り用の分類（`migrations/20261024_100300_create_ai_cloud_views.sql`）に 2 表の 8 列を足す | 足さないと分類の漏れになる（`backend/tests/ops/test_ai_cloud_views.py:492-498` の判定）。先例: 契約の表は分類を別便（ADR-1061 便2-2b・commit 108da716a）にしたが、本件は 8 列なので同じ便に入れる |
| 分類のファイルを直したら、確認 8 の例外の一覧 `scripts/migration-guard/reference-allowlist.tsv` の同じファイルの行の sha256 を直した後の中身の値に直し、決めた根拠の欄の末尾に ` / secretary-rulebook card-bin1（分類5行追加）` を足す | 一覧の sha256 が中身と違うと、例外が効かず確認 8・repo モード・`scripts/tests/test_migration_value_writes.py` が落ちる（`scripts/check-migration-value-writes.py:166-173`・`:243-254`）。2026-11-12 の実装の 1 回目はこれで止まった。先例: 同じファイルを直した commit 788d535ef・c7ecbcf2d も一覧の 1 行を同じ形で直した |
| 新しい 2 表の名前を `.github/workflows/migration-guard.yml` の `PUBLIC_TABLES` の末尾に足す | 同ファイル 226-227 行目「新しいテーブルを public に追加した場合はここを更新すること（SSoT）」。今の 2 表を指す外部キーは無いので足さなくても落ちないが、正本の一覧を最新に保つ。先例: commit 788d535ef（customer_statuses）・c7ecbcf2d（countries） |
| 戻しの SQL は別ファイル `_down.sql` にし、`scripts/run_all_migrations.sh` には「手動実行のみ」の注記の行で載せる（run_sql にしない） | 先例 `scripts/run_all_migrations.sh:555`。MIGRATION GUARD は「ファイル名が run_all_migrations.sh に書かれているか」だけを見る（`.github/workflows/migration-guard.yml:133-136`） |

## やること（この順）

1. 作業場所を公式の台本で作る（クラウドでも同じ。card-bin0.md のやること 1 と同じ形）。`<main>` はクラウドが最初に置いた場所。1 つずつ流し、出力を報告に書く。
   - (1a) `cd <main> && git fetch origin main`
   - (1b) `cd <main> && git branch --list release/secretary-rulebook-bin1`。空であること。空でなければ消さずに BLOCKED:。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/secretary-rulebook-bin1`（`--claude` は付けない）。
   - (1d) `cd <main> && git worktree list`。`$HOME/worktrees/salesanchor/release-secretary-rulebook-bin1` が出ること。以後の `<repo>` はこの絶対パス。
   - (1e) `cd <repo> && ./scripts/dev/executor-preflight.sh`。生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ BLOCKED:。
   - (1f) `cd <repo> && ls migrations | tail -3`。いちばん新しいファイルの名前が `20261113_100000` より前であること。同じか後のものがあれば BLOCKED:（採番を Opus が決め直す）。
2. `migrations/20261113_100000_create_secretary_rules.sql` を作る。中身は下の「migration の中身」を 1 文字も変えずに使う。
3. `migrations/20261113_100000_create_secretary_rules_down.sql` を作る。中身は下の「戻しの中身」を 1 文字も変えずに使う。
4. `scripts/run_all_migrations.sh` の最後の行（今は 1269 行目 `run_sql migrations/20261112_170000_add_calendar_events_recurrence.sql`）の後ろに、次の 3 行を足す。ほかの行は変えない。
   ```
   # ADR-1077 便1: 秘書の決まり帳の表 2 つ（public.secretary_rules・public.secretary_rule_checks・FORCE RLS）と使いみち secretary_regression を足す（作るだけ・行なし・冪等）
   run_sql migrations/20261113_100000_create_secretary_rules.sql
   # ADR-1077 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_100000_create_secretary_rules_down.sql
   ```
   （空行は足さない。足した後に `tail -4 scripts/run_all_migrations.sh` の生出力を報告に貼る。）
5. `migrations/20261024_100300_create_ai_cloud_views.sql` の分類の行に、下の「分類に足す行」の 5 行（8 列）を、表の名前の ABC 順に合う位置へ足す（`secretary_` で始まる表の位置。今は `('public','sa_products',…)` の行（230 行目）と `('public','source_messages',…)` の行（231 行目）の間。前後の行の表名を報告に書く）。同じファイルの 3 行目の「下の 1143 行」を、足した後の列の数に直す（今 1143 に 8 を足して 1151 になるはず）。`backend/tests/ops/test_ai_cloud_views.py:486` の `1143` も同じ数に直す。足す前に `grep -n "1143" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py` を流し、1143 がこの 2 か所だけであることを報告に貼る。違えば BLOCKED:。
   - 5b. 5 を終えた後（分類のファイルをもう直さない状態で）、`sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` を流し、生出力を報告に貼る。`scripts/migration-guard/reference-allowlist.tsv` の `migrations/20261024_100300_create_ai_cloud_views.sql` で始まる行（今は 7 行目・1 行だけ）を Edit で直す。直すのは 2 か所だけ: 2 列目（タブ区切り）の sha256 を今流した値に置き換える／4 列目の末尾（行末）に ` / secretary-rulebook card-bin1（分類5行追加）` を足す。1 列目と 3 列目・タブ・ほかの行は変えない。直した後に `git diff scripts/migration-guard/reference-allowlist.tsv` を報告に貼る（- 1 行・+ 1 行であること）。この後で分類のファイルを直したら、5b をやり直す。
   - 5c. `.github/workflows/migration-guard.yml` の `PUBLIC_TABLES="` で始まる行（今は 228 行目・1 行だけ）の末尾の `countries"` を `countries secretary_rules secretary_rule_checks"` に Edit で直す。ほかの行は変えない。直した後に `git diff --stat .github/workflows/migration-guard.yml` を報告に貼る（1 行の追加と 1 行の削除であること）。`countries"` が行末に無ければ（だれかが先に足した）、行末の `"` の手前に ` secretary_rules secretary_rule_checks` を足し、その行の最後の 3 語を報告に書く。
6. `backend/tests/ops/test_ai_cloud_views.py` の最後の T10 の試験（`test_t10_issuer_columns_are_classified_on_bootstrapped_db`・今 836 行目から、`test_t10_detects_added_columns`（886 行目）の手前まで）の後ろに、同じ形の試験を 1 つ足す。題は `test_t10_secretary_rules_columns_are_classified_on_bootstrapped_db`。違いは: 流す migration は `_read(_SECRETARY_RULES_SQL)` を 2 回（冪等）、表の集合は `{"secretary_rules", "secretary_rule_checks"}`、行があるべき列は下の「分類に足す行」の 8 列。`_VIEWER_ACCOUNTS_SQL` は流さない。新しい migration は `public.llm_usage_events` を直すので、流す順は AI 担当の T10（`backend/tests/ops/test_ai_cloud_views.py:705-724`）と同じにする: bootstrap → `_read(_PIPELINE_PUBLIC_SQL)` → `_read(_LLM_USAGE_SQL)` → 新しい migration 2 回 → `_read(_CREATE_SQL)`。`_PIPELINE_PUBLIC_SQL` を抜くと、使用の記録の表が参照する `public.extraction_attempts` が無くて落ちる（`migrations/20260930_150000_create_llm_usage_events.sql:40`）。どちらの定数もファイルに既にあるので足さない。ファイル上の定数は `_SECRETARY_RULES_SQL = "20261113_100000_create_secretary_rules.sql"` を 1 行足す。
7. 試験ファイル `backend/tests/test_secretary_rules_tables_pg.py` を新しく作る。決まりは下の「試験の決まり」。
8. commit（1 つ。`git add` は 8 ファイルを名前で指定する: 2・3 の 2 つ・`scripts/run_all_migrations.sh`・`migrations/20261024_100300_create_ai_cloud_views.sql`・`scripts/migration-guard/reference-allowlist.tsv`・`.github/workflows/migration-guard.yml`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/tests/test_secretary_rules_tables_pg.py`。題は `feat(db): 秘書の決まり帳の表2つと使いみちsecretary_regressionを足す（ADR-1077 便1・作るだけ）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`git log --oneline -1` を報告に貼る。
9. 提出前: `cd <repo> && bash scripts/dev/check-before-submit.sh`。生の結果をファイルに残し、パスと最後の 5 行を報告する。通ったら `cd <repo> && git push origin release/secretary-rulebook-bin1`。

## migration の中身

```sql
-- ADR-1077 便1: 秘書の決まり帳の表 2 つと、使用の記録の使いみち secretary_regression を足す（作るだけ。行は入れない）
-- 設計: docs/handoff/secretary-rulebook/design.md §4・§6 の①・§12 便1。手順書: docs/handoff/secretary-rulebook/card-bin1.md
-- RLS: 2 表とも ENABLE と FORCE。読む・書くとも「自社の会社文脈 OR 運営文脈」（型 C の書く側の式。読む側の USING (true) は使わない）
-- 冪等: 表と索引は IF NOT EXISTS。CHECK は表を作る文の中に書く。方針は DROP POLICY IF EXISTS の後に作る。使いみちの CHECK は定義に値が無いときだけ付け替える
-- ロールバック: migrations/20261113_100000_create_secretary_rules_down.sql（手動実行のみ）

BEGIN;

-- 会社の決まりと候補（この 1 表だけに持つ）
CREATE TABLE IF NOT EXISTS public.secretary_rules (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    rule_text TEXT NOT NULL DEFAULT '',
    source_text TEXT NULL,
    source_kind TEXT NULL,
    source_reply TEXT NULL,
    created_by INTEGER NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    decided_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_secretary_rules_status CHECK (status IN ('candidate', 'approved', 'rejected', 'removed')),
    CONSTRAINT ck_secretary_rules_rule_text_len CHECK (char_length(rule_text) <= 150),
    CONSTRAINT ck_secretary_rules_approved_text CHECK (status <> 'approved' OR char_length(btrim(rule_text)) >= 1),
    CONSTRAINT ck_secretary_rules_source_text_len CHECK (source_text IS NULL OR char_length(source_text) <= 1000),
    CONSTRAINT ck_secretary_rules_source_kind CHECK (source_kind IS NULL OR source_kind IN ('invoice', 'event', 'unknown', 'rule_proposal', 'rule_list')),
    CONSTRAINT ck_secretary_rules_source_reply_len CHECK (source_reply IS NULL OR char_length(source_reply) <= 200),
    CONSTRAINT ck_secretary_rules_decided CHECK ((status = 'candidate') = (decided_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_secretary_rules_tenant_status
    ON public.secretary_rules (tenant_id, status, id);

-- 前と同じか確かめる試しの結果（1 回の試しごとに 1 行）
CREATE TABLE IF NOT EXISTS public.secretary_rule_checks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    started_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    sdk TEXT NOT NULL,
    model TEXT NOT NULL,
    rules_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    ok INTEGER NOT NULL DEFAULT 0,
    ng INTEGER NOT NULL DEFAULT 0,
    unmeasured INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    progress_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_secretary_rule_checks_sdk_len CHECK (char_length(sdk) BETWEEN 1 AND 50),
    CONSTRAINT ck_secretary_rule_checks_model_len CHECK (char_length(model) BETWEEN 1 AND 100),
    CONSTRAINT ck_secretary_rule_checks_rules_count CHECK (rules_count >= 0),
    CONSTRAINT ck_secretary_rule_checks_status CHECK (status IN ('running', 'done', 'failed')),
    CONSTRAINT ck_secretary_rule_checks_counts CHECK (ok >= 0 AND ng >= 0 AND unmeasured >= 0 AND total >= 0 AND ok + ng + unmeasured <= total),
    CONSTRAINT ck_secretary_rule_checks_finished CHECK ((status = 'running') = (finished_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_secretary_rule_checks_tenant_started
    ON public.secretary_rule_checks (tenant_id, started_at DESC);

-- 列の説明（backend/AGENTS.md「書き方の決まり」: 新しい表は全部の列に COMMENT ON COLUMN）
COMMENT ON TABLE public.secretary_rules IS '秘書の決まり帳。会社ごとの決まりと候補をこの 1 表だけに持つ（ADR-1077）';
COMMENT ON COLUMN public.secretary_rules.id IS '番号';
COMMENT ON COLUMN public.secretary_rules.tenant_id IS '会社の番号（public.tenants.id）';
COMMENT ON COLUMN public.secretary_rules.status IS '状態: candidate=候補・approved=使う・rejected=捨てた・removed=外した';
COMMENT ON COLUMN public.secretary_rules.rule_text IS '決まりの文（150 字まで。approved のときは空白以外が 1 字以上）';
COMMENT ON COLUMN public.secretary_rules.source_text IS '元になった利用者の文 1 つ（1000 字まで）';
COMMENT ON COLUMN public.secretary_rules.source_kind IS '元になった秘書の答えの種類（invoice・event・unknown・rule_proposal・rule_list）';
COMMENT ON COLUMN public.secretary_rules.source_reply IS '元になった秘書の答えの文（200 字まで）';
COMMENT ON COLUMN public.secretary_rules.created_by IS '作った人（public.users.id）';
COMMENT ON COLUMN public.secretary_rules.decided_by IS '使う・捨てる・外すを決めた人（public.users.id）。人が消えたら空になる';
COMMENT ON COLUMN public.secretary_rules.created_at IS '作った時刻';
COMMENT ON COLUMN public.secretary_rules.decided_at IS '決めた時刻。候補のあいだは空';
COMMENT ON TABLE public.secretary_rule_checks IS '前と同じに読めるか確かめる試しの結果。1 回の試しごとに 1 行（ADR-1077）';
COMMENT ON COLUMN public.secretary_rule_checks.id IS '番号';
COMMENT ON COLUMN public.secretary_rule_checks.tenant_id IS '会社の番号（public.tenants.id）';
COMMENT ON COLUMN public.secretary_rule_checks.started_by IS '試しを始めた人（public.users.id）。人が消えたら空になる';
COMMENT ON COLUMN public.secretary_rule_checks.sdk IS '試しに使った AI の道具の名前（値の一覧は backend/app/services/llm_budget.py の USAGE_SDKS が正本）';
COMMENT ON COLUMN public.secretary_rule_checks.model IS '試しに使った AI のモデルの名前';
COMMENT ON COLUMN public.secretary_rule_checks.rules_count IS '試しのときに付けていた決まりの数';
COMMENT ON COLUMN public.secretary_rule_checks.status IS '状態: running=実行中・done=終わった・failed=途中で失敗';
COMMENT ON COLUMN public.secretary_rule_checks.ok IS '種類が合った件数';
COMMENT ON COLUMN public.secretary_rule_checks.ng IS '種類が合わなかった件数';
COMMENT ON COLUMN public.secretary_rule_checks.unmeasured IS '測れなかった件数（混み合い・時間切れでやり直しても取れなかった）';
COMMENT ON COLUMN public.secretary_rule_checks.total IS '試しの件数';
COMMENT ON COLUMN public.secretary_rule_checks.started_at IS '始めた時刻';
COMMENT ON COLUMN public.secretary_rule_checks.progress_at IS '最後に進んだ時刻（止まっていないかを見る）';
COMMENT ON COLUMN public.secretary_rule_checks.finished_at IS '終わった時刻。実行中のあいだは空';

ALTER TABLE public.secretary_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.secretary_rules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS secretary_rules_tenant ON public.secretary_rules;
CREATE POLICY secretary_rules_tenant ON public.secretary_rules FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
           OR current_setting('app.is_operator', true) = 'true')
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                OR current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.secretary_rule_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.secretary_rule_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS secretary_rule_checks_tenant ON public.secretary_rule_checks;
CREATE POLICY secretary_rule_checks_tenant ON public.secretary_rule_checks FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
           OR current_setting('app.is_operator', true) = 'true')
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                OR current_setting('app.is_operator', true) = 'true');

-- 使用の記録の使いみちに secretary_regression を足す（定義に値があれば何もしない。形は 20261103_120000_create_ai_job_assignments.sql の 1-7 と同じ）
DO $$
DECLARE
    purpose_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO purpose_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_purpose_check';

    IF purpose_def IS NULL OR purpose_def NOT LIKE '%secretary_regression%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_purpose_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_purpose_check
            CHECK (purpose IN ('line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent', 'secretary_regression'));
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.secretary_rules, public.secretary_rule_checks TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.secretary_rules_id_seq, public.secretary_rule_checks_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
```

## 戻しの中身

```sql
-- ADR-1077 便1 の戻し（手動実行のみ・本番デプロイでは実行しない）。2 表と方針・索引を消す。
-- 使いみちの CHECK は戻さない（便2 の後に secretary_regression の行があると、狭めると失敗するため。値が 1 つ多く許されるだけで害は無い）。
BEGIN;
DROP TABLE IF EXISTS public.secretary_rule_checks;
DROP TABLE IF EXISTS public.secretary_rules;
COMMIT;
```

## 分類に足す行

`migrations/20261024_100300_create_ai_cloud_views.sql` の VALUES の中に、この 5 行（8 列）を足す。理由の文は 1 文字も変えない。足す位置が VALUES の最後になる場合は、最後の行の末尾のカンマを先例の最後の行に合わせる。

```
  ('public','secretary_rule_checks',ARRAY['model','sdk'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('public','secretary_rule_checks',ARRAY['status'],'allow','値の決まり ck_secretary_rule_checks_status で値が限られる'),
  ('public','secretary_rules',ARRAY['rule_text','source_reply','source_text'],'mask',''),
  ('public','secretary_rules',ARRAY['source_kind'],'allow','値の決まり ck_secretary_rules_source_kind で値が限られる'),
  ('public','secretary_rules',ARRAY['status'],'allow','値の決まり ck_secretary_rules_status で値が限られる'),
```

（数えるのは列の数＝8。mask の行の理由の欄の書き方（空でよいか）は、同じファイルの既存の mask の行に合わせる。合わせ方が分からなければ NEEDS_DECISION:。）

## 試験の決まり（`backend/tests/test_secretary_rules_tables_pg.py`）

- 先例の形をそのまま使う: `backend/tests/test_viewer_contract_public_tables_pg.py` の `needs_ci_pg`（:27-30）・`_app_conn_and_url`（:82-88）・`pg` fixture の import（:23-24）。表の定義を試験に写さない（`scripts/check_test_schema_dup.py`）。表は本物の migration を流して作る。
- 下ごしらえ（管理者の接続）: `pg` fixture が試験ごとに使い捨ての DB を作り、`public.tenants`・`public.users`（`_ensure_public_users`）・`public.llm_usage_events`（`:338` で作り、`:421` の `20261103_120000_create_ai_job_assignments.sql` で今の 7 値の CHECK に広がる）まで用意し、試験の後に DB ごと消す（`backend/tests/test_tcg_work_matching_integration.py:385-432`）。だから試験では新しい migration を 2 回流す（冪等）だけにし、`_ensure_public_users` や使用の記録の migration を流し直さない。後片付けの DELETE も書かない（DB ごと消える）。会社は 999（`_ensure_public_users` が入れる）に加えて 998 を管理者で入れ、利用者を各社 1 人ずつ管理者で入れる。名前やメールは作り物。
- 試験（すべて `@needs_ci_pg`）:
  1. `test_tables_and_columns_match_design`: 2 表の列の名前の集合が、design.md §4 の一覧（secretary_rules 11 列・secretary_rule_checks 14 列）と同じ（R9）。`information_schema.columns` で読む。
  2. `test_rls_four_cells`: アプリの役割（`rolsuper`・`rolbypassrls` が両方 False であることを先に確かめる）で、`SET app.tenant_id = '999'` のとき 999 の行だけが見え、998 の行は見えない・998 の行の UPDATE は 0 行・998 の会社番号での INSERT は 42501。承認済みと候補の 2 状態 × 2 社の 4 マスを管理者で入れておき、見える数が 2 であることを確かめる（R5）。`secretary_rule_checks` も 1 社 1 行ずつで同じことを確かめる。
  3. `test_operator_context_reads_all`: `SET app.is_operator = 'true'`（app.tenant_id は空）で 2 表とも全社の行が見える。
  4. `test_no_context_sees_nothing`: どちらも付けないと 2 表とも 0 行・INSERT は 42501。
  5. `test_app_role_cannot_delete`: 自社の文脈でも DELETE は権限の誤り（42501）。
  6. `test_checks`: 次の INSERT が CHECK の誤り（23514）になる。status が `other`／approved で rule_text が空白だけ／rule_text が 151 字／source_kind が `other`／candidate なのに decided_at あり／approved なのに decided_at なし／試しで ok+ng+unmeasured が total を超える／試しで status が done なのに finished_at なし。
  7. `test_purpose_check_has_secretary_regression`: `pg_get_constraintdef` の結果に 8 つの値（今の 7 つ＋`secretary_regression`）がすべて入る。migration をもう 1 回流しても定義の文字列が変わらない。
- 試験の中で外の AI・本番・ネットワークは呼ばない。

## 触らない

- `backend/app` の .py・`frontend`・`.github/workflows`（やること 5c の `migration-guard.yml` の `PUBLIC_TABLES` の 1 行だけは直す）・`secretary-agent`・`secretary-codex`・`docker-compose*.yml`。
- `backend/app/services/llm_budget.py` の USAGE_PURPOSES と `backend/tests/test_llm_usage_isolated.py`（便2 で直す・上の「決めたこと」）。
- design.md・kgi.md・recon.md・research.md・baseline.md・ADR（Opus が直す）。
- 本番のサーバー・本番の DB（本番に当てるのは Opus。PO の GO の後）。

## 想定される分かれ道

- CI の `migration-test.yml` の流し（本物の DB に全 migration を当てる）が新しい migration で落ちる → 直さずに、落ちた step の名前と生の出力を添えて NEEDS_DECISION:。
- `test_ai_cloud_views.py` のほかの試験（ai_ro 側の分類など）が新しい表の列で落ちる → 直さずに NEEDS_DECISION:（分類の置き場が他にもあるかは Opus が決める）。
- やること 6 の試験が、この 8 列のほかにも分類の漏れの列（例: created_by など）を挙げる → 推測で行を足さずに、挙がった列の一覧を添えて NEEDS_DECISION:。
- `public.users.id` が CI の DB で INTEGER でない（BIGINT など）で外部キーが張れない → 型を推測で変えずに BLOCKED:。
- `scripts/run_all_migrations.sh` の最後の行が 1269 行目の行でない（だれかが先に足した）→ その行の後ろに足す。足した位置の前後 3 行を報告に貼る。
- check-before-submit が落ちる → 直さずに、落ちた検査の名前とログの最後 30 行を添えて NEEDS_DECISION:。

## Opus が本番に当てる前に確かめること（実装役はしない）

- 本番の `public.llm_usage_events` の行数と大きさ（使いみちの CHECK を付け替えるとき表全体を読む）。**まだ確かめていない**（2026-11-12 の読み取りは自動判定で止まった）。同じ付け替えは 2026-11-03 の migration（`migrations/20261103_120000_create_ai_job_assignments.sql:148-175` 相当）で本番に当てて通っている。
- 本番の `public.users.id` の型（INTEGER の前提）。
- 本番で `public.secretary_rules` がまだ無いこと。

## 終わりの報告（停止したときも同じ形で報告する）

- DONE: 受領確認の行・preflight の生出力・(1f) の出力・やること 4 と 5 の生出力・commit の sha・check-before-submit の結果ファイルのパスと最後の 5 行・push の生出力。
- BLOCKED: 止まった手順・コマンド・生の出力。
- NEEDS_DECISION: 迷った点・選べる形・それぞれの影響。

END OF CARD
