# Stage W recon raw facts

origin/main base: d97928fa7bd91639b3880f882c46babff22ee548

## R1
$ ls migrations | grep 20261101
20261101_120000_enable_secretary_chat_tenant4.sql
20261101_130000_add_new_device_approval.sql
$ sed -n 6,39p migrations/20261101_130000_add_new_device_approval.sql
CREATE TABLE IF NOT EXISTS public.user_trusted_devices (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL,
    label VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    created_via VARCHAR(20) NOT NULL,
    created_ip VARCHAR(45) NULL,
    created_location VARCHAR(200) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    last_ip VARCHAR(45) NULL,
    last_location VARCHAR(200) NULL,
    revoked_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_user_trusted_devices_user_token UNIQUE (user_id, token_hash),
    CONSTRAINT ck_user_trusted_devices_created_via CHECK (
        created_via IN ('bootstrap', 'first_login', 'passkey', 'device_approval', 'recovery_code', 'admin_approval', 'cli')
    )
);
CREATE INDEX IF NOT EXISTS ix_user_trusted_devices_user_id ON public.user_trusted_devices (user_id);
COMMENT ON TABLE public.user_trusted_devices IS 'いつもの機械の印（Cookie sa_device）。ハッシュだけ保存。ADR-1055';
COMMENT ON COLUMN public.user_trusted_devices.id IS '機械の ID';
COMMENT ON COLUMN public.user_trusted_devices.user_id IS '人の正本 public.users.id。1つの印を複数の人が使える';
COMMENT ON COLUMN public.user_trusted_devices.token_hash IS '印の sha256（32 バイト）。印そのものは保存しない';
COMMENT ON COLUMN public.user_trusted_devices.label IS '機械の呼び名（管理用の命令で付ける）';
COMMENT ON COLUMN public.user_trusted_devices.user_agent IS '登録したときのブラウザ情報';
COMMENT ON COLUMN public.user_trusted_devices.created_via IS '登録の経路（bootstrap・first_login・passkey・device_approval・recovery_code・admin_approval・cli）';
COMMENT ON COLUMN public.user_trusted_devices.created_ip IS '登録したときの IP';
COMMENT ON COLUMN public.user_trusted_devices.created_location IS '登録したときの場所の目安（IP から引く）';
COMMENT ON COLUMN public.user_trusted_devices.created_at IS '登録した時刻';
COMMENT ON COLUMN public.user_trusted_devices.last_used_at IS '最後に使った時刻。180日使わないと失効扱い';
COMMENT ON COLUMN public.user_trusted_devices.last_ip IS '最後に使ったときの IP';
COMMENT ON COLUMN public.user_trusted_devices.last_location IS '最後に使ったときの場所の目安';
COMMENT ON COLUMN public.user_trusted_devices.revoked_at IS '取り消した時刻。NULL は有効';
$ sed -n 126,132p migrations/20261101_130000_add_new_device_approval.sql
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_trusted_devices, public.auth_login_requests, public.user_recovery_codes TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.user_trusted_devices_id_seq, public.user_recovery_codes_id_seq TO salesanchor_app;
    END IF;
END $$;
$ grep -n 'GRANT\|user_trusted_devices_id_seq' migrations/20261101_130000_add_new_device_approval.sql
129:        GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_trusted_devices, public.auth_login_requests, public.user_recovery_codes TO salesanchor_app;
130:        GRANT USAGE, SELECT ON SEQUENCE public.user_trusted_devices_id_seq, public.user_recovery_codes_id_seq TO salesanchor_app;

## R2
$ grep -n PUBLIC_TABLES .github/workflows/migration-guard.yml
224:          PUBLIC_TABLES="tenants users permissions products suppliers supplier_aliases inventory inventory_movements tcg_series_master pokemon_dex trainer_dex supplier_prompts meta_page_routing tenant_settings tenant_llm_budgets data_access_events data_deletion_logs auth_events tenant_discord_config tenant_discord_ticket_config knowledge_rules supplier_discord_routing user_inventory_filters ingestion_jobs link_templates quantity_units registration_tokens units unit_aliases line_units conditions condition_aliases tcg_note_master tcg_status_master tcg_product_categories product_lines product_formats product_kinds type_master condition_definitions supplier_channels source_messages import_jobs import_job_messages extraction_jobs extraction_items extraction_attempts analysis_runs analysis_results analysis_run_snapshots item_corrections tcg_normalization_rules tcg_distribution_settings tcg_distribution_targets tcg_product_import_jobs tcg_product_import_rows weight_classes audit_log buyback_shop_products buyback_price_logs product_format_game_links rule_test_cases rule_test_runs rule_test_run_results line_conditions llm_usage_events payment_fee_settings viewer_accounts viewer_login_tokens viewer_login_events viewer_status_changes ops_incidents ops_incident_events ops_control analysis_error_reports analysis_error_report_fields analysis_error_report_events accuracy_gold_versions accuracy_gold_rows user_trusted_devices auth_login_requests user_recovery_codes"
243:              if echo " $PUBLIC_TABLES " | grep -q " $ref "; then
270:            echo "  $PUBLIC_TABLES"
272:            echo "新テーブルを public に追加した場合は migration-guard.yml の PUBLIC_TABLES を更新してください"

## R3
$ sed -n 1,20p migrations/20261024_100300_create_ai_cloud_views.sql
-- ADR-1052 段1: 相談係用の伏せたビュー ai_cloud を作る（冪等・1 トランザクション）。
-- 一覧には載せない。run_all_migrations.sh の EXIT trap が、毎回の実行の最後に流す（ai_ro と同じ形）。
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1054 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
-- 2) ai_cloud を作り直す。3) ai_cloud_meta.build_views() で全ビューを作り、build_log に 1 行書く。
-- 4) ai_reader_cloud に ai_cloud の USAGE と SELECT だけを付ける。
-- 分類表の元: docs/handoff/cloud-case-ai/stage1-column-class.tsv（表ごと・class ごとにまとめて unnest で入れる）。
-- 途中でエラーや打ち切り（57014）が出ると全体が戻り、ai_cloud は外れたまま（相談係は読めない側に倒れる）。

BEGIN;

TRUNCATE ai_cloud_meta.column_class;

