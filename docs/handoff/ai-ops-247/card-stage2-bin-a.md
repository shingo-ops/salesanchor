# 実装カード 段階2 便A — 障害記録の表を作る（空のまま）

> この文書は何か：AI保守運用24時間化 段階2 便A の作業指示書です。障害の記録を入れる表 3 つを、本番 DB の public に空のまま作ります。表を読み書きできるのは運用者の旗が立った接続だけで、記録は消せません。表に書き込むコード（保守 API）は便B で作るので、この便では書きません。

- 設計: docs/handoff/ai-ops-247/stage2-design.md §2 便A・§1 T7〜T10・§6
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階2（:103-110）・配線と DB の正本（:63-73）
- 対象ADR: ADR-1012（本テーマ）、ADR-1018（RLS の型）、ADR-155（migration は構造の変更だけ）、ADR-136（危険 PR の GO）
- 状態: 設計は Opus 自己審査 APPROVE（stage2-design.md §9・#4355 マージ済み 2259c6e6d）。段階2 の着手は PO の「次を進める」（2026-10-16）
- 危険便: はい（`migrations/`・`scripts/run_all_migrations.sh` を含む）。GO は ADR-136 の手順で Opus（PO の委任）が出す。担当はマージしない
- 担当: 実装 Sonnet／コード審査・GO・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（表を作るだけ。書き込むコードは便B） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に SQL の完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から（ポリシー数・権限は §4 の SQL から決まる） | ○ |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない（本番の確認は Opus が PO の `!` で行う） | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階2 便A の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新しい migration ファイル 1 本（§4-1 の SQL そのまま）
2. `scripts/run_all_migrations.sh` の末尾に登録の 1 行（§4-2）
3. 新しい試験ファイル 1 本（§4-3）

入れない:
- 表に書き込むコード・API・ルーター（便B）
- 初めの 1 行などの値の書き込み（ADR-155。`INSERT`・`UPDATE`・`DELETE` を migration に書かない）
- `backend/tests/rls_bootstrap.py` の変更（試験は自分で migration を当てる。§4-3）
- ほかの表の RLS・権限

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | migration は `migrations/` の生 SQL で、`scripts/run_all_migrations.sh` の `run_sql` 1 行で登録する。いまの末尾は `run_sql migrations/20261016_020000_add_suppliers_rls.sql` | `scripts/run_all_migrations.sh`（末尾） |
| F2 | 運用者だけに書き込みを許す RLS の型：`ENABLE`＋`FORCE`、条件は `current_setting('app.is_operator', true) = 'true'` | `migrations/20261015_130000_add_permissions_rls.sql:1-13` |
| F3 | アプリのロールへの権限の付け方：`DO $$ ... IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN GRANT ... END IF; END $$;` | `migrations/20261013_160000_add_self_hosted_auth_tables.sql:95-101` |
| F4 | public の新しい表には、所有者 jarvis の既定の権限で `salesanchor_app` に SELECT・INSERT・UPDATE・DELETE が自動で付く（CI の準備で同じ設定）。そのため DELETE などを外すには `REVOKE` が要る | `.github/workflows/test.yml` の `ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public` の行・`migrations/20260605_030000_create_salesanchor_app_role.sql` |
| F5 | RLS の試験の型：`RLS_ADMIN_DATABASE_URL`（jarvis）と `RLS_TEST_DATABASE_URL`（salesanchor_app）の 2 本の接続。どちらかが無ければ skip | `backend/tests/test_permissions_rls.py:1-60` |
| F6 | migration を試験の中で当てる関数 `_apply_migration(admin_engine, filename)` と、xdist で直列にする `public_bootstrap_lock(admin_engine)` がある | `backend/tests/rls_bootstrap.py:68`・`:45` |
| F7 | 値の書き込み検査は、保護対象の表への `INSERT`・`UPDATE`・`DELETE` を落とす。新しい表は保護対象に無いが、ADR-155 の方針で値の書き込みはそもそも書かない | `scripts/check-migration-value-writes.py:1-14` |
| F8 | 本番の `salesanchor_app` は RLS を飛ばせない（`rolbypassrls=f`）。jarvis は superuser | /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/explain/result.txt Q6 |
| F9 | deploy は migration のパスを含む変更のとき、先に DB を自動でバックアップする | `.github/workflows/deploy.yml:47-58` |

## 3. 触るファイル（これ以外は触らない）

