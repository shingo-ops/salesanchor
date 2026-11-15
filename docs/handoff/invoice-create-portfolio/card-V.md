# card: 便V 振込先を版で持つ（列2つ・見張りの関数3つ・見張り6つ。invoice-create-portfolio）

状態: カード発行（Opus、2026-11-15）。PO の設計承認と実装承認は 2026-11-14 の「1,」（振込先を版で持つ案。ADR-1079）と、2026-11-13 の常設の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」。
設計: docs/handoff/invoice-create-portfolio/design.md §3-8（便V）・§8 の K25・ADR-1079。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `25cc56065` で行番号と数を測った。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` に新しい SQL を足し、`scripts/run_all_migrations.sh` を変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 この便は「形と見張りを作るだけ」。画面・API・請求書の作り方は後の便で行う。値は入れない（ADR-155）。
- D2 会社ごとのスキーマの振込先の一覧 `tenant_invoice_payment_methods` に2列を足す: `superseded_by_id`（INTEGER・NULL 可。次の版の番号）と `deleted_at`（TIMESTAMPTZ・NULL 可。消した時刻）。どちらも最後の列 updated_at の後ろに置く（移行の ADD COLUMN と同じ並び）。
- D3 決まりを3つ足す: 自分を指さない CHECK `chk_tenant_invoice_payment_methods_superseded_not_self`・同じ表の id を指す外部キー `fk_tenant_invoice_payment_methods_superseded_by`（ON DELETE は付けない。行は消せないので要らない）・次の版を指せるのは前の版1つだけの一意索引 `uq_tenant_invoice_payment_methods_superseded_by`（superseded_by_id が NULL の行は数えない）。
- D4 見張りの関数3つ（会社ごとのスキーマに置く）: 詳細は書き足すだけで、今の版にしか足せない `trg_payment_detail_immutable`・振込先の行は消せず、版の中身（id・tenant_id・region・method_type・display_name・created_at）は書き換えられず、次の版と消した時刻は1回だけ付けられる `trg_payment_method_version_guard`・表を空にさせない `trg_payment_version_no_wipe`。直してよいのは sort_order・is_active・updated_by_user_id・updated_at だけ。中身は §2-1 と §2-2 の全文。
- D5 見張り6つ: 一覧に1つ（行ごと・足す/直す/消すの前）、銀行と Wise の詳細に1つずつ（同じ）、3表それぞれに空にする前の見張り（文ごと）。表の持ち主の役でも止まる（見張りは役を見ない）。
- D6 関数は表を `TG_TABLE_SCHEMA`（見張りが付いた表のスキーマ）で引く。呼び出し側の search_path に頼らない（design.md §3-8）。試験で search_path を public にして確かめる。
- D7 関数の中身の正本は1つ。tenant.py と移行の両方に同じ文を書き、試験 test_function_bodies_are_the_same_in_ddl_and_migration で一字一句同じかを確かめる（片方だけ直すと CI が赤になる）。
- D8 詳細の表の外部キーの ON DELETE CASCADE は残す。一覧の行を消す道が見張りで閉じるので、連鎖は起きない。会社を消すときの DROP SCHEMA … CASCADE（backend/app/routers/super_admin_tenants.py:167）は見張りを通らないので、今のまま消せる。
- D9 足す列は数と時刻の型なので、分類表（migrations/20261024_100300_create_ai_cloud_views.sql）に行は要らない（型で通る。便A の D6 と同じ）。口座番号の列には触らない（ADR-1061 決定9 の名前による隠し方がそのまま効く）。
- D10 移行の試験のテナント番号は 957（2026-11-15 に 25cc56065 で backend/tests・migrations・scripts を git grep して 0 件）。
- D11 本番の振込先と請求書の行は 2026-11-14 に読み取り用の鍵で数えて全社 0 件。足す列は NULL 可なので、既にある行があっても書き換えは起きない。
- D12 見張りの関数は一覧の行を `FOR SHARE` で読む（同時に版を付けかえる取引とぶつからないように）。`FOR SHARE` は表の UPDATE 権限が要り、アプリの役は持っている（既存の振込先の表の権限のまま。この便で権限は変えない）。
- D13 既存の試験 backend/tests/test_tenant_issuer_tables_pg.py は「振込先を消すと詳細も消える」を確かめていた。この便で行は消せなくなるので、「消そうとすると P0001 で止まり、詳細は残る」に直す。あわせて、表を作り直す PG 試験で便Vの移行も2回流し、形の比べ（_shape）に索引・見張り6つの定義・関数3つの中身（pg_get_functiondef）を足す（設計 K25・§2-4）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（振込先を版で持つ形と見張りを作る。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/invoice-create-portfolio-bin-v-impl` を作る） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順7 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P9 は 25cc56065 で実測。tenant.py と既存試験の足す・消す行の数は写しに §2 を当てて実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-create-portfolio-V HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便V 振込先を版で持つ の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/invoice-create-portfolio/card-V.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261113_200001_add_ops_case_report_kind_down.sql`。
- P3 `grep -c -E "superseded_by|trg_payment|pv_detail|_no_wipe|payment_versioning"` が backend/app/services/tenant.py・backend/tests/rls_bootstrap.py・backend/tests/test_tenant_loop_migration_guard.py・scripts/run_all_migrations.sh・backend/tests/test_tenant_issuer_tables_pg.py でそれぞれ 0。
- P4 `grep -c "957"` が backend/tests/rls_bootstrap.py と backend/tests/test_tenant_loop_migration_guard.py でそれぞれ 0。
- P5 次の3つの文が backend/app/services/tenant.py にそれぞれ 1 か所: `    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),`・`    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '')`・`-- invoice-create-portfolio 便A: 関税の決まり（行き先の国・送料の会社ごと。DDP のときに使う）`。
- P6 `wc -l < backend/app/services/tenant.py` が 2091。`wc -l < scripts/run_all_migrations.sh` が 1277。`wc -l < backend/tests/test_tenant_issuer_tables_pg.py` が 306。
- P7 `tail -1 scripts/run_all_migrations.sh` が `# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_200001_add_ops_case_report_kind_down.sql`。
- P8 `grep -c "振込先を消すと詳細も消える" backend/tests/test_tenant_issuer_tables_pg.py` が 1。
- P9 `ls migrations/20261115_100000_add_payment_method_versioning.sql` が「無い」。`ls backend/tests/test_tenant_payment_versioning_pg.py` も「無い」。

