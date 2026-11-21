# 実装カード 便1: Meta 審査用の会社だけのスイッチ（裏側・移行・試験）

> この文書は何か（専門用語なしの1行）:
> 会社006だけで使える「ログインの機械の確かめを一時的に外すスイッチ」の、データの置き場・判定・管理の口・試験を作る作業の指示書（画面は便2）。

- 親: [review-exempt-design.md](review-exempt-design.md) の 3-1〜3-7・3-9・3-11・§8（以下「設計 3-x」）。ADR-1055 What 11
- 承認: 設計審査3回目 APPROVE（[review-exempt-review-opus.md](review-exempt-review-opus.md)）・PO 承認 2026-11-22「1」（この形で作り始める）
- 基準: origin/main `2560f963f`（2026-11-22 Opus 取得）。下の行番号はすべてこの版で Opus が読んで確かめた
- ブランチ: `release/meta-review-switch-bin1`（`bash scripts/new-worktree.sh release/meta-review-switch-bin1 --claude` で作る。clone のまま commit しない）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md（コマンドは作業台のフルパスへの cd で始める・1手順1コマンド・出力に head を付ける）・07-migration.md（`run_all_migrations.sh` に登録・採番は直近を実測）・10-executor.md（プレースホルダを残さない）。照合: このカードに未確定の値は §0 の確かめ以外に無い
- 受領確認: 着手の前に §0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う（担当は push まで）。Draft・`--base main`・`shingo-cc` 名義。**危険 PR**（`migrations/`・`scripts/run_all_migrations.sh` を含む。ADR-135・ADR-136）。マージ・本番反映・本番のデータの変更は担当が行わない
- 返事の形: 最後の行を `DONE`・`BLOCKED:` の後に理由・`NEEDS_DECISION:` の後に問い、のどれかにする。迷ったら推測で進めず NEEDS_DECISION:
- 停止の報告: 途中で止まるときは、その時点までの commit を push してから、止まった手順の番号・実行したコマンド・出力の最後の20行を返事に書いて停止する（push できないときは差分を `/tmp/CC報告ファイル/meta-review-bin1/stop-diff.txt` に保存して場所を書く）

## 0. 着手条件（1つでも違えば BLOCKED: で差を返す）

表の各行について、例えば1行目なら `git show origin/main:backend/app/routers/auth.py | sed -n '438p'` のように、ファイルと行を入れて確かめる。

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `backend/app/routers/auth.py:438` | `elif user_row.last_login is None and await devices.count_all_devices(db, user_row.id) == 0:` |
| `backend/app/routers/auth.py:552` | `elif devices.is_enforced():` |
| `backend/app/routers/auth.py:556` | `if cutoff is not None and rotated.family_created_at is not None and rotated.family_created_at < cutoff:` |
| `backend/app/routers/auth.py:939` | `@router.get("/passkey/prompt", response_model=PasskeyPromptStatus)` |
| `backend/app/routers/auth.py:978` | `@router.post("/passkey/register/options", response_model=PasskeyChallengeResponse)` |
| `backend/app/routers/auth.py:1007` | `@router.post("/passkey/register/verify", response_model=PasskeyCreated, status_code=201)` |
| `backend/app/routers/auth.py:1884` | `@router.post("/recovery-codes", response_model=RecoveryCodesCreated)` |
| `backend/app/routers/auth.py:282` | `async def _record_auth_audit(` |
| `backend/app/routers/tenant_login_requests.py:68` | `@router.post("/tenant/login-requests/{request_id}/approve", response_model=AdminApproveResult)` |
| `scripts/run_all_migrations.sh:1489` | `mr_report_summary` |
| `backend/tests/conftest.py:1770` | `CREATE TABLE IF NOT EXISTS tenants (` |
| `backend/tests/test_users_rls.py:57` | `_MUST_CHANGE_MIGRATION = "20261107_130000_add_users_password_must_change.sql"` |

- `git ls-tree --name-only origin/main migrations/ | tail -1` が `migrations/20261121_100000_add_invoice_payment_fee_charged.sql`。後ろに新しいファイルがあれば、§4 のファイル名の時刻をそれより後にして進めてよい（その旨を返事に書く）
- 行がずれていても中身が同じなら、ずれた行で進めてよい（ずれを返事に書く）。中身が違えば BLOCKED:

## 1. やること（この順）

1. クラウドの事前確認: `git config user.name shingo-cc` と `git rev-parse --verify origin/main`。失敗したら BLOCKED:（gh の確認と PR の起票は Opus が手元で行う）
2. §2 の判定の部品を作る
3. §3 のログインと更新を直す
4. §4 の4つの口を直す
5. §5 の管理の口を作る
6. §6 の移行を作り、登録する
7. §7 の試験を作る
8. API の形の写しを作り直す: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（新しい口3つの分だけ差が出る。ほかの差が出たら NEEDS_DECISION:）
9. 試験は手元で回さない。push して GitHub の CI で確かめる
10. PR 本文の材料（`git diff origin/main...HEAD --name-only` の全一覧・migration の一覧 1本・`### 標準ワークフロー確認` の下書き）を `/tmp/CC報告ファイル/meta-review-bin1/pr-body.md` に書いて返す