INSERT INTO ai_cloud_meta.column_class (schema_pattern, table_name, column_name, class, reason)
SELECT v.schema_pattern, v.table_name, col, v.class, v.reason
FROM (VALUES
  ('public','accuracy_gold_rows',ARRAY['a1_product_id','a2_condition','a3_unit','a4_basis','a4_status','a5_ship','allowed_lines','e2_price','e3_quantity','exclusion'],'mask',''),
  ('public','accuracy_gold_rows',ARRAY['gold_version'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('public','accuracy_gold_rows',ARRAY['hesitation','lines','po_check','price_line','ruling_basis'],'mask',''),
  ('public','accuracy_gold_versions',ARRAY['file_sha256'],'mask',''),
  ('public','accuracy_gold_versions',ARRAY['gold_version'],'mask','値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）'),
$ grep -n "auth_events\|user_trusted_devices" migrations/20261024_100300_create_ai_cloud_views.sql
48:  ('public','auth_events',ARRAY['client_ip'],'mask',''),
49:  ('public','auth_events',ARRAY['event_type','method'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
50:  ('public','auth_events',ARRAY['path','user_agent'],'mask',''),
51:  ('public','auth_events',ARRAY['reason'],'mask',''),
286:  ('public','user_trusted_devices',ARRAY['created_ip','created_location','created_via','label','last_ip','last_location','user_agent'],'mask',''),
$ wc -l docs/handoff/cloud-case-ai/stage1-column-class.tsv
1055 docs/handoff/cloud-case-ai/stage1-column-class.tsv
$ grep -n user_trusted_devices docs/handoff/cloud-case-ai/stage1-column-class.tsv
469:public	user_trusted_devices	created_ip	mask		character varying
470:public	user_trusted_devices	created_location	mask		character varying
471:public	user_trusted_devices	created_via	mask		character varying
472:public	user_trusted_devices	label	mask		character varying
473:public	user_trusted_devices	last_ip	mask		character varying
474:public	user_trusted_devices	last_location	mask		character varying
475:public	user_trusted_devices	user_agent	mask		character varying
$ cat -n scripts/migration-guard/reference-allowlist.tsv
     1	# migration の確認 8（共用マスタの中身の参照）の例外の一覧。唯一の正本。
     2	# scripts/check-migration-value-writes.py diff が、ここにあり sha256 が一致するファイルを確認 8 から外す（外したことは出力に出す）。
     3	# 列（タブ区切り）: file / sha256（HEAD のそのファイルの中身の sha256sum）/ reason / decision_ref
     4	# 規則: (1) 確認 7（値の書き込み）は一覧に関係なく全ファイルに効く。(2) 一覧にあっても sha256 が違えば、そのファイルは失敗（中身が変わったので例外は効かない）。
     5	#       (3) repo モードは、各行のファイルが在り・scripts/run_all_migrations.sh にパスが書かれ・sha256 が一致することを確かめる。違えば失敗（古い行を残さない）。
     6	#       (4) 1 ファイル 1 行。理由は読んで確かめたことだけを書く。
     7	migrations/20261024_100300_create_ai_cloud_views.sql	e757c7f99bafaa80a23f2f05a1a5f794bbf9cd5760f3938587169aaba02b50c8	ai_cloud.column_class の初期値として表の名前を文字の値で並べる。共用マスタの中身は読まない	PO「1」2026-10-31 / docs/handoff/cloud-case-ai/stage1-h-decision.md §3 / ADR-1055 design §4 A-1（19行追加）
$ grep -n -B3 -A3 1054 backend/tests/ops/test_ai_cloud_views.py
477-    # meta の migration も冪等（分類表の中身は消えない）
478-    n0 = _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0]
479-    c.execute(_read(_META_SQL))
480:    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1054
481-
482-
483-# ---------------------------------------------------------------- T10（CI の見張り）

## R4
$ grep -n -B5 -A5 user_trusted_devices backend/tests/conftest.py
323-            statement = statement.replace("public.password_reset_tokens", "password_reset_tokens")
324-        if "public.webauthn_credentials" in statement:
325-            statement = statement.replace("public.webauthn_credentials", "webauthn_credentials")
326-        if "public.passkey_enroll_prompt_skips" in statement:
327-            statement = statement.replace("public.passkey_enroll_prompt_skips", "passkey_enroll_prompt_skips")
328:        if "public.user_trusted_devices" in statement:
329:            statement = statement.replace("public.user_trusted_devices", "user_trusted_devices")
330-        if "public.auth_login_requests" in statement:
331-            statement = statement.replace("public.auth_login_requests", "auth_login_requests")
332-        if "public.user_recovery_codes" in statement:
333-            statement = statement.replace("public.user_recovery_codes", "user_recovery_codes")
334-        # SQLite は FOR UPDATE をサポートしない（ファイルレベルロックで代替）。
--
1360-                trusted_device_id INTEGER
1361-            )
1362-        """))
1363-        # ADR-1055 段A: 新しい機械の許可の3表の SQLite 版（BYTEA→BLOB, UUID→TEXT, BIGSERIAL→INTEGER, CHAR/VARCHAR→TEXT）
1364-        await conn.execute(text("""
1365:            CREATE TABLE IF NOT EXISTS user_trusted_devices (
1366-                id INTEGER PRIMARY KEY AUTOINCREMENT,
1367-                user_id INTEGER NOT NULL,
1368-                token_hash BLOB NOT NULL,
1369-                label TEXT,
1370-                user_agent TEXT,
$ grep -n "user_trusted_devices\|auth_login_requests" .github/workflows/migration-test.yml

## R5
$ grep -n '^async def\|^def' backend/app/auth/devices.py
56:def approval_mode() -> str:
61:def is_enforced() -> bool:
65:def bootstrap_cutoff() -> datetime | None:
78:def _now() -> datetime:
82:def hash_value(raw: str) -> bytes:
89:def clean_cookie_value(raw: str | None) -> str | None:
96:def set_device_cookie(response: Response, raw: str) -> None:
109:def set_pending_cookie(response: Response, raw: str) -> None:
122:def clear_pending_cookie(response: Response) -> None:
135:def describe_user_agent(ua: str | None) -> str:
171:def jst_text(moment: datetime | None = None) -> str:
185:async def find_trusted_device(db: AsyncSession, user_id: int, raw_cookie: str | None) -> DeviceRow | None:
204:async def has_any_trusted_device(db: AsyncSession, user_id: int) -> bool:
215:async def count_all_devices(db: AsyncSession, user_id: int) -> int:
227:async def register_device(
285:async def touch_device(db: AsyncSession, device_id: int, request: Request) -> None:
297:async def revoke_user_sessions(
324:async def revoke_family(db: AsyncSession, user_id: int, family_id: str) -> None:
336:async def revoke_device(db: AsyncSession, user_id: int, device_id: int) -> bool:
353:async def bind_family_to_device(db: AsyncSession, family_id: str, user_id: int, device_id: int) -> None:
364:async def is_device_active(db: AsyncSession, device_id: int) -> bool:
387:def _numbers() -> tuple[str, str]:
396:async def create_login_request(
446:def parse_request_id(value: str) -> str | None:
$ sed -n 185,203p backend/app/auth/devices.py
async def find_trusted_device(db: AsyncSession, user_id: int, raw_cookie: str | None) -> DeviceRow | None:
    """印がその人のいつもの機械か（取り消されていない・180日以内に使った）。"""
    raw = clean_cookie_value(raw_cookie)
    if raw is None:
        return None
    cutoff = _now() - timedelta(days=DEVICE_IDLE_DAYS)
    row = (
        await db.execute(
            text(
                "SELECT id, created_via FROM public.user_trusted_devices "
                "WHERE user_id = :uid AND token_hash = :h AND revoked_at IS NULL "
                "AND COALESCE(last_used_at, created_at) > :cutoff"
            ),
            {"uid": user_id, "h": hash_value(raw), "cutoff": cutoff},
        )
    ).first()
    return DeviceRow(int(row.id), row.created_via) if row else None



## R6
$ grep -n 'auth_login_requests' backend/app/routers/auth.py | grep -n 'INSERT'  (INSERT 行は auth.py に無し。devices.py を検索)
$ grep -n 'INSERT INTO public.auth_login_requests' backend/app/auth/devices.py
423:            "INSERT INTO public.auth_login_requests "
$ grep -n 'send_new_device_mail' backend/app/routers/auth.py
52:from app.services.auth_mail import send_invite_email, send_new_device_mail, send_password_reset_email
342:        send_new_device_mail,
419:                send_new_device_mail,
1181:                send_new_device_mail,
$ grep -n 'publish_user_change' backend/app/routers/auth.py
48:from app.realtime.publisher import publish_user_change
340:    await publish_user_change(user_id, TOPIC_AUTH_LOGIN_REQUEST)
1399:            await publish_user_change(row.user_id, TOPIC_AUTH_LOGIN_REQUEST)
1512:            await publish_user_change(user_row.id, TOPIC_AUTH_LOGIN_REQUEST)
1533:    await publish_user_change(user_row.id, TOPIC_AUTH_LOGIN_REQUEST)
1575:    await publish_user_change(session.user.id, TOPIC_AUTH_LOGIN_REQUEST)
1613:    await publish_user_change(session.user.id, TOPIC_AUTH_LOGIN_REQUEST)
$ grep -n 'create_login_request' backend/app/routers/auth.py
428:            new = await devices.create_login_request(db, user_row.id, request, cookie_raw)
$ sed -n 396,445p backend/app/auth/devices.py   # create_login_request (def から return まで)
async def create_login_request(
    db: AsyncSession,
    user_id: int,
    request: Request,
    device_raw: str | None,
) -> NewRequest:
    """許可依頼を作る。1人1時間に5件まで（超えたら 429 too_many_requests）。commit は呼び出し側。"""
    now = _now()
    recent = (
        await db.execute(
            text("SELECT count(*) FROM public.auth_login_requests WHERE user_id = :uid AND created_at > :since"),
            {"uid": user_id, "since": now - timedelta(hours=1)},
        )
    ).scalar_one()
    if int(recent) >= REQUEST_HOURLY_LIMIT:
        raise HTTPException(status_code=429, detail="too_many_requests")
    request_id = str(uuid.uuid4())
    pending_raw = secrets.token_urlsafe(32)
    match_number, candidates = _numbers()
    expires_at = now + REQUEST_TTL
    ip = get_client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:500] or None
    device_clean = clean_cookie_value(device_raw)
    label = describe_user_agent(ua)[:100]
    location = geo.lookup(ip)
    await db.execute(
        text(
            "INSERT INTO public.auth_login_requests "
            "(id, user_id, status, match_number, candidates, pending_token_hash, device_token_hash, "
            " label, user_agent, ip, location, created_at, expires_at) "
            "VALUES (:id, :uid, 'pending', :num, :cands, :ph, :dh, :label, :ua, :ip, :loc, :now, :exp)"
        ),
        {
            "id": request_id,
            "uid": user_id,
            "num": match_number,
            "cands": candidates,
            "ph": hash_value(pending_raw),
            "dh": hash_value(device_clean) if device_clean else None,
            "label": label,
            "ua": ua,
            "ip": ip[:45] if ip else None,
            "loc": location,
            "now": now,
            "exp": expires_at,
        },
    )
    return NewRequest(request_id, pending_raw, match_number, candidates, expires_at, label, location)


$ sed -n 330,344p backend/app/routers/auth.py   # _notify_new_request
    match_number: str = Field(description="待つ機械に出す2けたの番号")
    expires_in: int = Field(description="依頼の有効秒数")
    has_trusted_device: bool = Field(description="いつもの機械があるか")
    has_recovery_codes: bool = Field(description="予備の合言葉が残っているか")


async def _notify_new_request(
    background_tasks: BackgroundTasks, email: str, new: devices.NewRequest, user_id: int
) -> None:
    """許可依頼を、いつもの機械の画面（SSE）とメールで知らせる。失敗しても依頼は作ってある。"""
    await publish_user_change(user_id, TOPIC_AUTH_LOGIN_REQUEST)
    background_tasks.add_task(
        send_new_device_mail,
        email,
        when=devices.jst_text(),
$ sed -n 355,486p backend/app/routers/auth.py   # self_login (def 〜 次の @router 手前)
async def self_login(
    data: SelfLoginRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """自社ログイン。失敗理由は区別せず 1 種類の文言で返す。

    AUTH_DEVICE_APPROVAL=off（既定）は今までと同じ。enforce のとき、知らない機械は 202 で止める（ADR-1055）。
    """
    _require_issuance_enabled()
    _require_app_origin(request)
    ip = _get_client_ip(request)
    if await check_auth_rate_limit(ip):
        _audit(request, user_id=None, reason="rate_limited")
        raise HTTPException(status_code=429, detail="too_many_attempts")

    now = datetime.now(timezone.utc)
    email = data.email.strip().lower()
    user_row = (
        await db.execute(
            text(
                "SELECT id, email, tenant_id, is_active, password_argon2_hash, failed_login_count, locked_until, "
                "last_login FROM public.users WHERE lower(email) = :email"
            ),
            {"email": email},
        )
    ).first()
    locked_until = self_tokens._as_utc(user_row.locked_until) if user_row else None
    if user_row is None or not user_row.is_active or (locked_until is not None and locked_until > now):
        if user_row is None:
            _audit(request, user_id=None, reason="unknown_user")
        else:
            _audit(request, user_id=user_row.id, reason="inactive" if not user_row.is_active else "locked")
        await asyncio.to_thread(verify_password, None, data.password)
        await record_auth_failure(ip)
        raise _invalid_credentials()

    if not await asyncio.to_thread(verify_password, user_row.password_argon2_hash, data.password):
        _audit(request, user_id=user_row.id, reason="bad_password")
        await _count_login_failure(db, user_row, ip, now)
        raise _invalid_credentials()

    # 機械の判定（ADR-1055 D2〜D5・D11）。off は今までと同じ（機械の登録も印の発行もしない）
    trusted_device_id: int | None = None
    device_cookie_raw: str | None = None
    audit_reason, audit_new_device = "ok", None
    if devices.is_enforced():
        cookie_raw = request.cookies.get(devices.DEVICE_COOKIE_NAME)
        found = await devices.find_trusted_device(db, user_row.id, cookie_raw)
        if found is not None:
            # いつもの機械: 使った時刻を更新し、印の期限を延ばす
            await devices.touch_device(db, found.id, request)
            trusted_device_id = found.id
            device_cookie_raw = devices.clean_cookie_value(cookie_raw)
            audit_new_device = False
        elif user_row.last_login is None and await devices.count_all_devices(db, user_row.id) == 0:
            # D5: 一度もログインしていない人の最初のログイン。この機械を最初のいつもの機械にする
            trusted_device_id, device_cookie_raw = await devices.register_device(
                db, user_row.id, cookie_raw, "first_login", request
            )
            audit_reason, audit_new_device = "first_login", True
            background_tasks.add_task(
                send_new_device_mail,
                user_row.email,
                when=devices.jst_text(),
                device=devices.describe_user_agent(request.headers.get("user-agent")),
                location=geo.lookup(ip),
                note="この機械を最初のいつもの機械として登録しました。 / This device was registered as your first trusted device.",
            )
        else:
            # 知らない機械: 許可依頼を作って 202（トークンは出さない）
            new = await devices.create_login_request(db, user_row.id, request, cookie_raw)
            has_trusted = await devices.has_any_trusted_device(db, user_row.id)
            has_codes = (await recovery_codes.remaining(db, user_row.id)) > 0
            await db.commit()
            await _notify_new_request(background_tasks, user_row.email, new, user_row.id)
            pending = JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=LoginApprovalRequired(
                    match_number=new.match_number,
                    expires_in=int(devices.REQUEST_TTL.total_seconds()),
                    has_trusted_device=has_trusted,
                    has_recovery_codes=has_codes,
                ).model_dump(),
            )
            devices.set_pending_cookie(pending, new.pending_raw)
            _audit(
                request,
                user_id=user_row.id,
                reason="device_approval_required",
                is_new_device=True,
                event_type="auth_pending",
            )
            return pending

    await set_tenant_context(db, user_row.tenant_id)
    await db.execute(
        text(
            "UPDATE public.users SET failed_login_count = 0, locked_until = NULL, last_login = :now "
            "WHERE id = :id"
        ),
        {"now": now, "id": user_row.id},
    )
    if needs_rehash(user_row.password_argon2_hash):
        new_hash = await asyncio.to_thread(hash_password, data.password)
        await db.execute(
            text("UPDATE public.users SET password_argon2_hash = :h WHERE id = :id"),
            {"h": new_hash, "id": user_row.id},
        )
    await clear_tenant_context(db)
    family_id = str(uuid.uuid4())
    raw, expires_at = await self_tokens.issue_refresh_token(
        db,
        user_row.id,
        request.headers.get("user-agent"),
        family_id=family_id,
        trusted_device_id=trusted_device_id,
    )
    await db.commit()
    access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd", family_id)
    if device_cookie_raw:
        devices.set_device_cookie(response, device_cookie_raw)
    _audit(request, user_id=user_row.id, reason=audit_reason, is_new_device=audit_new_device)
    return SelfTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
    )



## R7
$ grep -rn 'get_current_session\|resolve_current_session\|CurrentSession' backend/app
backend/app/auth/dependencies.py:712:class CurrentSession:
backend/app/auth/dependencies.py:721:async def resolve_current_session(request: Request, db: AsyncSession, user: User) -> CurrentSession:
backend/app/auth/dependencies.py:747:    return CurrentSession(
backend/app/auth/dependencies.py:755:async def get_current_session(
backend/app/auth/dependencies.py:759:) -> CurrentSession:
backend/app/auth/dependencies.py:760:    """承認・拒否・機械の一覧・機械の取り消しが使う依存。get_current_user の後に resolve_current_session を呼ぶ。"""
backend/app/auth/dependencies.py:762:    return await resolve_current_session(request, db, user)
backend/app/routers/auth.py:25:    CurrentSession,
backend/app/routers/auth.py:28:    get_current_session,
backend/app/routers/auth.py:31:    resolve_current_session,
backend/app/routers/auth.py:751:        session = await resolve_current_session(request, db, current_user)
backend/app/routers/auth.py:1543:    session: CurrentSession = Depends(get_current_session),
backend/app/routers/auth.py:1587:    session: CurrentSession = Depends(get_current_session),
backend/app/routers/auth.py:1620:    session: CurrentSession = Depends(get_current_session),
backend/app/routers/auth.py:1654:    session: CurrentSession = Depends(get_current_session),
$ sed -n 711,719p backend/app/auth/dependencies.py   # CurrentSession 全体
@dataclass(frozen=True)
class CurrentSession:
    """今のログイン（更新トークンの組）。trusted_device_id は取り消されていない機械だけ（無ければ None）。"""

    user: User
    sid: str
    trusted_device_id: int | None
    family_created_at: datetime | None

$ grep -rn 'def _require_app_origin\|def require_app_origin' backend/app
backend/app/auth/origin.py:10:def require_app_origin(request: Request) -> None:

## R8
$ sed -n 93,494p backend/app/realtime/topics.py   # NO_SIGNAL_ROUTES
NO_SIGNAL_ROUTES: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/admin/channel-masters"): _PENDING,
    ("DELETE", "/api/v1/admin/channel-masters/{master_id}"): _PENDING,
    ("DELETE", "/api/v1/admin/discord-config"): _PENDING,
    ("PUT", "/api/v1/admin/discord-config"): _PENDING,
    ("PUT", "/api/v1/admin/discord-ticket-config"): _PENDING,
    ("POST", "/api/v1/admin/discord-ticket-config/deploy-button"): _PENDING,
    ("POST", "/api/v1/admin/discord/auto-setup"): _PENDING,
    ("PUT", "/api/v1/admin/inventory-visibility/roles/{role_id}"): _PENDING,
    ("PUT", "/api/v1/admin/tenant-policy"): _PENDING,
    ("PUT", "/api/v1/admin/tenant-profile"): _PENDING,
    ("POST", "/api/v1/admin/tenants"): _PENDING,
    ("POST", "/api/v1/archives"): _PENDING,
    ("POST", "/api/v1/archives/{archive_id}/restore"): _PENDING,
    # ADR-1056: 下書きを返すだけで何も作らない
    ("POST", "/api/v1/assistant/messages"): _PENDING,
    ("POST", "/api/v1/auth/login"): _PENDING,
    ("POST", "/api/v1/auth/logout"): _PENDING,
    ("POST", "/api/v1/auth/login-requests/poll"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",
    ("POST", "/api/v1/auth/login-requests/recovery"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",
    ("POST", "/api/v1/auth/login-requests/{request_id}/approve"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",
    ("POST", "/api/v1/auth/login-requests/{request_id}/reject"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",
    ("DELETE", "/api/v1/auth/devices/{device_id}"): "機械の取り消しは本人の画面の応答で差し替える。人宛ての合図は口の中で直接送る（ADR-1055）",
    ("POST", "/api/v1/auth/recovery-codes"): "予備の合言葉の作り直しは本人の画面の応答で差し替える（ADR-1055）",
    ("POST", "/api/v1/super-admin/login-requests/{request_id}/approve"): "人宛ての合図は口の中で直接送る（ADR-1055）。書き込みの口の自動合図にしない",
    ("POST", "/api/v1/tcg/analysis-results/client-timing"): "データを変えない。計時ログを1行残すだけ",
    ("POST", "/api/v1/viewer/login"): "閲覧ページ ADR-1019: 閲覧者のログインは画面更新の通知対象外",
    ("POST", "/api/v1/viewer/logout"): "閲覧ページ ADR-1019: 閲覧者のログアウトは画面更新の通知対象外",
    ("POST", "/api/v1/viewer/password"): "閲覧ページ ADR-1019: 閲覧者のパスワード変更は画面更新の通知対象外",
    ("POST", "/api/v1/viewer/password-reset/request"): "閲覧ページ ADR-1019: 閲覧者のパスワード再発行の申請は画面更新の通知対象外",
    ("POST", "/api/v1/viewer/password-reset/confirm"): "閲覧ページ ADR-1019: 閲覧者のパスワード再発行の確定は画面更新の通知対象外",
    ("POST", "/api/v1/viewer/signup"): "閲覧ページ ADR-1019: 閲覧者の申込は画面更新の通知対象外",
    ("POST", "/api/v1/super-admin/viewers/{viewer_id}/activate"): "閲覧者管理 ADR-1019: 社外の閲覧者の状態変更で画面更新の通知対象外",
    ("POST", "/api/v1/super-admin/viewers/{viewer_id}/suspend"): "閲覧者管理 ADR-1019: 社外の閲覧者の状態変更で画面更新の通知対象外",
    ("POST", "/api/v1/super-admin/viewers/{viewer_id}/unsuspend"): "閲覧者管理 ADR-1019: 社外の閲覧者の状態変更で画面更新の通知対象外",
    ("POST", "/api/v1/super-admin/viewers/{viewer_id}/extend"): "閲覧者管理 ADR-1019: 社外の閲覧者の状態変更で画面更新の通知対象外",
    ("POST", "/api/v1/super-admin/viewers/{viewer_id}/reissue-signup-code"): "閲覧者管理 ADR-1019: 一覧に出る値を変えない（申込コードを置き換えるだけ）ので通知対象外",
    ("PATCH", "/api/v1/super-admin/viewers/{viewer_id}"): "閲覧者管理 ADR-1019: 社外の閲覧者の LINE名の訂正で画面更新の通知対象外（保存した画面は応答で差し替える）",
    ("PUT", "/api/v1/super-admin/viewer-templates/{key}"): "閲覧者管理 段11: 文面テンプレートの本文を直すだけで画面更新の通知対象外（保存した画面は応答で差し替える）",
    ("POST", "/api/v1/ops/alertmanager"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/control/halt"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/control/resume"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/incidents/{incident_id}/events"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/incidents/human"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/incidents/{incident_id}/close"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/case/audits"): "相談係 ADR-1052 段2: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/case/unmask-requests/{request_id}/decision"): "相談係 ADR-1052 段2: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/case/{incident_id}/report"): "相談係 ADR-1052 段2: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/case/{incident_id}/ticket"): "相談係 ADR-1052 段2: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/case/{incident_id}/unmask-requests"): "相談係 ADR-1052 段2: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/auth/password-reset/confirm"): _PENDING,
    ("POST", "/api/v1/auth/password-reset/request"): _PENDING,
    ("POST", "/api/v1/auth/password/change"): _PENDING,
    ("POST", "/api/v1/auth/passkey/login/options"): _PENDING,
    ("POST", "/api/v1/auth/passkey/login/verify"): _PENDING,
    ("POST", "/api/v1/auth/passkey/register/options"): _PENDING,
    ("POST", "/api/v1/auth/passkey/register/verify"): _PENDING,
    ("POST", "/api/v1/auth/passkey/prompt/skip"): "ログイン直後の案内 ADR-1013: 本人の案内を出すかどうかの記録だけで画面更新の通知対象外",
    ("DELETE", "/api/v1/auth/passkeys/{passkey_id}"): _PENDING,
    ("POST", "/api/v1/auth/refresh"): _PENDING,
    ("POST", "/api/v1/auth/register"): _PENDING,
    ("POST", "/api/v1/bots"): _PENDING,
    ("DELETE", "/api/v1/bots/{bot_id}"): _PENDING,
    ("PATCH", "/api/v1/bots/{bot_id}"): _PENDING,
    ("POST", "/api/v1/bots/{bot_id}/rotate-key"): _PENDING,
    ("POST", "/api/v1/buyback-alerts"): _PENDING,
    ("DELETE", "/api/v1/buyback-alerts/{rule_id}"): _PENDING,
    ("PUT", "/api/v1/buyback-alerts/{rule_id}"): _PENDING,
    ("POST", "/api/v1/buyback-prices/rematch"): _PENDING,
    ("POST", "/api/v1/buyback-prices/trigger"): _PENDING,
    ("POST", "/api/v1/buyback-prices/{shop_product_id}/link"): _PENDING,
    ("POST", "/api/v1/calendar/events"): _PENDING,
    ("DELETE", "/api/v1/calendar/events/{event_id}"): _PENDING,
    ("PATCH", "/api/v1/calendar/events/{event_id}"): _PENDING,
    ("PATCH", "/api/v1/calendar/owners/{user_id}"): _PENDING,
    ("PATCH", "/api/v1/calendar/sync-mode"): _PENDING,
    ("POST", "/api/v1/close-reasons"): _PENDING,
    ("PATCH", "/api/v1/close-reasons/{reason_id}"): _PENDING,
    ("POST", "/api/v1/companies"): _PENDING,
    ("DELETE", "/api/v1/companies/{company_id}"): _PENDING,
    ("PATCH", "/api/v1/companies/{company_id}"): _PENDING,
    ("POST", "/api/v1/companies/{master_id}/merge"): _PENDING,
    ("POST", "/api/v1/conditions"): _PENDING,
    ("DELETE", "/api/v1/conditions/aliases/{alias_id}"): _PENDING,
    ("POST", "/api/v1/conditions/import/commit"): _PENDING,
    ("POST", "/api/v1/conditions/import/preview"): _PENDING,
    ("DELETE", "/api/v1/conditions/{condition_id}"): _PENDING,
    ("PATCH", "/api/v1/conditions/{condition_id}"): _PENDING,
    ("POST", "/api/v1/conditions/{condition_id}/aliases"): _PENDING,
    ("POST", "/api/v1/contact"): _PENDING,
    ("POST", "/api/v1/contacts"): _PENDING,
    ("DELETE", "/api/v1/contacts/{contact_id}"): _PENDING,
    ("PATCH", "/api/v1/contacts/{contact_id}"): _PENDING,
    ("POST", "/api/v1/contacts/{contact_id}/channel-acknowledge-duplicate"): _PENDING,
    ("POST", "/api/v1/contacts/{master_id}/merge"): _PENDING,
    ("POST", "/api/v1/discord/announce"): _PENDING,
    ("POST", "/api/v1/discord/ban/{lead_id}"): _PENDING,
    ("POST", "/api/v1/discord/channel-invite/{lead_id}"): _PENDING,
    ("POST", "/api/v1/discord/kick/{lead_id}"): _PENDING,
    ("POST", "/api/v1/discord/oauth/start"): _PENDING,
    ("POST", "/api/v1/discord/remove-from-channel/{lead_id}"): _PENDING,
    ("POST", "/api/v1/discord/sync-role/{lead_id}"): _PENDING,
    ("POST", "/api/v1/erp/export-invoices"): _PENDING,
    ("POST", "/api/v1/goals"): _PENDING,
    ("DELETE", "/api/v1/goals/{goal_id}"): _PENDING,
    ("PATCH", "/api/v1/goals/{goal_id}"): _PENDING,
    ("DELETE", "/api/v1/google-calendar/connect"): _PENDING,
    ("POST", "/api/v1/google-calendar/events"): _PENDING,
    ("DELETE", "/api/v1/google-calendar/events/{event_id}"): _PENDING,
    ("PATCH", "/api/v1/google-calendar/events/{event_id}"): _PENDING,
    ("POST", "/api/v1/google-calendar/webhook"): _PENDING,
    ("DELETE", "/api/v1/integrations/carriers/{carrier}/credentials"): _PENDING,
    ("PUT", "/api/v1/integrations/carriers/{carrier}/credentials"): _PENDING,
    ("POST", "/api/v1/integrations/carriers/{carrier}/test-connection"): _PENDING,
    ("DELETE", "/api/v1/integrations/google-drive/connect"): _PENDING,
    ("POST", "/api/v1/integrations/google-drive/test-upload"): _PENDING,
    ("DELETE", "/api/v1/integrations/paypal/credentials"): _PENDING,
    ("PUT", "/api/v1/integrations/paypal/credentials"): _PENDING,
    ("POST", "/api/v1/integrations/paypal/test-connection"): _PENDING,
    ("POST", "/api/v1/integrations/paypal/test-invoice"): _PENDING,
    ("POST", "/api/v1/integrations/paypal/webhook"): _PENDING,
    ("POST", "/api/v1/invoices"): _PENDING,
    ("POST", "/api/v1/invoices/from-quote/{quote_id}"): _PENDING,
    ("PATCH", "/api/v1/invoices/{invoice_id}"): _PENDING,
    ("POST", "/api/v1/invoices/{invoice_id}/issue"): _PENDING,
    ("POST", "/api/v1/invoices/{invoice_id}/pay"): _PENDING,
    ("POST", "/api/v1/invoices/{invoice_id}/paypal-confirm"): _PENDING,
    ("POST", "/api/v1/invoices/{invoice_id}/paypal-link"): _PENDING,
    ("POST", "/api/v1/invoices/{invoice_id}/void"): _PENDING,
    ("POST", "/api/v1/leads"): _PENDING,
    ("DELETE", "/api/v1/leads/{lead_id}"): _PENDING,
    ("PATCH", "/api/v1/leads/{lead_id}"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/conv-logs"): _PENDING,
    ("DELETE", "/api/v1/leads/{lead_id}/conv-logs/{log_id}"): _PENDING,
    ("PATCH", "/api/v1/leads/{lead_id}/conv-logs/{log_id}"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/convert"): _PENDING,
    ("PATCH", "/api/v1/leads/{lead_id}/message-labels/{label_id}/override"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages/image"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages/mark-read"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages/mark-unread"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages/{message_id}/reactions"): _PENDING,
    ("DELETE", "/api/v1/leads/{lead_id}/messages/{message_id}/reactions/{emoji}"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/messages/{message_id}/translate"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/priority-score/override"): _PENDING,
    ("POST", "/api/v1/leads/{lead_id}/priority-score/recalculate"): _PENDING,
    ("POST", "/api/v1/leads/{master_id}/merge"): _PENDING,
    ("POST", "/api/v1/leads/{master_id}/merge/preview"): _PENDING,
    ("PATCH", "/api/v1/me/inventory-filters"): _PENDING,
    ("POST", "/api/v1/meta/connect/start"): _PENDING,
    ("DELETE", "/api/v1/meta/connect/{page_id}"): _PENDING,
    ("POST", "/api/v1/meta/data-deletion"): _PENDING,
    ("POST", "/api/v1/note-master"): _PENDING,
    ("POST", "/api/v1/note-master/import/commit"): _PENDING,
    ("POST", "/api/v1/note-master/import/preview"): _PENDING,
    ("DELETE", "/api/v1/note-master/{note_id}"): _PENDING,
    ("PATCH", "/api/v1/note-master/{note_id}"): _PENDING,
    ("POST", "/api/v1/notification-channels"): _PENDING,
    ("DELETE", "/api/v1/notification-channels/{channel_id}"): _PENDING,
    ("PATCH", "/api/v1/notification-channels/{channel_id}"): _PENDING,
    ("POST", "/api/v1/orders"): _PENDING,
    ("DELETE", "/api/v1/orders/{order_id}"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/commissions/assign"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/commissions/recalc"): _PENDING,
    ("DELETE", "/api/v1/orders/{order_id}/commissions/{role}"): _PENDING,
    ("DELETE", "/api/v1/orders/{order_id}/financial"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}/financial"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/financial"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/items"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}/paid"): _PENDING,
    ("DELETE", "/api/v1/orders/{order_id}/purchase"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}/purchase"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/purchase"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}/purchase/status"): _PENDING,
    ("DELETE", "/api/v1/orders/{order_id}/shipping"): _PENDING,
    ("PATCH", "/api/v1/orders/{order_id}/shipping"): _PENDING,
    ("POST", "/api/v1/orders/{order_id}/shipping"): _PENDING,
    ("POST", "/api/v1/own-inventory"): _PENDING,
    ("PATCH", "/api/v1/own-inventory/{own_inventory_id}"): _PENDING,
    ("POST", "/api/v1/own-inventory/{own_inventory_id}/release"): _PENDING,
    ("POST", "/api/v1/own-inventory/{own_inventory_id}/reserve"): _PENDING,
    ("POST", "/api/v1/own-inventory/{own_inventory_id}/ship"): _PENDING,
    ("POST", "/api/v1/payment-fee-settings"): _PENDING,
    ("DELETE", "/api/v1/payment-fee-settings/{setting_id}"): _PENDING,
    ("PATCH", "/api/v1/payment-fee-settings/{setting_id}"): _PENDING,
    ("POST", "/api/v1/product-categories"): _PENDING,
    ("POST", "/api/v1/product-categories/import/commit"): _PENDING,
    ("POST", "/api/v1/product-categories/import/preview"): _PENDING,
    ("DELETE", "/api/v1/product-categories/{category_id}"): _PENDING,
    ("PATCH", "/api/v1/product-categories/{category_id}"): _PENDING,
    ("POST", "/api/v1/products"): _PENDING,
    ("DELETE", "/api/v1/products/{product_id}"): _PENDING,
    ("PATCH", "/api/v1/products/{product_id}"): _PENDING,
    ("POST", "/api/v1/public/register"): _PENDING,
    ("POST", "/api/v1/public/register/address"): _PENDING,
    ("POST", "/api/v1/public/register/change-billing"): _PENDING,
    ("POST", "/api/v1/purchase-orders"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/cancel"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/order"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/receive"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/resend-email"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/send-email"): _PENDING,
    ("POST", "/api/v1/purchase-orders/{po_id}/unreceive"): _PENDING,
    ("POST", "/api/v1/quotes"): _PENDING,
    ("DELETE", "/api/v1/quotes/{quote_id}"): _PENDING,
    ("PATCH", "/api/v1/quotes/{quote_id}"): _PENDING,
    ("POST", "/api/v1/quotes/{quote_id}/approve"): _PENDING,
    ("POST", "/api/v1/quotes/{quote_id}/reject"): _PENDING,
    ("POST", "/api/v1/quotes/{quote_id}/send"): _PENDING,
    ("POST", "/api/v1/registration-tokens"): _PENDING,
    ("POST", "/api/v1/reports/export"): _PENDING,
    ("POST", "/api/v1/roles"): _PENDING,
    ("DELETE", "/api/v1/roles/{role_id}"): _PENDING,
    ("PATCH", "/api/v1/roles/{role_id}"): _PENDING,
    ("PUT", "/api/v1/roles/{role_id}/permissions"): _PENDING,
    ("POST", "/api/v1/shifts"): _PENDING,
    ("DELETE", "/api/v1/shifts/{shift_id}"): _PENDING,
    ("POST", "/api/v1/shipping/calculate"): _PENDING,
    ("POST", "/api/v1/shipping/etd/images"): _PENDING,
    ("POST", "/api/v1/shipping/label-validation/samples"): _PENDING,
    ("POST", "/api/v1/shipping/pickups"): _PENDING,
    ("POST", "/api/v1/shipping/rates"): _PENDING,
    ("DELETE", "/api/v1/shipping/rates/{rate_id}"): _PENDING,
    ("POST", "/api/v1/shipping/shipments"): _PENDING,
    ("POST", "/api/v1/shipping/zones"): _PENDING,
    ("DELETE", "/api/v1/shipping/zones/{zone_id}"): _PENDING,
    ("POST", "/api/v1/staff"): _PENDING,
    ("POST", "/api/v1/staff-reports"): _PENDING,
    ("POST", "/api/v1/staff-reports/{report_id}/review"): _PENDING,
    ("DELETE", "/api/v1/staff/me/avatar"): _PENDING,
    ("POST", "/api/v1/staff/me/avatar"): _PENDING,
    ("PATCH", "/api/v1/staff/me/locale"): _PENDING,
    ("PATCH", "/api/v1/staff/me/profile"): _PENDING,
    ("PATCH", "/api/v1/staff/me/theme"): _PENDING,
    ("DELETE", "/api/v1/staff/{staff_id}"): _PENDING,
    ("PATCH", "/api/v1/staff/{staff_id}"): _PENDING,
    ("POST", "/api/v1/status-master"): _PENDING,
    ("POST", "/api/v1/status-master/import/commit"): _PENDING,
    ("POST", "/api/v1/status-master/import/preview"): _PENDING,
    ("DELETE", "/api/v1/status-master/{entry_id}"): _PENDING,
    ("PATCH", "/api/v1/status-master/{entry_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/aliases"): _PENDING,
    ("POST", "/api/v1/super-admin/aliases/import"): _PENDING,
    ("DELETE", "/api/v1/super-admin/aliases/{alias_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/aliases/{alias_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/condition-definitions"): _PENDING,
    ("DELETE", "/api/v1/super-admin/condition-definitions/{def_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/condition-definitions/{def_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/conditions"): _PENDING,
    ("DELETE", "/api/v1/super-admin/conditions/aliases/{alias_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/conditions/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/conditions/import/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/conditions/{condition_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/conditions/{condition_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/conditions/{condition_id}/aliases"): _PENDING,
    ("POST", "/api/v1/super-admin/dex/pokemon/import/apply"): _PENDING,
    ("POST", "/api/v1/super-admin/dex/pokemon/import/preview"): _PENDING,
    ("POST", "/api/v1/super-admin/dex/{dex_kind}"): _PENDING,
    ("DELETE", "/api/v1/super-admin/dex/{dex_kind}/{entry_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/dex/{dex_kind}/{entry_id}"): _PENDING,
    ("PUT", "/api/v1/super-admin/extraction-prompts/{prompt_key}"): _PENDING,
    ("POST", "/api/v1/super-admin/fx-rate/refresh"): _PENDING,
    ("POST", "/api/v1/super-admin/inventory-offers"): _PENDING,
    ("DELETE", "/api/v1/super-admin/inventory-offers/{offer_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/inventory-offers/{offer_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/knowledge"): _PENDING,
    ("POST", "/api/v1/super-admin/knowledge-rules"): _PENDING,
    ("POST", "/api/v1/super-admin/knowledge/import"): _PENDING,
    ("DELETE", "/api/v1/super-admin/knowledge/{rule_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/knowledge/{rule_id}"): _PENDING,
    ("DELETE", "/api/v1/super-admin/link-templates/{channel}"): _PENDING,
    ("PUT", "/api/v1/super-admin/link-templates/{channel}"): _PENDING,
    ("PUT", "/api/v1/super-admin/llm-budget/{tenant_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/note-master"): _PENDING,
    ("POST", "/api/v1/super-admin/note-master/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/note-master/import/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/note-master/{note_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/note-master/{note_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/payment-fee-settings"): _PENDING,
    ("DELETE", "/api/v1/super-admin/payment-fee-settings/{setting_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/payment-fee-settings/{setting_id}"): _PENDING,
    ("PUT", "/api/v1/super-admin/phase-switch/{tenant_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/product-categories"): _PENDING,
    ("POST", "/api/v1/super-admin/product-categories/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/product-categories/import/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/product-categories/{category_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/product-categories/{category_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/product-formats"): _PENDING,
    ("DELETE", "/api/v1/super-admin/product-formats/{format_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/product-formats/{format_id}"): _PENDING,
    ("PUT", "/api/v1/super-admin/product-formats/{format_id}/games"): _PENDING,
    ("POST", "/api/v1/super-admin/product-kinds"): _PENDING,
    ("DELETE", "/api/v1/super-admin/product-kinds/{kind_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/product-kinds/{kind_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/product-lines"): _PENDING,
    ("DELETE", "/api/v1/super-admin/product-lines/{line_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/product-lines/{line_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/product-masters"): _PENDING,
    ("DELETE", "/api/v1/super-admin/product-masters/{master_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/product-masters/{master_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/quantity-units"): _PENDING,
    ("DELETE", "/api/v1/super-admin/quantity-units/{unit_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/quantity-units/{unit_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/rule-tests/cases"): _PENDING,
    ("POST", "/api/v1/super-admin/rule-tests/cases/seed"): _PENDING,
    ("DELETE", "/api/v1/super-admin/rule-tests/cases/{case_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/rule-tests/run"): _PENDING,
    ("POST", "/api/v1/super-admin/status-master"): _PENDING,
    ("POST", "/api/v1/super-admin/status-master/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/status-master/import/preview"): _PENDING,
    ("POST", "/api/v1/super-admin/status-master/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/status-master/{entry_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/status-master/{entry_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/suppliers"): _PENDING,
    ("DELETE", "/api/v1/super-admin/suppliers/discord-routing/{routing_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/suppliers/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/suppliers/import/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/suppliers/{supplier_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/suppliers/{supplier_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/suppliers/{supplier_id}/discord-routing"): _PENDING,
    ("PATCH", "/api/v1/super-admin/suppliers/{supplier_id}/extraction-rules"): _PENDING,
    ("POST", "/api/v1/super-admin/suppliers/{supplier_id}/knowledge-links"): _PENDING,
    ("DELETE", "/api/v1/super-admin/suppliers/{supplier_id}/knowledge-links/{link_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/tcg/series"): _PENDING,
    ("DELETE", "/api/v1/super-admin/tcg/series/{series_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/tcg/series/{series_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/tcg/types"): _PENDING,
    ("DELETE", "/api/v1/super-admin/tcg/types/{type_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/tcg/types/{type_id}"): _PENDING,
    ("DELETE", "/api/v1/super-admin/tenants/{tenant_id}"): _PENDING,
    ("DELETE", "/api/v1/super-admin/tenants/{tenant_id}/physical"): _PENDING,
    ("POST", "/api/v1/super-admin/unit-ignore-phrases"): _PENDING,
    ("DELETE", "/api/v1/super-admin/unit-ignore-phrases/{phrase_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/unit-ignore-phrases/{phrase_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/units"): _PENDING,
    ("DELETE", "/api/v1/super-admin/units/aliases/{alias_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/units/import/commit"): _PENDING,
    ("POST", "/api/v1/super-admin/units/import/preview"): _PENDING,
    ("DELETE", "/api/v1/super-admin/units/{unit_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/units/{unit_id}"): _PENDING,
    ("POST", "/api/v1/super-admin/units/{unit_id}/aliases"): _PENDING,
    ("POST", "/api/v1/super-admin/weight-classes"): _PENDING,
    ("DELETE", "/api/v1/super-admin/weight-classes/{class_id}"): _PENDING,
    ("PATCH", "/api/v1/super-admin/weight-classes/{class_id}"): _PENDING,
    ("POST", "/api/v1/suppliers"): _PENDING,
    ("POST", "/api/v1/suppliers/import/commit"): _PENDING,
    ("POST", "/api/v1/suppliers/import/preview"): _PENDING,
    ("DELETE", "/api/v1/suppliers/{supplier_id}"): _PENDING,
    ("PATCH", "/api/v1/suppliers/{supplier_id}"): _PENDING,
    ("POST", "/api/v1/tcg/diagnostics/retry-extraction"): _PENDING,
    ("POST", "/api/v1/tcg/distribution/run"): _PENDING,
    ("POST", "/api/v1/tcg/distribution/run/{target_id}"): _PENDING,
    ("PUT", "/api/v1/tcg/distribution/settings/{key}"): _PENDING,
    ("POST", "/api/v1/tcg/distribution/targets"): _PENDING,
    ("DELETE", "/api/v1/tcg/distribution/targets/{target_id}"): _PENDING,
    ("PUT", "/api/v1/tcg/distribution/targets/{target_id}"): _PENDING,
    ("POST", "/api/v1/tcg/extraction-jobs/{extraction_job_id}/reanalyze"): _PENDING,
    ("POST", "/api/v1/ops/error-reports/{report_code}/events"): "誤り報告の記録のみ。画面に出る在庫データは変えない（ADR-1025 便2）",
    ("POST", "/api/v1/ops/error-reports/{report_code}/reanalyze"): _PENDING,
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/corrections"): _PENDING,
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/error-reports"): "誤り報告の記録のみ。画面に出る在庫データは変えない（ADR-1025 便1）",
    ("POST", "/api/v1/tcg/line-devices/approve"): _PENDING,
    ("POST", "/api/v1/tcg/line-devices/import"): _PENDING,
    ("POST", "/api/v1/tcg/line-devices/start"): _PENDING,
    ("POST", "/api/v1/tcg/line-devices/{identifier}/revoke"): _PENDING,
    ("POST", "/api/v1/tcg/line-import"): _PENDING,
    ("POST", "/api/v1/tcg/line-import/android"): _PENDING,
    ("POST", "/api/v1/tcg/line-import/{import_job_id}/commit"): _PENDING,
    ("POST", "/api/v1/tcg/line-import/{import_job_id}/resolve"): _PENDING,
    ("POST", "/api/v1/tcg/products"): _PENDING,
    ("POST", "/api/v1/tcg/products/check-duplicates"): _PENDING,
    ("POST", "/api/v1/tcg/products/create"): _PENDING,
    ("DELETE", "/api/v1/tcg/products/detail/{product_id}"): _PENDING,
    ("PUT", "/api/v1/tcg/products/detail/{product_id}"): _PENDING,
    ("POST", "/api/v1/tcg/products/import/commit"): _PENDING,
    ("POST", "/api/v1/tcg/products/import/preview"): _PENDING,
    ("POST", "/api/v1/tcg/products/{product_id}/exclude-keywords"): _PENDING,
    ("POST", "/api/v1/tcg/products/{product_id}/search-keywords"): _PENDING,
    ("POST", "/api/v1/tcg/review/csv/commit"): _PENDING,
    ("POST", "/api/v1/tcg/review/csv/preview"): _PENDING,
    ("PUT", "/api/v1/tcg/v102/posts/{job_id}/items"): _PENDING,
    ("POST", "/api/v1/teams"): _PENDING,
    ("DELETE", "/api/v1/teams/{team_id}"): _PENDING,
    ("PATCH", "/api/v1/teams/{team_id}"): _PENDING,
    ("POST", "/api/v1/teams/{team_id}/members"): _PENDING,
    ("DELETE", "/api/v1/teams/{team_id}/members/{user_id}"): _PENDING,
    ("PATCH", "/api/v1/tenant-commission-settings"): _PENDING,
    ("POST", "/api/v1/translation/glossary"): _PENDING,
    ("POST", "/api/v1/translation/glossary/seed-products"): _PENDING,
    ("DELETE", "/api/v1/translation/glossary/{entry_id}"): _PENDING,
    ("PATCH", "/api/v1/translation/glossary/{entry_id}"): _PENDING,
    ("POST", "/api/v1/translation/outbound-confirm/{draft_id}"): _PENDING,
    ("POST", "/api/v1/translation/outbound-preview"): _PENDING,
    ("POST", "/api/v1/units"): _PENDING,
    ("POST", "/api/v1/units/import/commit"): _PENDING,
    ("POST", "/api/v1/units/import/preview"): _PENDING,
    ("DELETE", "/api/v1/units/{unit_id}"): _PENDING,
    ("PATCH", "/api/v1/units/{unit_id}"): _PENDING,
    ("PUT", "/api/v1/users/{user_id}/roles"): _PENDING,
    ("POST", "/api/v1/webhook/messenger"): _PENDING,
}
$ sed -n 19,33p backend/tests/test_realtime_topics.py   # _write_routes
def _write_routes():
    # 遅延 import: 収集時に app.main を読むと、全権限モック(conftest bypass_permissions)の前に
    # inventory_search が本物の load_user_permissions を束縛し、他の試験が 403 になる
    from app.main import app

    out = {}
    for r in app.routes:
        methods = getattr(r, "methods", None)
        if not methods:
            continue
        for m in methods & _WRITE:
            out[(m, r.path)] = r
    return out



## R9
$ grep -n -B3 -A3 "AUTH_PROVIDER\|GEOIP_DB_PATH\|AUTH_DEVICE" docker-compose.yml
131-      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
132-      - MAIL_FROM=${MAIL_FROM:-}
133-      - CONTACT_NOTIFY_EMAIL=${CONTACT_NOTIFY_EMAIL:-}
134:      # ADR-1013 便4b: 自社ログインへの切り替え。.env に AUTH_PROVIDER=self が入る。
135-      # 戻すときは deploy.yml の heredoc を firebase に変える前進 PR（revert はしない）
136:      - AUTH_PROVIDER=${AUTH_PROVIDER:-firebase}
137-      - AUTH_JWT_SECRET=${AUTH_JWT_SECRET:-}
138-      # ADR-1019 段2: 閲覧者のトークンの鍵。この行が無いと .env に値があっても os.getenv が空になる。
139-      - AUTH_VIEWER_JWT_SECRET=${AUTH_VIEWER_JWT_SECRET:-}
--
146-      - CASE_AGENT_TOKEN=${CASE_AGENT_TOKEN:-}
147-      - CASE_ADMIN_TOKEN=${CASE_ADMIN_TOKEN:-}
148-      # ADR-1055 段A: 知らない機械からのログインの許可。off（既定）は今のログインと同じ。enforce は段B で deploy.yml が入れる。
149:      # 締切 AUTH_DEVICE_BOOTSTRAP_CUTOFF が空なら、ログイン中だった機械の自動登録（D4）をしない。
150:      - AUTH_DEVICE_APPROVAL=${AUTH_DEVICE_APPROVAL:-off}
151:      - AUTH_DEVICE_BOOTSTRAP_CUTOFF=${AUTH_DEVICE_BOOTSTRAP_CUTOFF:-}
152-      # 場所の目安の元データ（DB-IP City Lite）。.env で空にすると場所の表示が止まる（空以外の値は入れない）
153:      - GEOIP_DB_PATH=${GEOIP_DB_PATH-/geoip/dbip-city-lite.mmdb}
154-    volumes:
155-      # 場所の元データは celery-worker が書き、backend は読むだけ（ADR-1055 D9）
156-      - geoip:/geoip:ro
--
198-        VITE_FIREBASE_AUTH_DOMAIN: ${VITE_FIREBASE_AUTH_DOMAIN}
199-        VITE_GCP_PROJECT_ID: ${VITE_GCP_PROJECT_ID}
200-        VITE_FUNNEL_DASHBOARD: ${VITE_FUNNEL_DASHBOARD}
201:        VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER:-firebase}
202-    restart: unless-stopped
203-    healthcheck:
204-      # localhost が IPv6 (::1) に解決され nginx の IPv4-only listen と
--
285-    volumes:
286-      - ./firebase-credentials.json:/app/firebase-credentials.json:ro
287-      - ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro
288:      # 場所の元データ（DB-IP）を月次で書く。worker は GEOIP_DB_PATH を受け取らず、コードの既定 /geoip/... に書く（ADR-1055 D9）
289-      - geoip:/geoip
290-    depends_on:
291-      postgres:
$ grep -n "secrets\." .github/workflows/deploy.yml
66:          GH_TOKEN: ${{ secrets.PIPELINE_PAT }}
100:          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
105:          ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts
111:            ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}:/home/ubuntu/salesanchor/www/salesanchor/
128:          VIEWER_CRED: ${{ secrets.DESIGN_SITE_VIEWER_CRED }}
129:          SMOKE_CRED: ${{ secrets.DESIGN_SITE_SMOKE_CRED }}
131:          host: ${{ secrets.VPS_HOST }}
132:          username: ${{ secrets.VPS_USER }}
133:          key: ${{ secrets.SSH_PRIVATE_KEY }}
150:            ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}:/home/ubuntu/salesanchor/www/design-site/
153:            ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}:/home/ubuntu/salesanchor/www/design-site/progress.json
164:          host: ${{ secrets.VPS_HOST }}
165:          username: ${{ secrets.VPS_USER }}
166:          key: ${{ secrets.SSH_PRIVATE_KEY }}
202:          host: ${{ secrets.VPS_HOST }}
203:          username: ${{ secrets.VPS_USER }}
204:          key: ${{ secrets.SSH_PRIVATE_KEY }}
238:          host: ${{ secrets.VPS_HOST }}
239:          username: ${{ secrets.VPS_USER }}
240:          key: ${{ secrets.SSH_PRIVATE_KEY }}
275:            #     `${{ secrets.X }}` 自体は GitHub Actions が SSH 送信前に展開する。
337:            cat > .env.secrets.new <<'ENV_EOF'
338:            META_VERIFY_TOKEN='${{ secrets.META_VERIFY_TOKEN }}'
339:            META_APP_SECRET='${{ secrets.META_APP_SECRET }}'
340:            META_APP_ID='${{ secrets.META_APP_ID }}'
341:            META_OAUTH_REDIRECT_URI='${{ secrets.META_OAUTH_REDIRECT_URI }}'
342:            METADATA_FERNET_KEY='${{ secrets.METADATA_FERNET_KEY }}'
343:            GEMINI_API_KEY='${{ secrets.GEMINI_API_KEY }}'
344:            ADMIN_NOTIFICATION_DISCORD_WEBHOOK='${{ secrets.ADMIN_NOTIFICATION_DISCORD_WEBHOOK }}'
345:            ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK='${{ secrets.ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK }}'
346:            GOOGLE_CALENDAR_CLIENT_ID='${{ secrets.GOOGLE_CALENDAR_CLIENT_ID }}'
347:            GOOGLE_CALENDAR_CLIENT_SECRET='${{ secrets.GOOGLE_CALENDAR_CLIENT_SECRET }}'
348:            GOOGLE_CALENDAR_REDIRECT_URI='${{ secrets.GOOGLE_CALENDAR_REDIRECT_URI }}'
349:            DISCORD_BOT_TOKEN='${{ secrets.DISCORD_BOT_TOKEN }}'
350:            GOOGLE_DRIVE_CLIENT_ID='${{ secrets.GOOGLE_DRIVE_CLIENT_ID }}'
351:            GOOGLE_DRIVE_CLIENT_SECRET='${{ secrets.GOOGLE_DRIVE_CLIENT_SECRET }}'
352:            GOOGLE_DRIVE_REDIRECT_URI='${{ secrets.GOOGLE_DRIVE_REDIRECT_URI }}'
353:            SMOKE_SERVICE_TOKEN='${{ secrets.FEDEX_SMOKE_API_TOKEN }}'
354:            SMOKE_SERVICE_EMAIL='${{ secrets.FEDEX_SMOKE_USER_EMAIL }}'
355:            REVIEW_MAIL_IMAP_HOST='${{ secrets.REVIEW_MAIL_IMAP_HOST }}'
356:            REVIEW_MAIL_IMAP_PORT='${{ secrets.REVIEW_MAIL_IMAP_PORT }}'
357:            REVIEW_MAIL_IMAP_USER='${{ secrets.REVIEW_MAIL_IMAP_USER }}'
358:            REVIEW_MAIL_IMAP_PASSWORD='${{ secrets.REVIEW_MAIL_IMAP_PASSWORD }}'
359:            REVIEW_MAIL_WEBMAIL_URL='${{ secrets.REVIEW_MAIL_WEBMAIL_URL }}'
360:            REVIEW_MAIL_DISCORD_WEBHOOK='${{ secrets.REVIEW_MAIL_DISCORD_WEBHOOK }}'
361:            OPS_MAIL_IMAP_USER='${{ secrets.OPS_MAIL_IMAP_USER }}'
362:            OPS_MAIL_IMAP_PASSWORD='${{ secrets.OPS_MAIL_IMAP_PASSWORD }}'
363:            OPS_MAIL_DISCORD_WEBHOOK='${{ secrets.OPS_MAIL_DISCORD_WEBHOOK }}'
364:            VITE_FUNNEL_DASHBOARD='${{ secrets.VITE_FUNNEL_DASHBOARD }}'
365:            SMTP_HOST='${{ secrets.SMTP_HOST }}'
366:            SMTP_PORT='${{ secrets.SMTP_PORT }}'
367:            SMTP_USER='${{ secrets.SMTP_USER }}'
368:            SMTP_PASSWORD='${{ secrets.SMTP_PASSWORD }}'
369:            MAIL_FROM='${{ secrets.MAIL_FROM }}'
370:            CONTACT_NOTIFY_EMAIL='${{ secrets.CONTACT_NOTIFY_EMAIL }}'
371:            AUTH_VIEWER_JWT_SECRET='${{ secrets.AUTH_VIEWER_JWT_SECRET }}'
373:            AUTH_JWT_SECRET='${{ secrets.AUTH_JWT_SECRET }}'
375:            OPS_API_TOKEN='${{ secrets.OPS_API_TOKEN }}'
376:            OPS_INGEST_TOKEN='${{ secrets.OPS_INGEST_TOKEN }}'
377:            ERROR_REPORT_AGENT_TOKEN='${{ secrets.ERROR_REPORT_AGENT_TOKEN }}'
378:            READ_WINDOW_TOKEN='${{ secrets.READ_WINDOW_TOKEN }}'
379:            CASE_AGENT_TOKEN='${{ secrets.CASE_AGENT_TOKEN }}'
380:            CASE_ADMIN_TOKEN='${{ secrets.CASE_ADMIN_TOKEN }}'
385:            _bad_lines=$(grep -nvE "^[A-Z0-9_]+='[^']*'$|^COMPOSE_FILE=" .env.secrets.new | cut -d: -f1 | tr '\n' ' ')
389:              rm -f .env.secrets.new
392:            cat .env.secrets.new >> .env
393:            rm -f .env.secrets.new .env.bak
514:          host: ${{ secrets.VPS_HOST }}
515:          username: ${{ secrets.VPS_USER }}
516:          key: ${{ secrets.SSH_PRIVATE_KEY }}
607:          host: ${{ secrets.VPS_HOST }}
608:          username: ${{ secrets.VPS_USER }}
609:          key: ${{ secrets.SSH_PRIVATE_KEY }}
625:          host: ${{ secrets.VPS_HOST }}
626:          username: ${{ secrets.VPS_USER }}
627:          key: ${{ secrets.SSH_PRIVATE_KEY }}
643:          host: ${{ secrets.VPS_HOST }}
644:          username: ${{ secrets.VPS_USER }}
645:          key: ${{ secrets.SSH_PRIVATE_KEY }}
664:          host: ${{ secrets.VPS_HOST }}
665:          username: ${{ secrets.VPS_USER }}
666:          key: ${{ secrets.SSH_PRIVATE_KEY }}
700:          host: ${{ secrets.VPS_HOST }}
701:          username: ${{ secrets.VPS_USER }}
702:          key: ${{ secrets.SSH_PRIVATE_KEY }}
754:          SALESANCHOR_APP_PASSWORD: ${{ secrets.SALESANCHOR_APP_PASSWORD }}
755:          ADMIN_DATABASE_URL: ${{ secrets.ADMIN_DATABASE_URL }}
762:          host: ${{ secrets.VPS_HOST }}
763:          username: ${{ secrets.VPS_USER }}
764:          key: ${{ secrets.SSH_PRIVATE_KEY }}
786:          host: ${{ secrets.VPS_HOST }}
787:          username: ${{ secrets.VPS_USER }}
788:          key: ${{ secrets.SSH_PRIVATE_KEY }}
800:          host: ${{ secrets.VPS_HOST }}
801:          username: ${{ secrets.VPS_USER }}
802:          key: ${{ secrets.SSH_PRIVATE_KEY }}
808:          SALESANCHOR_APP_PASSWORD: ${{ secrets.SALESANCHOR_APP_PASSWORD }}
821:          host: ${{ secrets.VPS_HOST }}
822:          username: ${{ secrets.VPS_USER }}
823:          key: ${{ secrets.SSH_PRIVATE_KEY }}
852:          SALESANCHOR_API_TOKEN: ${{ secrets.FEDEX_SMOKE_API_TOKEN }}
854:          ROLLBACK_DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}
856:          FEDEX_SMOKE_ENABLED: ${{ secrets.FEDEX_SMOKE_ENABLED }}
867:          ROLLBACK_DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}
869:          host: ${{ secrets.VPS_HOST }}
870:          username: ${{ secrets.VPS_USER }}
871:          key: ${{ secrets.SSH_PRIVATE_KEY }}
1021:          DESIGN_SITE_SMOKE_CRED: ${{ secrets.DESIGN_SITE_SMOKE_CRED }}
1023:          host: ${{ secrets.VPS_HOST }}
1024:          username: ${{ secrets.VPS_USER }}
1025:          key: ${{ secrets.SSH_PRIVATE_KEY }}
1117:          PIPELINE_PAT: ${{ secrets.PIPELINE_PAT }}
1118:          GH_TOKEN: ${{ secrets.PIPELINE_PAT }}
1257:          host: ${{ secrets.VPS_HOST }}
1258:          username: ${{ secrets.VPS_USER }}
1259:          key: ${{ secrets.SSH_PRIVATE_KEY }}
$ grep -n 'sed -i\|grep -v' .github/workflows/deploy.yml
282:            sed -i.bak \
403:              sed -i 's|@localhost:5432/|@postgres:5432/|g' .env
418:              sed -i '/^DATABASE_URL=/d' .env
724:              sed -i '/^DATABASE_URL=/d' .env
746:            sed -i '/^ADMIN_DATABASE_URL=/d' .env
912:                sed -i '/^DATABASE_URL=/d' .env
914:                sed -i '/^SA18_PHASE2_ENABLED=/d' .env