## 1. 触るファイル

1. migrations/20261115_100000_add_payment_method_versioning.sql（新規）
2. backend/app/services/tenant.py（3か所。1行を直し、ほかは足すだけ）
3. backend/tests/test_tenant_issuer_tables_pg.py（5か所）
4. backend/tests/test_tenant_payment_versioning_pg.py（新規）
5. backend/tests/rls_bootstrap.py（1か所に足す）
6. backend/tests/test_tenant_loop_migration_guard.py（3か所）
7. scripts/run_all_migrations.sh（最後に2行足す）

触らない: docs/ の全部（このカードを含む）・frontend/・backend/app のほかのファイル・migrations のほかのファイル・.github/workflows の全部（特に workflow-lint.yml）・scripts/migration-guard の全部。

## 2. 変更

### 2-1. migrations/20261115_100000_add_payment_method_versioning.sql（新規。全文。Write ツールで、下の囲みの中身をそのまま書く。最後は改行で終わる）

````sql
-- invoice-create-portfolio 便V: 振込先を版で持つ（design.md §3-8・ADR-1079）
-- 目的: 振込先を直しても消しても前の版を残し、発行済みの請求書が元の振込先を指し続けるようにする。
-- 中身（全テナント・冪等）:
--   tenant_invoice_payment_methods に superseded_by_id（次の版）と deleted_at（消した時刻）を足す
--   次の版を自分に向けない決まり・同じ表への外部キー・次の版は前の版1つだけの一意索引
--   見張りの関数3つと見張り6つ（振込先の行は消さない・版は書き換えない・詳細は書き足すだけ・表を空にしない）
-- 決まり: ADR-155（全テナントを回す移行）・ロック待ちは run_sql の lock_timeout に従う（ADR-1037）
-- 戻し方（手で流す。ここには書くだけ）:
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_methods_version_guard ON <schema>.tenant_invoice_payment_methods
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_bank_immutable ON <schema>.tenant_invoice_payment_bank
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_wise_immutable ON <schema>.tenant_invoice_payment_wise
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_methods_no_wipe ON <schema>.tenant_invoice_payment_methods
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_bank_no_wipe ON <schema>.tenant_invoice_payment_bank
--   DROP TRIGGER IF EXISTS trg_tenant_invoice_payment_wise_no_wipe ON <schema>.tenant_invoice_payment_wise
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_detail_immutable()
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_method_version_guard()
--   DROP FUNCTION IF EXISTS <schema>.trg_payment_version_no_wipe()
--   DROP INDEX IF EXISTS <schema>.uq_tenant_invoice_payment_methods_superseded_by
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP CONSTRAINT IF EXISTS fk_tenant_invoice_payment_methods_superseded_by
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP CONSTRAINT IF EXISTS chk_tenant_invoice_payment_methods_superseded_not_self
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP COLUMN IF EXISTS deleted_at
--   ALTER TABLE <schema>.tenant_invoice_payment_methods DROP COLUMN IF EXISTS superseded_by_id

DO $$
DECLARE
    r RECORD;
    v_count INTEGER := 0;
    v_methods REGCLASS;
    v_detail CONSTANT TEXT := $pv_detail$
DECLARE
    v_id INTEGER;
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'payment detail rows are immutable (versioned). Add a new version instead.';
    END IF;
    IF NEW.payment_method_id IS NOT NULL THEN
        EXECUTE 'SELECT id, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.payment_method_id || ' FOR SHARE'
            INTO v_id, v_superseded, v_deleted;
        IF v_id IS NULL OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'payment detail can be added only to the current version of a payment method';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_detail$;
    v_method CONSTANT TEXT := $pv_method$
DECLARE
    v_id INTEGER;
    v_region VARCHAR(20);
    v_type VARCHAR(10);
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'payment methods cannot be deleted. Set deleted_at instead.';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.superseded_by_id IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a new payment method must start as the current version';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.region IS DISTINCT FROM OLD.region
        OR NEW.method_type IS DISTINCT FROM OLD.method_type
        OR NEW.display_name IS DISTINCT FROM OLD.display_name
        OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'payment method versions are immutable. Add a new version instead.';
    END IF;
    IF OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id THEN
        RAISE EXCEPTION 'superseded_by_id can be set only once';
    END IF;
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
        RAISE EXCEPTION 'deleted_at can be set only once';
    END IF;
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL
        AND (OLD.superseded_by_id IS NOT NULL OR NEW.superseded_by_id IS NOT NULL) THEN
        RAISE EXCEPTION 'only the current version can be deleted';
    END IF;
    IF OLD.superseded_by_id IS NULL AND NEW.superseded_by_id IS NOT NULL THEN
        IF OLD.deleted_at IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a deleted payment method cannot be superseded';
        END IF;
        IF NEW.superseded_by_id <= OLD.id THEN
            RAISE EXCEPTION 'the next version must be newer than the current version';
        END IF;
        EXECUTE 'SELECT id, region, method_type, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.superseded_by_id || ' FOR SHARE'
            INTO v_id, v_region, v_type, v_superseded, v_deleted;
        IF v_id IS NULL OR v_region IS DISTINCT FROM OLD.region OR v_type IS DISTINCT FROM OLD.method_type
            OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'the next version must be a current version of the same region and type';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_method$;
    v_wipe CONSTANT TEXT := $pv_wipe$