- 新規: `migrations/20261016_100000_create_ops_incident_tables.sql`
- 変更: `scripts/run_all_migrations.sh`（末尾に 2 行の追記のみ）
- 新規: `backend/tests/test_ops_incident_tables_rls.py`
- 変更: `docs/handoff/ai-ops-247/card-stage2-bin-a.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. migration（この SQL をそのまま書く。1 文字も足し引きしない）

```sql
-- ADR-1012 段階2 便A: 障害記録の表（public）。読み書きとも運用者の旗が立った接続だけ。記録は消せない。
-- 値の書き込みはしない（ADR-155）。書き込むのは便B の保守 API だけ。冪等。

-- 1. 1 件の障害 = 1 行（Alertmanager の fingerprint と startsAt で 1 件）
CREATE TABLE IF NOT EXISTS public.ops_incidents (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint           TEXT        NOT NULL,
    starts_at             TIMESTAMPTZ NOT NULL,
    alertname             TEXT        NOT NULL,
    severity              TEXT,
    labels                JSONB       NOT NULL DEFAULT '{}'::jsonb,
    annotations           JSONB       NOT NULL DEFAULT '{}'::jsonb,
    status                TEXT        NOT NULL,
    first_notified_at     TIMESTAMPTZ NOT NULL,
    last_notified_at      TIMESTAMPTZ NOT NULL,
    notify_count          INTEGER     NOT NULL DEFAULT 1,
    resolved_at           TIMESTAMPTZ,
    recurrence_of         UUID        REFERENCES public.ops_incidents(id),
    detection_path        TEXT        NOT NULL DEFAULT 'alert',
    human_noticed_at      TIMESTAMPTZ,
    needs_action          BOOLEAN,
    first_aid_started_at  TIMESTAMPTZ,
    first_aid_done_at     TIMESTAMPTZ,
    first_aid_result      TEXT,
    ai_started_at         TIMESTAMPTZ,
    root_cause            TEXT,
    fix_pr                INTEGER,
    review_note           TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ops_incidents_fingerprint_starts_at_key UNIQUE (fingerprint, starts_at),
    CONSTRAINT ops_incidents_status_check CHECK (status IN ('firing', 'resolved')),
    CONSTRAINT ops_incidents_detection_path_check CHECK (detection_path IN ('alert', 'human', 'ai')),
    CONSTRAINT ops_incidents_first_aid_result_check
        CHECK (first_aid_result IN ('recovered', 'not_recovered', 'escalated')),
    CONSTRAINT ops_incidents_notify_count_check CHECK (notify_count >= 1),
    CONSTRAINT ops_incidents_labels_size_check CHECK (octet_length(labels::text) <= 4096),
    CONSTRAINT ops_incidents_annotations_size_check CHECK (octet_length(annotations::text) <= 4096)
);

CREATE INDEX IF NOT EXISTS ix_ops_incidents_fingerprint_starts_at
    ON public.ops_incidents (fingerprint, starts_at DESC);
CREATE INDEX IF NOT EXISTS ix_ops_incidents_first_notified_at
    ON public.ops_incidents (first_notified_at);

-- 2. 出来事の記録（追記だけ）
CREATE TABLE IF NOT EXISTS public.ops_incident_events (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id  UUID        NOT NULL REFERENCES public.ops_incidents(id),
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind         TEXT        NOT NULL,
    actor        TEXT        NOT NULL,
    detail       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ops_incident_events_kind_check
        CHECK (kind IN ('notified', 'resolved', 'annotated', 'first_aid', 'ai', 'halt')),
    CONSTRAINT ops_incident_events_actor_check
        CHECK (actor IN ('alertmanager', 'ops_token', 'super_admin')),
    CONSTRAINT ops_incident_events_detail_size_check CHECK (octet_length(detail::text) <= 8192)
);

CREATE INDEX IF NOT EXISTS ix_ops_incident_events_incident_id_occurred_at
    ON public.ops_incident_events (incident_id, occurred_at);

-- 3. 全停止スイッチ（1 行だけ。行が無いときは「止めていない」として扱う。最初の行は便B の API が作る）
CREATE TABLE IF NOT EXISTS public.ops_control (
    id          SMALLINT    PRIMARY KEY,
    halt_all    BOOLEAN     NOT NULL DEFAULT false,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by  TEXT        NOT NULL,
    reason      TEXT,
    CONSTRAINT ops_control_single_row_check CHECK (id = 1)
);

COMMENT ON TABLE public.ops_incidents IS 'ADR-1012 段階2: 障害 1 件 = 1 行。書き込みは保守 API だけ';
COMMENT ON TABLE public.ops_incident_events IS 'ADR-1012 段階2: 障害の出来事の記録。追記だけ';
COMMENT ON TABLE public.ops_control IS 'ADR-1012 段階2: 全停止スイッチ。id=1 の 1 行だけ。行が無いときは止めていない';