## R10
$ grep -n "" backend/requirements.txt
1:fastapi==0.136.3
2:starlette==1.3.1
3:uvicorn[standard]==0.34.0
4:sqlalchemy==2.0.38
5:asyncpg==0.31.0
6:psycopg2-binary==2.9.10
7:python-dotenv==1.2.2
8:pydantic[email]==2.10.6
9:pydantic-settings==2.13.1
10:bcrypt==4.2.1
11:phonenumbers==8.13.52
12:pycountry==24.6.1
13:firebase-admin==6.6.0
14:python-jose[cryptography]==3.5.0
15:httpx==0.28.1
16:redis[hiredis]>=5.0.0
17:celery[redis]>=5.4.0
18:# Meta Data Deletion Callback の Form パース用（B1）
19:python-multipart==0.0.31
20:# Discord Gateway worker (ADR-009)
21:discord.py==2.4.0
22:# Phase 1-D: Fernet 暗号化（Meta Page Access Token の保管）
23:# python-jose[cryptography] が transitive に持ち込むが、用途が異なるため直接依存として明示
24:cryptography==48.0.1
25:# ADR-1013 便5: パスキー。pyOpenSSL 26.2.0 は cryptography 48 と両立する唯一の版（26.3.0 以降と webauthn 3.x は cryptography>=49）
26:webauthn==2.8.0
27:pyOpenSSL==26.2.0
28:# Sprint 4 (F4): Gemini 2.5 Flash LLM フォールバック（在庫メッセージ解析）
29:# structured output (response_mime_type=application/json + response_schema) を使うため 0.8.0+
30:google-generativeai>=0.8.0,<0.9.0
31:# MIG-04 Stage 2: Gemini 抽出（google-genai SDK 新版）
32:google-genai>=1.0.0
33:# Sprint 8 (F8): PO PDF レンダリング (発注書 PDF + alias 置換 + 敬称分岐 + テナント名義)
34:# reportlab: 純 Python (BSD-3-Clause)、商用 OK、TrueType 日本語フォント embedding 対応
35:# 日本語フォント (NotoSansJP / IPA) は OS 側 or 環境変数 PO_PDF_FONT_PATH で参照
36:reportlab>=4.0.0,<5.0.0
37:# ADR-129: pypdf — FedEx 公式 Label Validation カバーシートのフォームフィリング用
38:pypdf>=4.0.0,<6.0.0
39:# Google Calendar OAuth 連携（tenant_google_calendar_config）
40:google-api-python-client>=2.100.0,<3.0.0
41:google-auth-oauthlib>=1.2.0,<2.0.0
42:google-auth-httplib2>=0.2.0,<1.0.0
43:# MIG-05 Task 3: TCG ミラーシート書き出し（salesanchor-drive SA）
44:gspread>=6.0,<7.0
45:# Sprint 3 (monitoring): FastAPI メトリクスを /metrics エンドポイントで Prometheus に公開
46:# rate_limit.py / audit.py の _SKIP_PATHS で除外済み
47:prometheus-client==0.25.0
48:# ADR-157: 買取相場ログ（買取ホムラ HTML スクレイピング用）
49:# ADR-159: 担当者アイコンの EXIF 除去・正方形切り抜き・WebP 再エンコード
50:Pillow==12.3.0
51:beautifulsoup4>=4.12.0
52:lxml>=5.0.0
53:argon2-cffi==25.1.0
54:maxminddb==3.2.0
$ grep -n -i 'cryptography\|http\|requests\|pyjwt\|maxminddb' backend/requirements.txt
14:python-jose[cryptography]==3.5.0
15:httpx==0.28.1
23:# python-jose[cryptography] が transitive に持ち込むが、用途が異なるため直接依存として明示
24:cryptography==48.0.1
25:# ADR-1013 便5: パスキー。pyOpenSSL 26.2.0 は cryptography 48 と両立する唯一の版（26.3.0 以降と webauthn 3.x は cryptography>=49）
42:google-auth-httplib2>=0.2.0,<1.0.0
54:maxminddb==3.2.0
$ pip index versions pywebpush
WARNING: pip index is currently an experimental command. It may be removed/changed in a future release without prior warning.
pywebpush (2.5.0)
Available versions: 2.5.0, 2.4.0, 2.3.0, 2.2.1, 2.2.0, 2.1.2, 2.1.1, 2.1.0, 2.0.3, 2.0.1, 2.0.0, 1.14.1, 1.14.0, 1.13.0, 1.12.0, 1.11.0, 1.10.2, 1.10.1, 1.10.0, 1.9.4, 1.9.3, 1.9.2, 1.9.1, 1.9.0, 1.8.0, 1.7.0, 1.6.1, 1.6.0, 1.5.0, 1.4.0, 1.3.1, 1.3.0, 1.2.0, 1.1.1, 1.1.0, 1.0.6, 1.0.5, 1.0.4, 1.0.2, 1.0.1, 1.0.0, 0.8.0, 0.7.0, 0.6.2, 0.6.1, 0.6.0, 0.4.0, 0.3.4, 0.3.3, 0.3.2, 0.3.1, 0.3, 0.4.0.linux-x86_64, 0.2.linux-x86_64
$ pip download pywebpush==2.5.0 --no-deps -d /tmp/pw
Collecting pywebpush==2.5.0
  Downloading pywebpush-2.5.0-py3-none-any.whl.metadata (10 kB)