## 2. 判定の部品（新規 `backend/app/auth/meta_review.py`）

設計 3-2 のコードをそのまま書く（`META_REVIEW_MAX_DAYS = 14`・`is_meta_review_on`・`meta_review_until`・`is_meta_review_member`）。加えて設計 3-5 の `is_meta_review_session(db, request, user) -> bool` を同じファイルに書く（中の順は設計 3-5 の 1〜4 のとおり）。

- 読み込むのは `app.auth.devices`・`app.auth.self_tokens`・`app.auth.dependencies`（`resolve_current_session`）だけ。`devices` と `dependencies` からこのファイルを読み込まない（循環を作らない）
- 「印の会社・super admin でない」の条件は、このファイルの2つの SQL にだけ書く。ほかのファイルに `meta_review_tenant` の条件を書かない（§5 の管理の口の UPDATE の `WHERE meta_review_tenant` だけは例外。設計 3-7）
- ファイルの頭の説明に「ADR-1055 What 11。Meta の審査員が登録していない機械から入るための会社006だけの例外。ほかの会社に広げない」と書く

## 3. ログインと更新（`backend/app/routers/auth.py`）

| 場所 | 変更 |
|---|---|
| 頭の import | `from app.auth import meta_review` を既存の `from app.auth import ...` の並びに足す |
| `:438` の `elif`（D5）の前 | 設計 3-3 のコードの `elif` を足す（記録の名前 `meta_review`・知らせメール。`send_new_device_mail` の引数の名前は今の呼び出しと同じものを使う。`note=` の引数が今の関数に無ければ足さずに NEEDS_DECISION:） |
| `:438` の D5 の条件 | 末尾に `and not await meta_review.is_meta_review_member(db, user_row.id)` を足す |
| `:552-570` | 設計 3-4 の形にする。`cutoff = ...` の後に `if meta_review.is_meta_review_on(await meta_review.meta_review_until(db, user_id)): audit_reason = "meta_review_refresh"` を置き、今の `if cutoff ...` を `elif` に、今の `else` はそのまま。bootstrap と 401 の中身は1字も変えない |

- 印の会社でない人の動きは1つも変えない（既存の `backend/tests/test_new_device_approval.py` が全部緑のままであること）

## 4. 4つの口で「スイッチで入った組」を断る

| 場所 | 変更 |
|---|---|
| `backend/app/routers/auth.py:939` の `passkey_prompt_status` | 最初の `if not _is_fresh_password_login(...)` の前に `if await meta_review.is_meta_review_session(db, request, current_user): return PasskeyPromptStatus(can_auto=False, show_prompt=False)` |
| `:978` `passkey_register_options`・`:1007` `passkey_register_verify` | `_require_app_origin(request)` の直後に `if await meta_review.is_meta_review_session(db, request, current_user): raise HTTPException(status_code=403, detail="meta_review_session_no_enroll")` |
| `:1884` `recovery_codes_create` | 同じ1行を関数の最初（origin の確かめがあればその直後） |
| `backend/app/routers/tenant_login_requests.py:68` `approve_tenant_login_request` | `require_app_origin(request)` の直後に同じ1行 |

- `verify` の関数が `db` または `current_user` を受けていなければ、引数に `Depends` で足す（ほかの引数は変えない）。足せない形なら NEEDS_DECISION:

## 5. 管理の口（新規 `backend/app/routers/super_admin_meta_review.py`）

設計 3-7 の表の3つの口と、書き込みの順 1〜5（2.5 を含む）をそのまま作る。

- 守りは `backend/app/routers/super_admin_login_requests.py:107-116` と同じ（`Depends(require_super_admin)`・書く口は `require_app_origin(request)`）
- `backend/app/main.py:117` の import の並びに `super_admin_meta_review,  # ADR-1055 What 11: Meta 審査用のスイッチ` を足し、`:263` の次の行に `app.include_router(super_admin_meta_review.router, prefix="/api/v1", tags=["super-admin"])`
- GET の `until` は保存された値をそのまま ISO 文字で返す（過ぎていても NULL に直さない）。`is_on` は `meta_review.is_meta_review_on(until)`
- PUT の本文は `{on: bool}` だけ。印（`meta_review_tenant`）を書く道は作らない
- 履歴の口は設計 3-9 の SQL をそのまま使い、`limit` は 1〜200（既定 100）。返す行は `{created_at, email, path, status_code, reason, device}`。`device` は `devices.describe_user_agent(user_agent)`（`backend/app/auth/devices.py:135`）
- 監査は `_record_auth_audit`（`backend/app/routers/auth.py:282`）を読み込んで使う。前例 `backend/app/routers/super_admin_login_requests.py:134-143`（別の会社の id と super admin の user_id で書く形。`audit_logs.user_id` に外部キーは無い `backend/app/services/tenant.py:481-491`）