-- 4. RLS（運用者の旗が立った接続だけ。DELETE のポリシーは作らない）
ALTER TABLE public.ops_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incidents FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incident_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incident_events FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ops_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_control FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ops_incidents_operator_select ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_select ON public.ops_incidents
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incidents_operator_insert ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_insert ON public.ops_incidents
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incidents_operator_update ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_update ON public.ops_incidents
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS ops_incident_events_operator_select ON public.ops_incident_events;
CREATE POLICY ops_incident_events_operator_select ON public.ops_incident_events
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incident_events_operator_insert ON public.ops_incident_events;
CREATE POLICY ops_incident_events_operator_insert ON public.ops_incident_events
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS ops_control_operator_select ON public.ops_control;
CREATE POLICY ops_control_operator_select ON public.ops_control
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_control_operator_insert ON public.ops_control;
CREATE POLICY ops_control_operator_insert ON public.ops_control
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_control_operator_update ON public.ops_control;
CREATE POLICY ops_control_operator_update ON public.ops_control
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

-- 5. アプリのロールの権限（既定の権限で付いた DELETE などを外す）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.ops_incidents, public.ops_control TO salesanchor_app;
        GRANT SELECT, INSERT ON public.ops_incident_events TO salesanchor_app;
        REVOKE DELETE, TRUNCATE ON public.ops_incidents, public.ops_control FROM salesanchor_app;
        REVOKE UPDATE, DELETE, TRUNCATE ON public.ops_incident_events FROM salesanchor_app;
    END IF;
END $$;
```

### 4-2. 登録（`scripts/run_all_migrations.sh` の最後の行の後ろに、この 2 行を足す）

```bash

# ADR-1012 段階2 便A: 障害記録の表 3 つ（空・RLS は運用者だけ・記録は消せない）
run_sql migrations/20261016_100000_create_ops_incident_tables.sql
```

（1 行目は空行。足す前に、最後の行が `run_sql migrations/20261016_020000_add_suppliers_rls.sql` であることを確かめる。違えば §6 の分岐）

### 4-3. 試験 `backend/tests/test_ops_incident_tables_rls.py`

- 冒頭の環境の扱い（2 本の接続・skip の条件・`pytest.mark.asyncio`）は `backend/tests/test_permissions_rls.py:1-25` と同じ書き方にする
- 準備：管理の接続（jarvis）で `public_bootstrap_lock(admin_engine)` の中で `_apply_migration(admin_engine, "20261016_100000_create_ops_incident_tables.sql")` を呼ぶ（冪等なので毎回呼んでよい）
- 試験で作る行の `fingerprint` は `"test-ops-rls-" + uuid4().hex` にする。後片付けは管理の接続で、その fingerprint の行の出来事 → 障害の順に消す。ops_control を触る試験は 1 本だけにし、後片付けで管理の接続から `id = 1` の行を消す
- 運用者の旗は、アプリの接続のトランザクションの中で `SELECT set_config('app.is_operator', 'true', true)` で立てる
- 試験は次の 7 本（名前もこのとおり）:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_insert_denied_without_operator_flag` | 旗なしで ops_incidents に INSERT → `DBAPIError`、元の例外の `sqlstate` が `42501` |
| 2 | `test_operator_can_insert_and_select_incident_and_event` | 旗ありで障害 1 行と出来事 1 行を INSERT し、同じトランザクションで SELECT すると両方 1 行ずつ見える |
| 3 | `test_rows_invisible_without_operator_flag` | 2 と同じように作って commit した後、旗なしの別の接続で、その fingerprint の障害の SELECT が 0 行 |
| 4 | `test_delete_denied_even_with_operator_flag` | 旗ありで、3 表それぞれの DELETE → `42501`（権限がない） |
| 5 | `test_event_update_denied_even_with_operator_flag` | 旗ありで ops_incident_events の UPDATE → `42501` |
| 6 | `test_duplicate_fingerprint_starts_at_rejected` | 旗ありで同じ (fingerprint, starts_at) を 2 回 INSERT → 2 回目が `23505` |
| 7 | `test_ops_control_allows_only_id_1` | 旗ありで ops_control に id=1 の INSERT は通り、id=2 の INSERT は `23514` |

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 値の書き込みが無いこと：作業場所で `grep -nEi "^\s*(INSERT|UPDATE|DELETE)\b" migrations/20261016_100000_create_ops_incident_tables.sql` の出力が 0 行。あわせて `python3 scripts/check-migration-value-writes.py repo` の終了コードが 0。