Downloading pywebpush-2.5.0-py3-none-any.whl (22 kB)
Saved /tmp/pw/pywebpush-2.5.0-py3-none-any.whl
Successfully downloaded pywebpush
total 32
drwxr-xr-x 2 root root  4096 Nov  2 00:35 .
drwxrwxrwt 9 root root  4096 Nov  2 00:35 ..
-rw-r--r-- 1 root root 22520 Nov  2 00:35 pywebpush-2.5.0-py3-none-any.whl
$ unzip -p /tmp/pw/pywebpush-2.5.0-py3-none-any.whl '*/METADATA' | grep Requires-Dist
3:Version: 2.5.0
13:Requires-Python: >=3.10
16:Requires-Dist: aiohttp
17:Requires-Dist: cryptography>=47.0.0
18:Requires-Dist: http-ece>=1.1.0
19:Requires-Dist: requests>=2.21.0
20:Requires-Dist: py-vapid>=1.7.0
22:Requires-Dist: isort; extra == "dev"
23:Requires-Dist: bandit; extra == "dev"
24:Requires-Dist: black; extra == "dev"
25:Requires-Dist: mock; extra == "dev"
26:Requires-Dist: pytest; extra == "dev"
$ pip index versions py-vapid
WARNING: pip index is currently an experimental command. It may be removed/changed in a future release without prior warning.
py-vapid (1.9.6)
Available versions: 1.9.6, 1.9.5, 1.9.4, 1.9.2, 1.9.1, 1.9.0, 1.8.2, 1.8.1, 1.8.0, 1.7.1, 1.7.0, 1.6.0, 1.5.0, 1.4.0, 1.3.1, 1.3.0, 1.2.6, 1.2.5, 1.2.4, 1.2.3, 1.2.2, 1.2.1, 1.2.0, 1.1.0, 0.8.1, 0.8.0, 0.7.1, 0.7.0, 0.6.0, 0.5.0, 0.4.1, 0.4, 0.2, 0.3.linux-x86_64
$ pip index versions http-ece
WARNING: pip index is currently an experimental command. It may be removed/changed in a future release without prior warning.
http-ece (1.2.1)
Available versions: 1.2.1, 1.2.0, 1.1.0, 1.0.5, 1.0.4, 1.0.2, 1.0.1, 1.0.0, 0.7.3, 0.7.2, 0.7.1, 0.7.0, 0.6.5, 0.5.0, 0.4.5, 0.4.4, 0.4.3, 0.4.1, 0.4.0, 0.2.0, 0.6.4.linux-x86_64, 0.6.3.linux-x86_64, 0.6.2.linux-x86_64, 0.6.1.linux-x86_64, 0.6.0.linux-x86_64, 0.4.0.linux-x86_64, 0.2.0.cygwin-2.2.1-x86_64