## 6. 移行（新規 `migrations/20261122_100000_add_tenants_meta_review_switch.sql`）

設計 3-11 のとおり。中身:

```sql
-- ADR-1055 What 11: Meta 審査用の会社（会社006）だけのログインのスイッチ。ほかの会社に広げない。
-- 列を足すだけ。値は書かない（印は本番のデータの変更で1回だけ付ける。設計 3-10）。何度流しても同じになる。
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS meta_review_tenant BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS meta_review_login_until TIMESTAMPTZ NULL;
DO $meta_review$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'public.tenants'::regclass AND conname = 'tenants_meta_review_until_needs_marker'
  ) THEN
    ALTER TABLE public.tenants
      ADD CONSTRAINT tenants_meta_review_until_needs_marker
      CHECK (meta_review_login_until IS NULL OR meta_review_tenant);
  END IF;
END
$meta_review$;
CREATE UNIQUE INDEX IF NOT EXISTS tenants_meta_review_one_marker
  ON public.tenants ((meta_review_tenant)) WHERE meta_review_tenant;
COMMENT ON COLUMN public.tenants.meta_review_tenant IS
  'Meta 審査用の会社の印（ADR-1055 What 11）。1社だけ。ほかの会社に広げない';
COMMENT ON COLUMN public.tenants.meta_review_login_until IS
  'Meta 審査用のスイッチ。今より後なら ON（最長14日）。NULL か過去なら OFF';
-- 戻し方: ALTER TABLE public.tenants DROP CONSTRAINT IF EXISTS tenants_meta_review_until_needs_marker;
--         DROP INDEX IF EXISTS public.tenants_meta_review_one_marker;
--         ALTER TABLE public.tenants DROP COLUMN IF EXISTS meta_review_login_until, DROP COLUMN IF EXISTS meta_review_tenant;
```

- `scripts/run_all_migrations.sh` の `:1486`（`20261121_100000` の行）の後、`:1488` の注記の前に、説明の1行（`# ADR-1055 What 11: Meta 審査用の会社だけのスイッチの列`）と `run_sql migrations/20261122_100000_add_tenants_meta_review_switch.sql` を足す
- INSERT・UPDATE・DELETE を書かない（ADR-155・`scripts/check-migration-value-writes.py`）
- 相談係用の伏せたビューの分類表（`ai_cloud_meta.column_class`）には行を足さない（2列は `bool`・`timestamptz` で、`backend/tests/ops/test_ai_cloud_views.py:111-114` のそのまま出す型。名前も `:105-108` の見張りに当たらないことを Opus が確かめた）。もし CI の T10 がこの2列で落ちたら、行を足さずに NEEDS_DECISION:
- `backend/app/models.py` の Tenant には足さない。deploy.yml も変えない

## 7. 試験

### 7-1. 試験の表

- `backend/tests/conftest.py:1770` の SQLite の tenants 表に `meta_review_tenant INTEGER NOT NULL DEFAULT 0` と `meta_review_login_until TIMESTAMP` を足す
- ほかの試験ファイルが自前で tenants 表を作っていて、ログインの試験でその表を使うなら、同じ2列を足す（`git grep -n "CREATE TABLE IF NOT EXISTS tenants" origin/main -- backend/tests/ | head -20` で探し、足したファイルを返事に並べる）

### 7-2. 新規 `backend/tests/test_meta_review_switch.py`（SQLite）

`backend/tests/test_new_device_approval.py` の準備（`:79-232` の `base_env`・`enforce`・`no_redis_and_spies`・`spies`・`_insert_user`・`machine`・`_login`・`_poll`）を同じ形で使う（読み込めるものは読み込み、読み込めないものは同じ中身で書く）。会社006の代わりに、試験の中で tenants に1行作って `meta_review_tenant = 1` にする（番号 6 を書かない）。

設計 K1〜K8・K11・K12 の試験名で次の関数を作る:

| 試験 | 確かめること |
|---|---|
| `test_meta_review_on_login_gets_tokens` | ON（until＝今＋1日）の印の会社の人が、知らない機械で 200 とトークン。`auth_refresh_tokens.trusted_device_id` が NULL・`user_trusted_devices` が0行・記録の reason が `meta_review` |
| `test_meta_review_off_returns_202` | until が NULL と過去の両方で 202 |
| `test_meta_review_other_tenant_still_202` | ON の印の会社があっても、印の無い会社の人は 202 |
| `test_meta_review_not_for_super_admin_user` | 印の会社の super admin の人は ON でも 202 |
| `test_meta_review_auto_off_after_14_days` | PUT で ON → until が今＋14日（±1分）。時刻を15日後に進めると（`devices._now` を patch）ログインが 202。GET が過ぎた until をそのまま返し `is_on` が偽 |
| `test_meta_review_refresh_after_off_401` | ON で入った組の更新は 200（reason `meta_review_refresh`）。OFF の後の更新は 401 |
| `test_meta_review_session_cannot_enroll_passkey` | ON で入った組で register/options と register/verify が 403 `meta_review_session_no_enroll` |
| `test_meta_review_session_cannot_create_recovery_codes` | 同じく `/recovery-codes` が 403 |
| `test_meta_review_session_prompt_not_auto` | `/passkey/prompt` が can_auto と show_prompt の両方とも偽 |
| `test_meta_review_session_cannot_approve_tenant_request` | 印の会社のオーナーにした人の機械の無い組で、会社の許可の口が 403 |
| `test_meta_review_session_cannot_enroll_after_off` | ON で入り、OFF にした後（until を過去にする）も同じアクセストークンで register/options が 403 |
| `test_meta_review_member_no_first_login_device` | 印の会社の、一度も入っていない人（last_login NULL・機械0件）が OFF で入ると 202 で、`user_trusted_devices` が0行 |
| `test_meta_review_switch_forbidden_for_non_super_admin` | super admin でない人の GET・PUT・履歴が 403 |
| `test_meta_review_switch_missing_tenant_409` | 印の会社が無いときの PUT が 409 `meta_review_tenant_missing` |
| `test_meta_review_manual_off_revokes_deviceless_families` | ON で入った組が、PUT OFF の後に `revoked_at` が入り、`mark_family_revoked` が呼ばれる。機械の付いた組は残る |
| `test_meta_review_history_lists_attempts` | 成功・パスワード違い・202・許可されて入った回（`approved_admin`）・止められた口座（`locked`）が新しい順に出る。ほかの会社の人の行と、人の付かない行（`unknown_user`）は出ない |
| `test_meta_review_switch_audited` | PUT の ON と OFF で、印の会社の audit_logs に `table_name="tenants"`・`event` が `meta_review_on`／`meta_review_off` の行が1つずつ |

### 7-3. `backend/tests/test_users_rls.py`（PostgreSQL）

- `:57` の次に `_META_REVIEW_MIGRATION = "20261122_100000_add_tenants_meta_review_switch.sql"` を足し、`:115` の `_apply_migration(admin_engine, _MUST_CHANGE_MIGRATION)` の次の行で当てる
- `test_meta_review_check_rejects_unmarked_tenant`: 管理者の接続で、印の無い会社に until を入れる UPDATE が CHECK で失敗する
- `test_meta_review_marker_unique`: 管理者の接続で、2社目に印を付ける UPDATE が一意の索引で失敗する
- `test_meta_review_switch_updates_under_rls`: 設計 3-11 の最後の段落のとおり。試験の中で `migrations/20261016_170000_add_tenants_write_rls.sql` を管理者の接続（`admin_engine`）で当て、確かめる UPDATE はアプリの接続（`app_engine`・`_ctx_conn`、`:145`）で流す。(1) 運営の文脈なしは0行 (2) `operator=True` は1行 (3) UPDATE → 会社の文脈を付けて外す → commit で値が残る。最後に管理者の接続で `ALTER TABLE public.tenants DISABLE ROW LEVEL SECURITY` と方針の削除で元に戻す。jarvis は superuser で RLS を通り抜けるので、確かめに管理者の接続を使わない（前例 `test_no_context_cannot_write` `:221-253`）

## 8. 触らない場所

- `AUTH_DEVICE_APPROVAL`・`.github/workflows/deploy.yml`・締切・パスワードの変更の口（`backend/app/routers/auth.py:769-779`）
- 画面（`frontend/`）は便2。ただし §1 の8 の `frontend/api-contract/openapi.json` だけは作り直す
- 本番のデータ（印を付けるのは Opus が別に行う。設計 3-10）

## 9. 検索で確かめる（push の前に返事に件数を書く）

- `git grep -n "meta_review_tenant" -- backend/app/` → `backend/app/auth/meta_review.py` の2件と `backend/app/routers/super_admin_meta_review.py` の UPDATE・履歴の SQL の分だけ
- `git grep -n "meta_review_session_no_enroll" -- backend/app/` → 5件（4つの口の5か所）
- `git grep -n -E "tenant_id ?== ?6|tenant_006|'6'" -- backend/app/auth/meta_review.py backend/app/routers/super_admin_meta_review.py migrations/20261122_100000_add_tenants_meta_review_switch.sql` → 0件

END OF CARD