5-2. 試験：手元に PostgreSQL が無い場合、試験は skip になる。そのときは `cd backend && python3 -m pytest tests/test_ops_incident_tables_rls.py -q` の出力（skip の数が 7）を貼り、「手元では skip・CI の pytest-run-internal で実行」と書く。手元で走るなら 7 passed を貼る。

5-3. 名前の対：`grep -nE "CREATE POLICY ops_" migrations/20261016_100000_create_ops_incident_tables.sql` の出力が 8 行で、名前が ops_incidents_operator_select・ops_incidents_operator_insert・ops_incidents_operator_update・ops_incident_events_operator_select・ops_incident_events_operator_insert・ops_control_operator_select・ops_control_operator_insert・ops_control_operator_update の 8 つであること。

5-4. `git diff origin/main --stat` が 4 ファイル（§3）であること。

5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI は Opus が見る）。

## 6. 分岐ごとの対処

- 4-2 で最後の行が違う（ほかの PR が先に migration を足した）→ その行の後ろに足す。新しい migration のファイル名の日時が、最後の行のファイル名の日時より前になるなら、作業を止めて NEEDS_DECISION: でファイル名を報告する（日時の順を Opus が決め直す）。
- 5-1 で 1 行以上出る → 4-1 の SQL を写し間違えている。4-1 のとおりに直す。
- 試験で 4 か 5 が通らず、`42501` 以外の失敗になる → 失敗の出力をそのまま貼って BLOCKED: で止まる（権限の設計の誤りかを Opus が見る）。
- 試験が CI で `rls_bootstrap` の準備の段で落ちる → 自分の試験の準備の書き方を確かめる。`rls_bootstrap.py` は変えない。直せなければ BLOCKED:。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| migration に値の書き込みが 0 行 | §5-1 |
| ポリシーが 8 つ、名前が決めたとおり | §5-3 |
| 旗なしでは書けず・見えず、旗ありでも消せず、出来事は直せない | CI の pytest（§4-3 の 7 本が passed） |
| 触ったファイルが 4 つ | §5-4 |
| 反映後、本番に 3 表があり、RLS・ポリシー・権限が §4-1 のとおり | §8（Opus が PO の `!` で読む） |

## 8. 本番での確認（マージ・deploy の後。Opus が行う。担当はしない）

- deploy の migration の段の成功と、自動バックアップの成功を Actions の記録で確かめる
- PO の `!` スクリプト（読み取りのみ・`default_transaction_read_only = on`）で、次を読む：3 表の `relrowsecurity`・`relforcerowsecurity`、`pg_policies` の表ごとの数（3・2・3）、`has_table_privilege('salesanchor_app', 表, 'DELETE')` が 3 表とも false、ops_incident_events の UPDATE が false、3 表の行数が 0
- 生出力は /tmp/CC報告ファイル/ai-ops-stage2-bin-a/deploy/ に置く

## 9. 戻し方

- repo：この PR の revert（表は残る。表が残っても使う口が無いので害は無い）
- 表を消す：DROP TABLE は不可逆操作で PO の確認が要る。表が空のうちに、段階2 をやめると決めたときだけ別の migration で行う

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage2-bin-a --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage2-bin-a` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（ruff がその場所にあり PATH に無いため。`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage2-bin-a -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを渡して作る。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage2-bin-a --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない（危険便。GO は Opus）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage2-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし（良い例: 触るファイル: migrations/20261016_100000_create_ops_incident_tables.sql, scripts/run_all_migrations.sh, backend/tests/test_ops_incident_tables_rls.py, docs/handoff/ai-ops-247/card-stage2-bin-a.md ／ 削除するファイル: docs/handoff/ai-ops-247/card-stage2-bin-a.md（§13 の「（未記入）」の行を書き換えるため）。注記は付けずにファイル名だけを書く）
- `### GO記録` は担当が書かない（Opus が書く）。本文に「GO 待ち（危険便・ADR-136）」と 1 行書く
- 本文に IP・URL の秘密・鍵のパスを書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage2-bin-a/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

- 5-1: 値の書き込みの grep は 0 行。`python3 scripts/check-migration-value-writes.py repo` は終了コード 0
- 5-2: 手元では 7 skipped（実 PostgreSQL 環境なし）。CI の pytest-run-internal で実行
- 5-3: `CREATE POLICY ops_` は 8 行・名前は §5-3 のとおり
- 5-4: 変更は 4 ファイル（§3）
- 生出力: /tmp/CC報告ファイル/ai-ops-stage2-bin-a/impl/

END OF CARD