## R11
$ ls -la frontend/public
total 448
drwxr-xr-x  5 root root   4096 Nov  2 00:34 .
drwxr-xr-x 10 root root   4096 Nov  2 00:34 ..
-rw-r--r--  1 root root  44563 Nov  2 00:34 apple-touch-icon.png
drwxr-xr-x  2 root root   4096 Nov  2 00:34 brand-icons
-rw-r--r--  1 root root  31629 Nov  2 00:34 favicon.png
-rw-r--r--  1 root root    298 Nov  2 00:34 favicon.svg
drwxr-xr-x  3 root root   4096 Nov  2 00:34 images
-rw-r--r--  1 root root  63203 Nov  2 00:34 logo.png
-rw-r--r--  1 root root 288337 Nov  2 00:34 og-image.png
drwxr-xr-x  2 root root   4096 Nov  2 00:34 templates
$ cat -n frontend/index.html
     1	<!doctype html>
     2	<html lang="en">
     3	  <head>
     4	    <meta charset="UTF-8" />
     5	    <link rel="icon" type="image/png" href="/favicon.png" />
     6	    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
     7	    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
     8	    <meta name="robots" content="noindex, nofollow" />
     9	    <meta name="description" content="Sales Anchor — TCG 輸出業者のための B2B Sales CRM & Intelligence Platform" />
    10	    <meta property="og:title" content="Sales Anchor" />
    11	    <meta property="og:description" content="Sales Anchor — TCG 輸出業者のための B2B Sales CRM & Intelligence Platform" />
    12	    <meta property="og:image" content="/og-image.png" />
    13	    <meta property="og:type" content="website" />
    14	    <meta name="twitter:card" content="summary_large_image" />
    15	    <meta name="twitter:image" content="/og-image.png" />
    16	    <title>Sales Anchor</title>
    17	  </head>
    18	  <body>
    19	    <div id="root"></div>
    20	    <script type="module" src="/src/main.tsx"></script>
    21	  </body>
    22	</html>