BEGIN
    RAISE EXCEPTION 'payment version tables cannot be truncated';
    RETURN NULL;
END;
$pv_wipe$;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        IF to_regclass(format('%I.tenant_invoice_payment_methods', r.nspname)) IS NULL THEN
            RAISE EXCEPTION 'tenant_invoice_payment_methods is missing in %', r.nspname;
        END IF;
        v_methods := format('%I.tenant_invoice_payment_methods', r.nspname)::regclass;
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD COLUMN IF NOT EXISTS superseded_by_id INTEGER', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ', r.nspname);
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = v_methods AND conname = 'chk_tenant_invoice_payment_methods_superseded_not_self') THEN
            EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = v_methods AND conname = 'fk_tenant_invoice_payment_methods_superseded_by') THEN
            EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ADD CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id) REFERENCES %I.tenant_invoice_payment_methods (id)', r.nspname, r.nspname);
        END IF;
        EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by ON %I.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL', r.nspname);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_detail_immutable() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_detail);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_method_version_guard() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_method);
        EXECUTE format('CREATE OR REPLACE FUNCTION %I.trg_payment_version_no_wipe() RETURNS TRIGGER AS %L LANGUAGE plpgsql', r.nspname, v_wipe);
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_version_guard' AND tgrelid = format('%I.tenant_invoice_payment_methods', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_methods_version_guard BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_methods FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_method_version_guard()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_immutable' AND tgrelid = format('%I.tenant_invoice_payment_bank', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_bank_immutable BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_bank FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_detail_immutable()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_immutable' AND tgrelid = format('%I.tenant_invoice_payment_wise', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_wise_immutable BEFORE INSERT OR UPDATE OR DELETE ON %I.tenant_invoice_payment_wise FOR EACH ROW EXECUTE FUNCTION %I.trg_payment_detail_immutable()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_methods', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_methods_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_methods FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_bank', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_bank_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_bank FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_no_wipe' AND tgrelid = format('%I.tenant_invoice_payment_wise', r.nspname)::regclass) THEN
            EXECUTE format('CREATE TRIGGER trg_tenant_invoice_payment_wise_no_wipe BEFORE TRUNCATE ON %I.tenant_invoice_payment_wise FOR EACH STATEMENT EXECUTE FUNCTION %I.trg_payment_version_no_wipe()', r.nspname, r.nspname);
        END IF;
        v_count := v_count + 1;
    END LOOP;
    RAISE NOTICE 'payment method versioning applied to % tenant schemas', v_count;
END $$;
````

### 2-2. backend/app/services/tenant.py（3か所）

(1) 振込先の一覧に2列を足す（:1277 の前）

変更前:
```
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
```

変更後:
```
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    superseded_by_id INTEGER,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
```

(2) 決まり2つと一意索引を足す（:1281-1282。最初の行の最後に `,` を付ける）

変更前:
```
    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '')
);
```

変更後:
```
    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> ''),
    CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id),
    CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id) REFERENCES {schema}.tenant_invoice_payment_methods (id)
);

-- invoice-create-portfolio 便V: 次の版を指せるのは前の版1つだけ（ADR-1079）
CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by ON {schema}.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL;
```

(3) 見張りの関数3つと見張り6つを、便A の関税の決まりの説明の行（:1324）の直前に足す。足すのは下の囲みの中身（最後の空の1行を含む）。説明の行そのものは変えない。

変更前（この1行の前に足す）:
```
-- invoice-create-portfolio 便A: 関税の決まり（行き先の国・送料の会社ごと。DDP のときに使う）
```

足す中身:
````
-- invoice-create-portfolio 便V: 振込先は版で持つ。詳細は書き足すだけ・振込先の行は消さない・表を空にしない（ADR-1079）
CREATE OR REPLACE FUNCTION {schema}.trg_payment_detail_immutable()
RETURNS TRIGGER AS $pv_detail$
DECLARE
    v_id INTEGER;
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'payment detail rows are immutable (versioned). Add a new version instead.';
    END IF;
    IF NEW.payment_method_id IS NOT NULL THEN
        EXECUTE 'SELECT id, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.payment_method_id || ' FOR SHARE'
            INTO v_id, v_superseded, v_deleted;
        IF v_id IS NULL OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'payment detail can be added only to the current version of a payment method';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_detail$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION {schema}.trg_payment_method_version_guard()