$ git grep -n -i 'serviceWorker\|manifest\|webpush\|PushManager\|vite-plugin-pwa' -- frontend/src frontend/index.html frontend/vite.config.ts frontend/package.json
frontend/vite.config.ts:19:    // 閲覧ページ(/viewer/)は本体と別の入口。manifest はここに書かない（CI のビルドでだけ --manifest を付ける）。
(exit=0)

## R12
$ ls -d nginx frontend/nginx* frontend/Dockerfile*
frontend/Dockerfile
frontend/nginx.conf
nginx
$ git grep -n -i 'Content-Security-Policy\|worker-src\|Service-Worker\|location = /sw\|webmanifest\|try_files\|add_header Cache-Control' -- nginx frontend/nginx* frontend/Dockerfile*
frontend/nginx.conf:18:        add_header Cache-Control "no-cache, must-revalidate";
frontend/nginx.conf:19:        try_files $uri =404;
frontend/nginx.conf:29:        add_header Cache-Control "no-cache, must-revalidate";
frontend/nginx.conf:30:        try_files $uri =404;
frontend/nginx.conf:33:        add_header Cache-Control "no-cache, must-revalidate";
frontend/nginx.conf:34:        try_files /viewer/index.html =404;
frontend/nginx.conf:41:        add_header Cache-Control "public, max-age=31536000, immutable";
frontend/nginx.conf:42:        try_files $uri =404;
frontend/nginx.conf:47:        try_files $uri $uri/ /index.html;
nginx/nginx.conf:96:    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
nginx/nginx.conf:257:        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:;" always;
nginx/nginx.conf:299:        try_files $uri $uri/ =404;
nginx/nginx.conf:303:        add_header Cache-Control "no-store, no-cache" always;
nginx/nginx.conf:363:    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
nginx/nginx.conf:582:    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
nginx/nginx.conf:788:        try_files $uri $uri/ /privacy/index.html;
nginx/nginx.conf:792:        try_files $uri $uri/ /terms/index.html;
nginx/nginx.conf:796:        try_files $uri $uri/ /data-deletion/index.html;
nginx/nginx.conf:802:        try_files $uri $uri/ =404;
(exit=0)