RETURNS TRIGGER AS $pv_method$
DECLARE
    v_id INTEGER;
    v_region VARCHAR(20);
    v_type VARCHAR(10);
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'payment methods cannot be deleted. Set deleted_at instead.';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.superseded_by_id IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a new payment method must start as the current version';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.region IS DISTINCT FROM OLD.region
        OR NEW.method_type IS DISTINCT FROM OLD.method_type
        OR NEW.display_name IS DISTINCT FROM OLD.display_name
        OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'payment method versions are immutable. Add a new version instead.';
    END IF;
    IF OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id THEN
        RAISE EXCEPTION 'superseded_by_id can be set only once';
    END IF;
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
        RAISE EXCEPTION 'deleted_at can be set only once';
    END IF;
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL
        AND (OLD.superseded_by_id IS NOT NULL OR NEW.superseded_by_id IS NOT NULL) THEN
        RAISE EXCEPTION 'only the current version can be deleted';
    END IF;
    IF OLD.superseded_by_id IS NULL AND NEW.superseded_by_id IS NOT NULL THEN
        IF OLD.deleted_at IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a deleted payment method cannot be superseded';
        END IF;
        IF NEW.superseded_by_id <= OLD.id THEN
            RAISE EXCEPTION 'the next version must be newer than the current version';
        END IF;
        EXECUTE 'SELECT id, region, method_type, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.superseded_by_id || ' FOR SHARE'
            INTO v_id, v_region, v_type, v_superseded, v_deleted;
        IF v_id IS NULL OR v_region IS DISTINCT FROM OLD.region OR v_type IS DISTINCT FROM OLD.method_type
            OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'the next version must be a current version of the same region and type';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_method$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION {schema}.trg_payment_version_no_wipe()
RETURNS TRIGGER AS $pv_wipe$
BEGIN
    RAISE EXCEPTION 'payment version tables cannot be truncated';
    RETURN NULL;
END;
$pv_wipe$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_version_guard' AND tgrelid = '{schema}.tenant_invoice_payment_methods'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_methods_version_guard BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_methods FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_method_version_guard();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_immutable' AND tgrelid = '{schema}.tenant_invoice_payment_bank'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_bank_immutable BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_bank FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_detail_immutable();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_immutable' AND tgrelid = '{schema}.tenant_invoice_payment_wise'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_wise_immutable BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_wise FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_detail_immutable();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_methods'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_methods_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_methods FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_bank'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_bank_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_bank FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_wise'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_wise_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_wise FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
END $$;

````

注意: この文は Python の文字列（`_TENANT_TABLES_SQL`）の中に入る。`{schema}` はそのまま書く（中括弧を二重にしない。関数の中身に中括弧は無い）。`$pv_detail$` などの印も一字も変えない（§2-1 の移行と一字一句同じであることを試験が確かめる）。

### 2-3. backend/tests/test_tenant_payment_versioning_pg.py（新規。全文。Write ツールで、下の囲みの中身をそのまま書く）