## R13
$ cat -n frontend/src/pages/account-settings/SecuritySection.tsx
     1	import { useCallback, useEffect, useState, FormEvent } from "react";
     2	import { useTranslation } from "react-i18next";
     3	import {
     4	  EmailAuthProvider,
     5	  reauthenticateWithCredential,
     6	  updatePassword,
     7	} from "../../lib/firebase-auth";
     8	import { auth } from "../../lib/firebase";
     9	import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
    10	import { authErrorMessage } from "../../lib/auth/authErrorMessage";
    11	import { isSelfAuth } from "../../lib/auth/provider";
    12	import { adoptAccessToken } from "../../lib/auth/selfAuth";
    13	import { api } from "../../lib/api";
    14	import { ACCOUNT_ICONS } from "../../constants/icons";
    15	import { ICON } from "../../constants/iconSizes";
    16	import { Badge } from "../../components/Badge";
    17	import { Button } from "../../components/Button";
    18	import ConfirmModal from "../../components/ConfirmModal";
    19	import { DataTable, type DataTableColumn } from "../../components/DataTable";
    20	import { Modal } from "../../components/Modal";
    21	import { Stack } from "../../components/Stack";
    22	import { TextFieldControl } from "../../components/TextField";
    23	import PasskeySection from "./PasskeySection";
    24	
    25	interface DeviceItem {
    26	  id: number;
    27	  label: string;
    28	  location: string | null;
    29	  created_via: string;
    30	  created_at: string | null;
    31	  last_used_at: string | null;
    32	  is_current: boolean;
    33	}
    34	
    35	/** ログインしている機械の一覧と、その機械のログアウト（ADR-1055・K8） */
    36	function DevicesSection() {
    37	  const { t, i18n } = useTranslation();
    38	  const [items, setItems] = useState<DeviceItem[]>([]);
    39	  const [pendingRemove, setPendingRemove] = useState<DeviceItem | null>(null);
    40	  const [removing, setRemoving] = useState(false);
    41	  const [error, setError] = useState("");
    42	
    43	  const load = useCallback(async () => {
    44	    try {
    45	      const res = await api.get<{ items: DeviceItem[] }>("/auth/devices");
    46	      setItems(res.items);
    47	    } catch (err) {
    48	      setError(authErrorMessage(err, t, "login"));
    49	    }
    50	  }, [t]);
    51	
    52	  useEffect(() => {
    53	    void load();
    54	  }, [load]);
    55	
    56	  const handleRemove = async () => {
    57	    if (!pendingRemove) return;
    58	    setError("");
    59	    setRemoving(true);
    60	    try {
    61	      await api.delete("/auth/devices/" + pendingRemove.id);
    62	      setPendingRemove(null);
    63	      await load();
    64	    } catch (err) {
    65	      setPendingRemove(null);
    66	      setError(authErrorMessage(err, t, "login"));
    67	    } finally {
    68	      setRemoving(false);
    69	    }
    70	  };
    71	
    72	  const formatDate = (value: string) => new Date(value).toLocaleString(i18n.language);
    73	
    74	  const columns: DataTableColumn<DeviceItem>[] = [
    75	    {
    76	      key: "label",
    77	      header: t("accountSettings.devices.colLabel"),
    78	      renderCell: (row) => (
    79	        <>
    80	          {row.label}
    81	          {row.is_current && (
    82	            <Badge variant="info" size="sm">
    83	              {t("accountSettings.devices.current")}
    84	            </Badge>
    85	          )}
    86	        </>
    87	      ),
    88	    },
    89	    {
    90	      key: "location",
    91	      header: t("accountSettings.devices.colLocation"),
    92	      renderCell: (row) => row.location ?? t("accountSettings.devices.unknown"),
    93	    },
    94	    {
    95	      key: "last_used_at",
    96	      header: t("accountSettings.devices.colLastUsed"),
    97	      renderCell: (row) => (row.last_used_at ? formatDate(row.last_used_at) : ""),
    98	    },
    99	    {
   100	      key: "actions",
   101	      header: "",
   102	      renderCell: (row) => (
   103	        <Button type="button" variant="danger" size="sm" onClick={() => setPendingRemove(row)}>
   104	          {t("accountSettings.devices.remove")}
   105	        </Button>
   106	      ),
   107	    },
   108	  ];
   109	
   110	  return (
   111	    <section className="account-settings-section">
   112	      <div className="account-settings-section-title">
   113	        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
   114	        {t("accountSettings.devices.title")}
   115	      </div>
   116	      <p>{t("accountSettings.devices.description")}</p>
   117	      <Stack gap="4">
   118	        <DataTable<DeviceItem>
   119	          columns={columns}
   120	          data={items}
   121	          rowKey={(row) => String(row.id)}
   122	          emptyState={t("accountSettings.devices.empty")}
   123	          mobileCards
   124	        />
   125	        <p>{t("accountSettings.devices.geoipCredit")}</p>
   126	        {error && <div className="error-message">{error}</div>}
   127	      </Stack>
   128	      <ConfirmModal
   129	        open={pendingRemove !== null}
   130	        danger
   131	        title={t("accountSettings.devices.removeTitle")}
   132	        message={t("accountSettings.devices.removeMessage")}
   133	        confirmLabel={t("accountSettings.devices.remove")}
   134	        confirmLoading={removing}
   135	        onConfirm={() => void handleRemove()}
   136	        onCancel={() => setPendingRemove(null)}
   137	      />
   138	    </section>
   139	  );
   140	}
   141	
   142	/** 予備の合言葉の残り数と作り直し。10個は作ったときに1回だけ見せる（ADR-1055・D14） */
   143	function RecoveryCodesSection() {
   144	  const { t } = useTranslation();
   145	  const [remaining, setRemaining] = useState<number | null>(null);
   146	  const [confirmOpen, setConfirmOpen] = useState(false);
   147	  const [busy, setBusy] = useState(false);
   148	  const [codes, setCodes] = useState<string[] | null>(null);
   149	  const [copied, setCopied] = useState(false);
   150	  const [error, setError] = useState("");
   151	
   152	  const load = useCallback(async () => {
   153	    try {
   154	      const res = await api.get<{ remaining: number }>("/auth/recovery-codes/status");
   155	      setRemaining(res.remaining);
   156	    } catch (err) {
   157	      setError(authErrorMessage(err, t, "login"));
   158	    }
   159	  }, [t]);
   160	
   161	  useEffect(() => {
   162	    void load();
   163	  }, [load]);
   164	
   165	  const handleCreate = async () => {
   166	    setError("");
   167	    setBusy(true);
   168	    try {
   169	      const res = await api.post<{ codes: string[] }>("/auth/recovery-codes", {});
   170	      setConfirmOpen(false);
   171	      setCodes(res.codes);
   172	      await load();
   173	    } catch (err) {
   174	      setConfirmOpen(false);
   175	      setError(authErrorMessage(err, t, "login"));
   176	    } finally {
   177	      setBusy(false);
   178	    }
   179	  };
   180	
   181	  const handleCopy = async () => {
   182	    if (!codes) return;
   183	    try {
   184	      await navigator.clipboard.writeText(codes.join("\n"));
   185	      setCopied(true);
   186	    } catch {
   187	      // コピーできなくても、画面の10個を書き留められる
   188	    }
   189	  };
   190	
   191	  const closeShown = () => {
   192	    setCodes(null);
   193	    setCopied(false);
   194	  };
   195	
   196	  return (
   197	    <section className="account-settings-section">
   198	      <div className="account-settings-section-title">
   199	        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
   200	        {t("accountSettings.recoveryCodes.title")}
   201	      </div>
   202	      <p>{t("accountSettings.recoveryCodes.description")}</p>
   203	      <Stack gap="3">
   204	        {remaining !== null && <p>{t("accountSettings.recoveryCodes.remaining", { count: remaining })}</p>}
   205	        {error && <div className="error-message">{error}</div>}
   206	        <Button type="button" variant="secondary" disabled={busy} onClick={() => setConfirmOpen(true)}>
   207	          {t("accountSettings.recoveryCodes.regenerate")}
   208	        </Button>
   209	      </Stack>
   210	      <ConfirmModal
   211	        open={confirmOpen}
   212	        title={t("accountSettings.recoveryCodes.regenerateTitle")}
   213	        message={t("accountSettings.recoveryCodes.regenerateMessage")}
   214	        confirmLabel={t("accountSettings.recoveryCodes.regenerate")}
   215	        confirmLoading={busy}
   216	        onConfirm={() => void handleCreate()}
   217	        onCancel={() => setConfirmOpen(false)}
   218	      />
   219	      <Modal
   220	        open={codes !== null}
   221	        size="sm"
   222	        title={t("accountSettings.recoveryCodes.shownTitle")}
   223	        onClose={closeShown}
   224	        footer={
   225	          <>
   226	            <Button variant="secondary" onClick={() => void handleCopy()}>
   227	              {t(copied ? "accountSettings.recoveryCodes.copied" : "accountSettings.recoveryCodes.copy")}
   228	            </Button>
   229	            <Button variant="primary" onClick={closeShown}>
   230	              {t("common.close")}
   231	            </Button>
   232	          </>
   233	        }
   234	      >
   235	        <p>{t("accountSettings.recoveryCodes.shownBody")}</p>
   236	        <ul>
   237	          {(codes ?? []).map((code) => (
   238	            <li key={code}>{code}</li>
   239	          ))}
   240	        </ul>
   241	      </Modal>
   242	    </section>
   243	  );
   244	}
   245	
   246	export default function SecuritySection() {
   247	  const { t } = useTranslation();
   248	  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
   249	  const [changing, setChanging] = useState(false);
   250	  const [success, setSuccess] = useState(false);
   251	  const [error, setError] = useState("");
   252	
   253	  const handleSubmit = async (e: FormEvent) => {
   254	    e.preventDefault();
   255	    setError(""); setSuccess(false);
   256	
   257	    if (form.next !== form.confirm) {
   258	      setError(t("accountSettings.passwordMismatch"));
   259	      return;
   260	    }
   261	    const selfMode = isSelfAuth();
   262	    // 自社ログインの長さ・よく使われるパスワードの決まりは backend が判定する（422 の識別子を文言にする）
   263	    if (!selfMode && form.next.length < 8) {
   264	      setError(t("accountSettings.passwordTooShort"));
   265	      return;
   266	    }
   267	
   268	    if (selfMode) {
   269	      setChanging(true);
   270	      try {
   271	        const res = await api.post<{ access_token?: string | null; expires_in?: number | null }>(
   272	          "/auth/password/change",
   273	          { current_password: form.current, new_password: form.next },
   274	        );
   275	        // 他の端末の更新用トークンは失効するので、今の端末は応答の新しいトークンに入れ替える
   276	        if (res.access_token && res.expires_in) adoptAccessToken(res.access_token, res.expires_in);
   277	        setSuccess(true);
   278	        setForm({ current: "", next: "", confirm: "" });
   279	      } catch (err) {
   280	        setError(authErrorMessage(err, t, "passwordChange"));
   281	      } finally {
   282	        setChanging(false);
   283	      }
   284	      return;
   285	    }
   286	
   287	    const user = auth.currentUser;
   288	    if (!user || !user.email) {
   289	      setError(t("firebaseError.default"));
   290	      return;
   291	    }
   292	
   293	    setChanging(true);
   294	    try {
   295	      const cred = EmailAuthProvider.credential(user.email, form.current);
   296	      await reauthenticateWithCredential(user as never, cred as never);
   297	      await updatePassword(user as never, form.next);
   298	      setSuccess(true);
   299	      setForm({ current: "", next: "", confirm: "" });
   300	    } catch (err) {
   301	      setError(firebaseErrorMessage(err, t));
   302	    } finally {
   303	      setChanging(false);
   304	    }
   305	  };
   306	
   307	  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
   308	    setForm((prev) => ({ ...prev, [k]: e.target.value }));
   309	
   310	  return (
   311	    <>
   312	    <section className="account-settings-section">
   313	      <div className="account-settings-section-title">
   314	        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
   315	        {t("accountSettings.sectionSecurity")}
   316	      </div>
   317	
   318	      <form onSubmit={handleSubmit}>
   319	        <div className="form-group">
   320	          <label htmlFor="current_password">{t("accountSettings.currentPassword")}</label>
   321	          <TextFieldControl
   322	            id="current_password"
   323	            type="password"
   324	            value={form.current}
   325	            onChange={set("current")}
   326	            autoComplete="current-password"
   327	            required
   328	          />
   329	        </div>
   330	
   331	        <div className="form-group">
   332	          <label htmlFor="new_password">{t("accountSettings.newPassword")}</label>
   333	          <TextFieldControl
   334	            id="new_password"
   335	            type="password"
   336	            value={form.next}
   337	            onChange={set("next")}
   338	            autoComplete="new-password"
   339	            required
   340	          />
   341	        </div>
   342	
   343	        <div className="form-group">
   344	          <label htmlFor="confirm_password">{t("accountSettings.confirmPassword")}</label>
   345	          <TextFieldControl
   346	            id="confirm_password"
   347	            type="password"
   348	            value={form.confirm}
   349	            onChange={set("confirm")}
   350	            autoComplete="new-password"
   351	            required
   352	          />
   353	        </div>
   354	
   355	        {error && <div className="error-message">{error}</div>}
   356	        {success && <div className="account-settings-success">{t("accountSettings.passwordChanged")}</div>}
   357	
   358	        <div className="account-settings-actions">
   359	          <Button loading={changing} variant="primary" size="md" type="submit" disabled={changing}>
   360	            {t("accountSettings.changePassword")}
   361	          </Button>
   362	        </div>
   363	      </form>
   364	    </section>
   365	    {isSelfAuth() && <DevicesSection />}
   366	    {isSelfAuth() && <RecoveryCodesSection />}
   367	    {isSelfAuth() && <PasskeySection />}
   368	    </>
   369	  );
   370	}
$ grep -n "export\|Props\|interface\|type " frontend/src/components/Toggle.tsx
12:export interface ToggleProps {
21:export const Toggle = forwardRef<HTMLInputElement, ToggleProps>(function Toggle(
$ wc -l frontend/src/features/auth/LoginApprovalWatcher.tsx
171 frontend/src/features/auth/LoginApprovalWatcher.tsx
$ grep -n "^import" frontend/src/features/auth/LoginApprovalWatcher.tsx
6:import { useCallback, useEffect, useRef, useState } from "react";
7:import { useTranslation } from "react-i18next";
8:import { Link } from "react-router-dom";
9:import { Button } from "../../components/Button";
10:import { Modal } from "../../components/Modal";
11:import { Stack } from "../../components/Stack";
12:import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
13:import { api } from "../../lib/api";
14:import { isSelfAuth } from "../../lib/auth/provider";
15:import { TOPICS } from "../../lib/realtime/topics";
$ grep -n "\"devices\"" frontend/src/locales/ja.json
3326:    "devices": {
$ sed -n 3296,3356p frontend/src/locales/ja.json
3296:    "passkeyDescription": "この端末の顔認証・指紋認証でログインできるようにします。顔や指紋のデータは端末から出ません。",
3297:    "passkeyLabel": "名前（例: 仕事用iPhone）",
3298:    "passkeyAdd": "この端末を登録",
3299:    "passkeyAdded": "登録しました。",
3300:    "passkeyColName": "名前",
3301:    "passkeyColCreated": "登録日",
3302:    "passkeyColLastUsed": "最後に使った日",
3303:    "passkeyUnnamed": "名前なし",
3304:    "passkeyNeverUsed": "まだ使っていません",
3305:    "passkeyEmpty": "登録されたパスキーはありません。",
3306:    "passkeyDelete": "削除",
3307:    "passkeyDeleteTitle": "パスキーを削除しますか",
3308:    "passkeyDeleteMessage": "削除すると、この端末の顔・指紋ではログインできなくなります。パスワードでのログインはそのまま使えます。",
3309:    "passkeyUnsupported": "この端末・ブラウザはパスキーに対応していません。",
3310:    "sectionPreferences": "環境設定",
3311:    "darkModeLabel": "ダークモード",
3312:    "languageLabel": "言語",
3313:    "avatarLabel": "アイコン",
3314:    "avatarChoose": "画像を選ぶ",
3315:    "avatarChange": "画像を変更",
3316:    "avatarRemove": "削除",
3317:    "avatarUploading": "保存中...",
3318:    "avatarHint": "2MB以下のJPG・PNG・WebP。Discordの返信に表示されます。",
3319:    "avatarAlt": "アイコン",
3320:    "avatarErrorInvalid": "2MB以下のJPG・PNG・WebP画像を選んでください。",
3321:    "avatarErrorInvalidAction": "画像を選び直す",
3322:    "avatarErrorSave": "画像を保存できませんでした。",
3323:    "avatarErrorSaveAction": "もう一度試す",
3324:    "englishNameHelp": "Discordで返信するときの表示名に使います。名（英語）は返信者として顧客に表示されます。",
3325:    "englishNameRequired": "英語の名前（姓・名）を入力してください。Discordで返信するときに必要です。",
3326:    "devices": {
3327:      "title": "ログインしている機械",
3328:      "description": "あなたのアカウントにログインしている機械の一覧です。心当たりのない機械はログアウトさせてください。",
3329:      "colLabel": "機械",
3330:      "colLocation": "場所の目安",
3331:      "colLastUsed": "最後に使った日時",
3332:      "current": "この機械",
3333:      "unknown": "不明",
3334:      "remove": "ログアウト",
3335:      "removeTitle": "この機械をログアウトしますか",
3336:      "removeMessage": "この機械は、次に使うときにもう一度許可が必要になります。",
3337:      "empty": "機械はありません。",
3338:      "geoipCredit": "場所の目安は IP Geolocation by DB-IP による推定です。"
3339:    },
3340:    "recoveryCodes": {
3341:      "title": "予備の合言葉",
3342:      "description": "いつもの機械が手元に無いときに、新しい機械でログインするための合言葉です。",
3343:      "remaining": "残り {{count}} 個",
3344:      "regenerate": "作り直す",
3345:      "regenerateTitle": "予備の合言葉を作り直しますか",
3346:      "regenerateMessage": "今ある未使用の合言葉は使えなくなります。新しい10個は作ったときに1回だけ表示されます。",
3347:      "shownTitle": "予備の合言葉",
3348:      "shownBody": "この10個は今しか表示されません。安全な場所に控えてください。",
3349:      "copy": "コピー",
3350:      "copied": "コピーしました",
3351:      "promptTitle": "予備の合言葉を作りませんか",
3352:      "promptBody": "いつもの機械が使えなくなったときに備えて、予備の合言葉を作っておくことをおすすめします。",
3353:      "promptCreate": "作る",
3354:      "promptLater": "あとで"
3355:    }
3356:  },

## R14
$ grep -n 'def send_new_device_mail' backend/app/services/auth_mail.py
164:def send_new_device_mail(
$ sed -n 164,194p backend/app/services/auth_mail.py
def send_new_device_mail(
    to_addr: str, *, when: str, device: str, location: str | None, note: str | None = None
) -> None:
    """新しい機械からのログインの知らせ（ADR-1055 K2）。BackgroundTasks から呼ぶ同期関数。

    リンクを入れない。パスワード・番号・Cookie の値は入れない。失敗しても外に出さずログに残す。
    """
    settings = smtp_settings()
    if settings is None:
        logger.info("[auth_mail] SMTP not configured, skipping new device mail")
        return
    try:
        body = _NEW_DEVICE_BODY.format(
            when=when,
            device=device,
            location=location or "不明 / unknown",
            note=(note + "\n") if note else "",
            geo_credit=GEO_CREDIT if location else "",
        )
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.mail_from
        msg["To"] = to_addr
        msg["Subject"] = NEW_DEVICE_SUBJECT
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.user, settings.password)
            smtp.send_message(msg)
        logger.info("[auth_mail] new device mail sent (to=%s)", _mask_addr(to_addr))
    except Exception as e:  # noqa: BLE001
        logger.error("[auth_mail] new device mail failed (to=%s): %s", _mask_addr(to_addr), type(e).__name__)
$ grep -n auth_login_requests backend/app/tasks/maintenance.py
273:                "DELETE FROM public.auth_login_requests "
313:                "UPDATE public.auth_login_requests SET status = 'expired', decided_at = NOW() "
$ grep -n "def test_" backend/tests/test_new_device_approval.py
229:async def test_a2_off_login_is_unchanged_but_carries_sid(machine, db_session, password_hash):
250:async def test_a2_off_unknown_cookie_machine_is_not_stopped(machine, db_session, password_hash):
260:async def test_k1_unknown_machine_gets_202_without_tokens(enforce, machine, db_session, password_hash, spies):
289:async def test_k1_pending_cookie_value_is_not_stored_raw(enforce, machine, db_session, password_hash):
300:async def test_request_limit_is_5_per_hour(enforce, machine, db_session, password_hash):
314:async def test_d5_first_login_registers_first_trusted_device(enforce, machine, db_session, password_hash, spies):
334:async def test_d5_known_user_with_no_device_is_not_first_login(enforce, machine, db_session, password_hash):
339:async def test_d5_never_logged_in_but_has_device_row_is_stopped(enforce, machine, db_session, password_hash):
355:async def test_k2_request_publishes_to_user_and_sends_one_mail(enforce, machine, db_session, password_hash, spies):
371:def test_k2_hub_delivers_user_channel_only_to_that_user():
384:async def test_k2_publish_user_change_uses_user_channel_and_minimal_payload():
398:def test_k2_mail_has_no_link_and_includes_time_device_location():
424:async def test_k3_correct_number_approves_and_waiting_machine_gets_tokens(enforce, machine, db_session, password_hash):
453:async def test_k3_poll_twice_issues_only_once(enforce, machine, db_session, password_hash):
467:async def test_k3_other_users_request_is_404_and_unchanged(enforce, machine, db_session, password_hash):
483:async def test_k3_token_without_sid_is_403(enforce, machine, db_session, password_hash):
494:async def test_k3_revoked_device_session_cannot_approve(enforce, machine, db_session, password_hash):
506:async def test_d1_wrong_number_rejects_only_that_request_and_logs_nobody_out(enforce, machine, db_session, password_hash):
523:async def test_k3_expired_request_poll_returns_expired(enforce, machine, db_session, password_hash):
537:async def test_k4_reject_revokes_other_sessions_and_keeps_current(enforce, machine, db_session, password_hash):
557:async def test_k4_approve_after_reject_is_404(enforce, machine, db_session, password_hash):
578:async def test_d4_family_before_cutoff_is_bootstrapped_on_refresh(machine, db_session, password_hash, monkeypatch):
597:async def test_d4_family_created_exactly_at_cutoff_is_401(machine, db_session, password_hash, monkeypatch):
610:async def test_d4_without_cutoff_enforce_refresh_of_deviceless_family_is_401(machine, db_session, password_hash, monkeypatch):
618:async def test_a2_off_refresh_of_deviceless_family_still_works(machine, db_session, password_hash):
629:async def test_refresh_of_revoked_device_family_is_401(enforce, machine, db_session, password_hash):
639:def test_k6_code_format_normalize_and_aliases():
649:async def test_k6_generate_10_hashed_codes_and_use_once(enforce, machine, db_session, password_hash):
683:async def test_k6_regenerate_revokes_old_unused_codes(enforce, machine, db_session, password_hash):
696:async def test_k6_five_wrong_codes_reject_the_request(enforce, machine, db_session, password_hash):
709:async def test_k6_recovery_without_pending_cookie_is_400(enforce, machine, db_session, password_hash):
723:async def test_k7_admin_approves_and_waiting_machine_gets_in(enforce, machine, db_session, password_hash):
751:async def test_k7_admin_guards(enforce, machine, db_session, password_hash):
770:async def test_k7_admin_cannot_approve_own_request(enforce, machine, db_session, password_hash):
784:async def test_k8_list_and_revoke_device(enforce, machine, db_session, password_hash):
809:async def test_k8_other_users_device_is_404(enforce, machine, db_session, password_hash):
824:async def test_k9_events_have_user_reason_and_no_secrets(enforce, machine, db_session, password_hash):
841:async def test_k9_login_success_records_user_and_is_new_device(machine, db_session, password_hash):
851:async def test_k9_known_device_login_records_not_new_device(enforce, machine, db_session, password_hash):
862:async def test_k9_middleware_reads_request_state_set_inside_the_route():
897:async def test_d8_revoke_user_sessions_returns_families_and_keeps_excluded(enforce, machine, db_session, password_hash):
910:async def test_d8_family_revoked_marker_uses_key_and_ttl():
924:async def test_d8_redis_down_fails_open():
932:async def test_d8_password_reset_confirm_revokes_all_families(enforce, machine, db_session, password_hash):
971:async def test_password_change_off_issues_family_without_device_and_accepts_sidless_token(machine, db_session, password_hash):
996:async def test_password_change_enforce_inherits_device(enforce, machine, db_session, password_hash):
1009:async def test_password_change_enforce_sidless_token_is_403_and_password_unchanged(enforce, machine, db_session, password_hash):
1020:async def test_password_change_enforce_deviceless_family_after_cutoff_is_403(machine, db_session, password_hash, monkeypatch):
1035:async def test_password_change_enforce_deviceless_family_before_cutoff_registers_bootstrap(machine, db_session, password_hash, monkeypatch):
1064:def test_describe_user_agent(ua, expected):
1068:def test_geo_lookup_returns_none_without_database(monkeypatch):
1078:def test_bootstrap_cutoff_parsing(monkeypatch):
1086:def test_device_approval_mode_defaults_to_off(monkeypatch):
$ grep -n 'monkeypatch\|send_new_device_mail' backend/tests/test_new_device_approval.py
78:def base_env(monkeypatch):
79:    monkeypatch.setenv("AUTH_PROVIDER", "self")
80:    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
81:    monkeypatch.delenv("AUTH_JWT_SECRET_PREVIOUS", raising=False)
82:    monkeypatch.delenv("AUTH_RP_ORIGIN", raising=False)
83:    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
84:    monkeypatch.delenv("AUTH_DEVICE_APPROVAL", raising=False)
85:    monkeypatch.delenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", raising=False)
86:    monkeypatch.setenv("GEOIP_DB_PATH", "")
90:def enforce(monkeypatch):
91:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
112:         patch("app.routers.auth.send_new_device_mail", new=mail), \
413:        auth_mail.send_new_device_mail("to@example.com", when="2026-11-01 10:00", device="iPhone・Safari", location="Tokyo, Japan")
578:async def test_d4_family_before_cutoff_is_bootstrapped_on_refresh(machine, db_session, password_hash, monkeypatch):
581:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
582:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (created + timedelta(seconds=1)).isoformat())
597:async def test_d4_family_created_exactly_at_cutoff_is_401(machine, db_session, password_hash, monkeypatch):
600:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
601:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", created.isoformat())
610:async def test_d4_without_cutoff_enforce_refresh_of_deviceless_family_is_401(machine, db_session, password_hash, monkeypatch):
613:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
1020:async def test_password_change_enforce_deviceless_family_after_cutoff_is_403(machine, db_session, password_hash, monkeypatch):
1024:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
1025:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2020-01-01T00:00:00+00:00")
1035:async def test_password_change_enforce_deviceless_family_before_cutoff_registers_bootstrap(machine, db_session, password_hash, monkeypatch):
1039:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
1040:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
1068:def test_geo_lookup_returns_none_without_database(monkeypatch):
1069:    monkeypatch.setenv("GEOIP_DB_PATH", "")
1071:    monkeypatch.setenv("GEOIP_DB_PATH", "/nonexistent/dbip.mmdb")
1078:def test_bootstrap_cutoff_parsing(monkeypatch):
1080:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2026-11-01T12:00:00Z")
1082:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "garbage")
1086:def test_device_approval_mode_defaults_to_off(monkeypatch):
1088:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "ENFORCE")
1090:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "whatever")