````python
"""invoice-create-portfolio 便V（design.md §3-8・ADR-1079）: 振込先を版で持つ形と見張りの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に列 2 つ・決まり・索引・見張りの関数 3 つ・見張り 6 つがあり、
  関数の中身が移行ファイルと一字一句同じで、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、見張り・関数・索引・決まり・列を外してから
  移行ファイルを 2 回流した形が同じ。版の決まりが設計どおりに効く。試験の中で入れた行は最後に戻す。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_tenant_issuer_tables_pg.py と同じ形）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests import rls_bootstrap
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261115_100000_add_payment_method_versioning.sql"
# 試験・移行のどこにも無い 957 を使う（2026-11-15 に origin/main で git grep して 0 件）
_TENANT_ID = 957
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = (
    "tenant_invoice_payment_methods",
    "tenant_invoice_payment_bank",
    "tenant_invoice_payment_wise",
)
_FUNCTIONS = {
    "trg_payment_detail_immutable": "pv_detail",
    "trg_payment_method_version_guard": "pv_method",
    "trg_payment_version_no_wipe": "pv_wipe",
}
_TRIGGERS = (
    ("trg_tenant_invoice_payment_methods_version_guard", "tenant_invoice_payment_methods"),
    ("trg_tenant_invoice_payment_bank_immutable", "tenant_invoice_payment_bank"),
    ("trg_tenant_invoice_payment_wise_immutable", "tenant_invoice_payment_wise"),
    ("trg_tenant_invoice_payment_methods_no_wipe", "tenant_invoice_payment_methods"),
    ("trg_tenant_invoice_payment_bank_no_wipe", "tenant_invoice_payment_bank"),
    ("trg_tenant_invoice_payment_wise_no_wipe", "tenant_invoice_payment_wise"),
)


def _migration_text() -> str:
    return (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")


def _body(sql: str, tag: str) -> str:
    """$tag$ と $tag$ の間（関数の中身）を返す。ちょうど 1 か所であること。"""
    found = re.findall(rf"\${tag}\$(.*?)\${tag}\$", sql, flags=re.S)
    assert len(found) == 1, tag
    return found[0]


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def test_tenant_ddl_has_versioning():
    sql = tenant_service._TENANT_TABLES_SQL
    marker = "CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods ("
    assert sql.count(marker) == 1
    methods = sql.split(marker)[1]
    methods = methods[: methods.index("\n);")]
    assert "    superseded_by_id INTEGER,\n    deleted_at TIMESTAMPTZ,\n" in methods
    assert "CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id)," in methods
    assert (
        "CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id)"
        " REFERENCES {schema}.tenant_invoice_payment_methods (id)"
    ) in methods
    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by"
        " ON {schema}.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL;"
    ) in sql
    for name, tag in _FUNCTIONS.items():
        assert f"CREATE OR REPLACE FUNCTION {{schema}}.{name}()\nRETURNS TRIGGER AS ${tag}$" in sql
    for trigger, table in _TRIGGERS:
        assert f"tgname = '{trigger}' AND tgrelid = '{{schema}}.{table}'::regclass" in sql
        assert f"CREATE TRIGGER {trigger} " in sql


def test_function_bodies_are_the_same_in_ddl_and_migration():
    """関数の中身の正本は 1 つ。新テナント用 DDL と移行ファイルで一字一句同じ。"""
    ddl = tenant_service._TENANT_TABLES_SQL
    migration = _migration_text()
    for tag in _FUNCTIONS.values():
        assert _body(ddl, tag) == _body(migration, tag), tag


def test_migration_file_exists_and_is_registered():
    body = _migration_text()
    assert "ADD COLUMN IF NOT EXISTS superseded_by_id INTEGER" in body
    assert "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ" in body
    for name in _FUNCTIONS:
        assert f"CREATE OR REPLACE FUNCTION %I.{name}() RETURNS TRIGGER AS %L LANGUAGE plpgsql" in body
    for trigger, table in _TRIGGERS:
        assert f"CREATE TRIGGER {trigger} " in body
        assert f"ON %I.{table} " in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1
    # 振込先の表を作る移行より後に流す（ファイル名の日付は書かない。分類表の照合に数えられないように）
    issuer = [i for i, line in enumerate(lines) if line.endswith("_create_tenant_issuer_and_payment_tables.sql")]
    assert len(issuer) == 1
    assert lines.index(f"run_sql migrations/{_MIGRATION}") > issuer[0]
    assert rls_bootstrap._TENANT_LOOP_MIGRATIONS[_MIGRATION] == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT INTO / UPDATE 表 / DELETE FROM を含まない）。"""
    code = "\n".join(
        line for line in _migration_text().splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT INTO", "UPDATE %I", "UPDATE PUBLIC.", "DELETE FROM"):
        assert word not in code


def test_migration_is_scoped_to_own_tenant():
    sql = _migration_text()
    scoped = rls_bootstrap._scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default"
            " FROM information_schema.columns WHERE table_schema = :s AND table_name = ANY(:t)"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) ORDER BY c.relname, con.conname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    indexes = await conn.execute(
        text(
            "SELECT tablename, indexname, indexdef FROM pg_indexes"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, indexname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    triggers = await conn.execute(
        text(
            "SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid), t.tgenabled"
            " FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) AND NOT t.tgisinternal"
            " ORDER BY c.relname, t.tgname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    functions = await conn.execute(
        text(
            "SELECT p.proname, pg_get_functiondef(p.oid) FROM pg_proc p"
            " JOIN pg_namespace n ON n.oid = p.pronamespace"
            " WHERE n.nspname = :s AND p.proname = ANY(:f) ORDER BY p.proname"
        ),
        {"s": _SCHEMA, "f": list(_FUNCTIONS)},
    )
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "indexes": [tuple(row) for row in indexes.all()],
        "triggers": [tuple(row) for row in triggers.all()],
        "functions": [tuple(row) for row in functions.all()],
    }


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, sql


async def _check_rules(conn) -> None:
    """版の決まりが効くことを確かめる。呼び出し側の取引は最後に戻す（行を残さない）。"""
    methods = f"{_SCHEMA}.tenant_invoice_payment_methods"
    new_method = f"INSERT INTO {methods} (region, method_type, display_name) VALUES (:r, :t, :n) RETURNING id"
    bank_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_bank"
        " (payment_method_id, account_holder, bank_name, bank_branch, bank_account_type, bank_account_number)"
        " VALUES (:id, 'シケン', '試験銀行', '本店', '普通', '1234567')"
    )
    wise_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_wise (payment_method_id, account_holder, wise_currency, wise_email)"
        " VALUES (:id, 'Test', 'USD', 'pay@example.com')"
    )

    async def add(region: str, kind: str, name: str) -> int:
        return (await conn.execute(text(new_method), {"r": region, "t": kind, "n": name})).scalar_one()

    v1 = await add("domestic", "bank", "銀行1")
    await conn.execute(text(bank_sql), {"id": v1})  # 今の版に詳細は書き足せる
    w1 = await add("overseas", "wise", "Wise1")
    await conn.execute(text(wise_sql), {"id": w1})

    # 詳細は書き換えも消しもできない
    await _expect_error(conn, f"UPDATE {_SCHEMA}.tenant_invoice_payment_bank SET bank_branch = '支店' WHERE payment_method_id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {_SCHEMA}.tenant_invoice_payment_wise SET wise_email = 'x@example.com' WHERE payment_method_id = :id", {"id": w1}, "P0001")
    await _expect_error(conn, f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_wise WHERE payment_method_id = :id", {"id": w1}, "P0001")
    # 振込先の行は消せない・版の中身は書き換えられない
    await _expect_error(conn, f"DELETE FROM {methods} WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET display_name = '別名' WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET region = 'overseas' WHERE id = :id", {"id": v1}, "P0001")
    for column, value in (("id", "999999"), ("tenant_id", "1"), ("method_type", "'wise'"), ("created_at", "now() - interval '1 day'")):
        await _expect_error(conn, f"UPDATE {methods} SET {column} = {value} WHERE id = :id", {"id": v1}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = id WHERE id = :id", {"id": v1}, "P0001")  # 自分は指せない
    # 並び順・使う/使わない・更新者・更新時刻は版を変えずに直せる
    await conn.execute(
        text(f"UPDATE {methods} SET sort_order = 5, is_active = FALSE, updated_by_user_id = 1, updated_at = now() WHERE id = :id"),
        {"id": v1},
    )
    flags = await conn.execute(text(f"SELECT sort_order, is_active FROM {methods} WHERE id = :id"), {"id": v1})
    assert tuple(flags.one()) == (5, False)
    # 新しい振込先は今の版として始まる
    await _expect_error(
        conn,
        f"INSERT INTO {methods} (region, method_type, display_name, deleted_at) VALUES ('domestic', 'bank', 'x', now())",
        {},
        "P0001",
    )

    # 直す: 新しい版を足して、前の版から次の版を指す
    v2 = await add("domestic", "bank", "銀行1（直し）")
    # 次の版を指すのと消すのを1回で同時にはできない
    await _expect_error(
        conn, f"UPDATE {methods} SET superseded_by_id = :n, deleted_at = now() WHERE id = :o", {"n": v2, "o": v1}, "P0001"
    )
    await conn.execute(text(f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o"), {"n": v2, "o": v1})
    await _expect_error(conn, bank_sql, {"id": v1}, "P0001")  # 前の版には詳細を足せない
    await conn.execute(text(bank_sql), {"id": v2})
    v3 = await add("domestic", "bank", "銀行1（再直し）")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v3, "o": v1}, "P0001")  # 次の版は1回だけ
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v1, "o": v2}, "P0001")  # 古い版は指せない
    w2 = await add("overseas", "wise", "Wise2")  # v2 より新しい・今の版・区分と種類が違う
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": w2, "o": v2}, "P0001")  # 区分と種類が違う
    a = await add("domestic", "bank", "A")
    b = await add("domestic", "bank", "B")
    c = await add("domestic", "bank", "C")
    d = await add("domestic", "bank", "D")  # b より新しい・後で消す
    await conn.execute(text(f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o"), {"n": c, "o": a})
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": c, "o": b}, "23505")  # 次の版を指せるのは1つだけ
    await _expect_error(conn, f"UPDATE {methods} SET deleted_at = now() WHERE id = :id", {"id": a}, "P0001")  # 前の版は消せない

    # 消す: 今の版に消した時刻を付ける（行は残る）
    await conn.execute(text(f"UPDATE {methods} SET deleted_at = now() WHERE id = :id"), {"id": v2})
    await _expect_error(conn, f"UPDATE {methods} SET deleted_at = now() - interval '1 day' WHERE id = :id", {"id": v2}, "P0001")
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": v3, "o": v2}, "P0001")
    await _expect_error(conn, bank_sql, {"id": v2}, "P0001")  # 消した版には詳細を足せない
    await conn.execute(text(f"UPDATE {methods} SET deleted_at = now() WHERE id = :id"), {"id": d})
    await _expect_error(conn, f"UPDATE {methods} SET superseded_by_id = :n WHERE id = :o", {"n": d, "o": b}, "P0001")  # 消した版は次の版にならない

    kept = await conn.execute(text(f"SELECT count(*) FROM {methods} WHERE id = ANY(:ids)"), {"ids": [v1, v2]})
    assert kept.scalar_one() == 2  # 前の版も消した版も残る
    details = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = ANY(:ids)"), {"ids": [v1, v2]}
    )
    assert details.scalar_one() == 2

    # 見張りは呼び出し側の検索先（search_path）に頼らない
    await conn.execute(text("SET LOCAL search_path TO public"))
    v4 = await add("domestic", "bank", "銀行4")
    await conn.execute(text(bank_sql), {"id": v4})  # 今の版には足せる（表が見つからない 42P01 にならない）
    await _expect_error(conn, bank_sql, {"id": v1}, "P0001")  # 前の版には足せない

    # 表を空にできない（振込先の一覧は詳細から参照されるので CASCADE 付きで試す）
    await _expect_error(conn, f"TRUNCATE {methods} CASCADE", {}, "P0001")
    await _expect_error(conn, f"TRUNCATE {_SCHEMA}.tenant_invoice_payment_bank", {}, "P0001")
    await _expect_error(conn, f"TRUNCATE {_SCHEMA}.tenant_invoice_payment_wise", {}, "P0001")


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_shape_equals_migration_and_versioning_holds():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                async with admin_engine.connect() as conn:
                    before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
                assert len(before["triggers"]) == 6
                assert len(before["functions"]) == 3
                # 便Vで足したものを外してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for trigger, table in _TRIGGERS:
                        await conn.execute(text(f"DROP TRIGGER {trigger} ON {_SCHEMA}.{table}"))
                    for name in _FUNCTIONS:
                        await conn.execute(text(f"DROP FUNCTION {_SCHEMA}.{name}()"))
                    await conn.execute(text(f"DROP INDEX {_SCHEMA}.uq_tenant_invoice_payment_methods_superseded_by"))
                    for constraint in (
                        "fk_tenant_invoice_payment_methods_superseded_by",
                        "chk_tenant_invoice_payment_methods_superseded_not_self",
                    ):
                        await conn.execute(
                            text(f"ALTER TABLE {_SCHEMA}.tenant_invoice_payment_methods DROP CONSTRAINT {constraint}")
                        )
                    for column in ("deleted_at", "superseded_by_id"):
                        await conn.execute(text(f"ALTER TABLE {_SCHEMA}.tenant_invoice_payment_methods DROP COLUMN {column}"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                async with admin_engine.connect() as conn:
                    after = await _shape(conn)
                assert before == after

                conn = await admin_engine.connect()
                try:
                    trans = await conn.begin()
                    try:
                        await _check_rules(conn)
                    finally:
                        await trans.rollback()
                finally:
                    await conn.close()
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()
````

### 2-4. backend/tests/test_tenant_issuer_tables_pg.py（5か所）

(1) 説明の行（:5）

変更前:
```
  決まり（CHECK・一意・外部キー・消したときの連鎖）が設計どおりに効く。試験の中で入れた行は最後に戻す。
```

変更後:
```
  決まり（CHECK・一意・外部キー）が設計どおりに効き、振込先の行は消せない（便V・ADR-1079）。試験の中で入れた行は最後に戻す。
```

(2) 移行の名前の後ろ（:30 の後ろに足す）

変更前:
```
_MIGRATION = "20261112_160000_create_tenant_issuer_and_payment_tables.sql"
```

変更後:
```
_MIGRATION = "20261112_160000_create_tenant_issuer_and_payment_tables.sql"
# 便V（ADR-1079）: 振込先の一覧に足した列・決まり・見張り。表を作り直したあとに一緒に流す
_VERSIONING_MIGRATION = "20261115_100000_add_payment_method_versioning.sql"
_VERSIONING_FUNCTIONS = (
    "trg_payment_detail_immutable",
    "trg_payment_method_version_guard",
    "trg_payment_version_no_wipe",
)
```

(3) 形の比べ _shape の返し（:147-152）

変更前:
```
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
    }
```

変更後:
```
    # 便V（ADR-1079）: 索引・見張り・見張りの関数の中身も比べる（K25）
    indexes = await conn.execute(
        text(
            "SELECT tablename, indexname, indexdef FROM pg_indexes"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, indexname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    triggers = await conn.execute(
        text(
            "SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid), t.tgenabled"
            " FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) AND NOT t.tgisinternal"
            " ORDER BY c.relname, t.tgname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    functions = await conn.execute(
        text(
            "SELECT p.proname, pg_get_functiondef(p.oid) FROM pg_proc p"
            " JOIN pg_namespace n ON n.oid = p.pronamespace"
            " WHERE n.nspname = :s AND p.proname = ANY(:f) ORDER BY p.proname"
        ),
        {"s": _SCHEMA, "f": list(_VERSIONING_FUNCTIONS)},
    )
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
        "indexes": [tuple(row) for row in indexes.all()],
        "triggers": [tuple(row) for row in triggers.all()],
        "functions": [tuple(row) for row in functions.all()],
    }
```

(4) 消したときの確かめ（:248-252）

変更前:
```
    await conn.execute(text(f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_methods WHERE id = :id"), {"id": bank_id})
    left = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id"), {"id": bank_id}
    )
    assert left.scalar_one() == 0  # 振込先を消すと詳細も消える
```

変更後:
```
    # 便V（ADR-1079）: 振込先の行は消せない（消すときは deleted_at を付ける）。詳細も残る
    await _expect_error(conn, f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_methods WHERE id = :id", {"id": bank_id}, "P0001")
    left = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id"), {"id": bank_id}
    )
    assert left.scalar_one() == 1
```

(5) 表を作り直す PG 試験（:276-278）

変更前:
```
                    await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN issuer_region"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
```

変更後:
```
                    await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN issuer_region"))
                    # 表と一緒に見張りは消えた。残った見張りの関数も外す（便V）
                    for name in _VERSIONING_FUNCTIONS:
                        await conn.execute(text(f"DROP FUNCTION {_SCHEMA}.{name}()"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                    await _apply_migration_on_conn(conn, _VERSIONING_MIGRATION, schema_name=_SCHEMA)  # 便V 1 回目
                    await _apply_migration_on_conn(conn, _VERSIONING_MIGRATION, schema_name=_SCHEMA)  # 便V 2 回目（冪等）
```

### 2-5. backend/tests/rls_bootstrap.py（:191 の行の後ろに1行足す）

変更前:
```
    "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql": 1,
}
```

変更後:
```
    "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql": 1,
    "20261115_100000_add_payment_method_versioning.sql": 1,
}
```

### 2-6. backend/tests/test_tenant_loop_migration_guard.py（3か所）

(1) rls_bootstrap.py の組（:53 の行の後ろに1行足す）

変更前:
```
                "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql",
            }
        ),
    ),
    "test_calendar_sync_tenant_reset_pg.py": (
```

変更後:
```
                "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql",
                "20261115_100000_add_payment_method_versioning.sql",
            }
        ),
    ),
    "test_calendar_sync_tenant_reset_pg.py": (
```

(2) 既存の試験 test_tenant_issuer_tables_pg.py の組（:111-115）

変更前:
```
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset({"20261112_160000_create_tenant_issuer_and_payment_tables.sql"}),
    ),
```

変更後:
```
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset(
            {
                "20261112_160000_create_tenant_issuer_and_payment_tables.sql",
                "20261115_100000_add_payment_method_versioning.sql",
            }
        ),
    ),
```

(3) 新しい試験の組（test_tenant_duty_rules_pg.py の組 :116-120 の後ろに足す）

変更前:
```
    "test_tenant_duty_rules_pg.py": (
        "scoped",
        "",
        frozenset({"20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"}),
    ),
```

変更後:
```
    "test_tenant_duty_rules_pg.py": (
        "scoped",
        "",
        frozenset({"20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"}),
    ),
    "test_tenant_payment_versioning_pg.py": (
        "scoped",
        "",
        frozenset({"20261115_100000_add_payment_method_versioning.sql"}),
    ),
```

### 2-7. scripts/run_all_migrations.sh（最後の行 :1277 の後ろに2行足す）

変更前（最後の行）:
```
# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_200001_add_ops_case_report_kind_down.sql
```

変更後:
```
# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_200001_add_ops_case_report_kind_down.sql
# invoice-create-portfolio 便V: 振込先を版で持つ（列2つ・見張りの関数3つ・見張り6つ。全テナント・冪等・ADR-1079）
run_sql migrations/20261115_100000_add_payment_method_versioning.sql
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/invoice-create-portfolio-bin-v-impl && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 2行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P9 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/invoice-create-portfolio/card-V.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && grep -c -E "superseded_by|trg_payment|pv_detail|_no_wipe|payment_versioning" backend/app/services/tenant.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py scripts/run_all_migrations.sh backend/tests/test_tenant_issuer_tables_pg.py | tail -5
    cd ~/sa && grep -c "957" backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py | tail -2
    cd ~/sa && grep -c -F "    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type)," backend/app/services/tenant.py
    cd ~/sa && grep -c -F "    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '')" backend/app/services/tenant.py
    cd ~/sa && grep -c -F "-- invoice-create-portfolio 便A: 関税の決まり（行き先の国・送料の会社ごと。DDP のときに使う）" backend/app/services/tenant.py
    cd ~/sa && wc -l < backend/app/services/tenant.py
    cd ~/sa && wc -l < scripts/run_all_migrations.sh
    cd ~/sa && wc -l < backend/tests/test_tenant_issuer_tables_pg.py
    cd ~/sa && tail -1 scripts/run_all_migrations.sh
    cd ~/sa && grep -c "振込先を消すと詳細も消える" backend/tests/test_tenant_issuer_tables_pg.py
    cd ~/sa && ls migrations/20261115_100000_add_payment_method_versioning.sql backend/tests/test_tenant_payment_versioning_pg.py 2>&1 | tail -2
  期待: 3行目 `20261113_200001_add_ops_case_report_kind_down.sql`。4行目は5ファイルとも `:0`。5行目は2ファイルとも `:0`。6〜8行目はどれも 1。9行目 2091。10行目 1277。11行目 306。12行目 `# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_200001_add_ops_case_report_kind_down.sql`。13行目 1。14行目は2つとも「No such file or directory」。

手順3 §2 の変更をする（2-1 から 2-7 の順。新規の2ファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    cd ~ && python3.12 --version 2>&1 | tail -1
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    cd ~ && ~/venv312/bin/ruff --version | tail -1
  手順4 の python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）。
    cd ~ && uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形と数
    cd ~/sa && ~/venv312/bin/ruff check backend/app/services/tenant.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/test_tenant_issuer_tables_pg.py backend/tests/test_tenant_payment_versioning_pg.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/python -c "import ast; ast.parse(open('backend/app/services/tenant.py').read()); print('tenant.py ok')" 2>&1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py repo > ~/vw-repo.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-repo.txt
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^-"
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^+"
    cd ~/sa && wc -l < backend/app/services/tenant.py
    cd ~/sa && git diff -U0 backend/tests/test_tenant_issuer_tables_pg.py | grep -c "^-"
    cd ~/sa && git diff -U0 backend/tests/test_tenant_issuer_tables_pg.py | grep -c "^+"
    cd ~/sa && grep -c "CREATE TRIGGER trg_tenant_invoice_payment" backend/app/services/tenant.py migrations/20261115_100000_add_payment_method_versioning.sql | tail -2
    cd ~/sa && wc -l < migrations/20261115_100000_add_payment_method_versioning.sql
    cd ~/sa && wc -l < backend/tests/test_tenant_payment_versioning_pg.py
    cd ~/sa && wc -l < scripts/run_all_migrations.sh
    cd ~/sa && grep -c "run_sql migrations/20261115_100000_add_payment_method_versioning.sql" scripts/run_all_migrations.sh
  期待（上から順に）: ruff は `All checks passed!`／`tenant.py ok`／値の書き込みの検査は `exit=0`／2（消した行1つと見出しの `--- a/` の1行）／117（足した行 116 と `+++ b/` の1行）／2206／4（直した行3つと `--- a/` の1行）／46（足した・直した行 45 と `+++ b/` の1行）／2ファイルとも `:6`／149／349／1279／1。
  repo の検査が exit=0 でなかったら、最後の 10 行を貼って `BLOCKED: value-writes`。

手順6 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_tenant_payment_versioning_pg.py tests/test_tenant_issuer_tables_pg.py tests/test_tenant_loop_migration_guard.py 2>&1 | tail -15
  期待: failed 0・error 0 で、passed に test_tenant_payment_versioning_pg.py の単体5件を含む（PG の試験は skipped でよい）。

手順7 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20
  期待: §1 の 7 ファイルだけ（新規の2ファイルは `??` で各1行）。

手順8 記録と送り出し
    cd ~/sa && git add migrations/20261115_100000_add_payment_method_versioning.sql backend/app/services/tenant.py backend/tests/test_tenant_issuer_tables_pg.py backend/tests/test_tenant_payment_versioning_pg.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py scripts/run_all_migrations.sh && git status --short | tail -20
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(tenant): version invoice payment methods with guard triggers per tenant (invoice-create-portfolio bin V)" && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all > ~/vw-diff.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-diff.txt
    cd ~/sa && git push origin release/invoice-create-portfolio-bin-v-impl 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/invoice-create-portfolio-bin-v-impl -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。3行目の diff 検査が exit=0 でなかったら push せずに最後の 10 行を貼って `BLOCKED: value-writes`。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P9 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 値の書き込みの検査（手順5・手順8）が失敗した → 最後の 10 行を貼って `BLOCKED: value-writes`。移行の文を直さない。
  - 手順5 の数の期待が外れた → 出力を貼って `BLOCKED: 手順5`。
  - 手順6 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - ruff が E501（行が長い）だけを出した → 直さずにそのまま書く（判定は Opus がする）。
  - 手順6 で skipped が出る → そのまま書く（実 PostgreSQL の試験は CI で動く）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED invoice-create-portfolio-V HEAD=…`。2 行目: 「本報告はカード 便V 振込先を版で持つ の実行結果である」。
- 手順1・2・4・5・6・7・8 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の2ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
