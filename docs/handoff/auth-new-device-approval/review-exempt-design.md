# Meta 審査用の会社だけの「ログイン確認なし」スイッチ — 設計

この文書は、Meta の審査員が審査用の会社（会社006）のアカウントで、登録していない機械からでもログインできるようにする作り方です。super admin が画面のスイッチで ON と OFF を切り替えます。ほかの会社には、データベースの決まりで使えないようにします。

- 親（あるべき姿）: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)
- 現在地: [review-exempt-recon.md](review-exempt-recon.md)（以下 recon:記号）
- 決定: [ADR-1055](../../adr/ADR-1055-new-device-login-approval.md) の改訂（What 11。2026-11-22 書き直し・提案中）
- 状態: 設計案作成済み（Opus 2026-11-22・PO の条件 2026-11-22 で書き直し）・審査待ち・実装未着手
- 前の版（人ごとに1〜14日の期限を付ける形）は 3回目の審査で合格したが、PO の条件（会社006だけ・画面のスイッチ・ログイン履歴）で作り直した。前の版の審査の記録: [review-exempt-review-opus.md](review-exempt-review-opus.md)

## 1. 目的と PO の条件（PO の言葉）

PO 2026-11-22 の条件（原文の要点をそのまま並べる）:

1. 「会社００６だけに限定した機能として実装する」
2. 「Metaの審査員がログインするときは登録されていない機器からログインがされるので認証で弾かれてログインできないことを防止するために付けた機能として記録すること」
3. 「通常ではセキュリティリスクの穴になる機能のため他のテナントに展開することは禁止」
4. 「審査期間のみとしてsuperadminもしくはあなたがON,OFFの切り替えが行えるようにすること」
5. 「Superadmin以外のユーザーとあなた以外がスイッチにさわれないように保護すること」
6. 「画面上で現在のスイッチのON/OFFが視覚的に判断できて切り替えもトグルで切り替えが可能にすること」
7. 「管理者メニューの利用者管理メニュー内のサブメニューのログインの許可待ちのサブメニューの下にMeta審査用のサブメニューを新たに作成してMeta審査用ページを作成」
8. 「Meta審査用ページの中にはトグルで切り替えるスイッチのON／OFF機能とログイン履歴を残す」
9. 「ログイン履歴はいつ、どのログイン情報でログインがあったか、ログインが成功したのか失敗したのかが見える化されて非エンジニアでも視覚的にログインの試行が合ったかどうか見える化されていること」

奥の目的: Meta の審査を通す。審査員が止まらずに入れるようにする。ほかの会社と人の守りは弱めない。

## 2. KGI（合格の基準）

| # | 基準（○×で判定） | 検証方法 |
|---|---|---|
| K1 | スイッチが ON の間、会社006の人は初めての機械からパスワードだけで入れ、受信箱の画面が開く | 本番: シークレット窓で review@ に入る。試験 `test_meta_review_on_login_gets_tokens` |
| K2 | スイッチを OFF にしたら、同じ操作で「許可を待っています」（202）に戻る | 試験 `test_meta_review_off_returns_202`。本番: OFF の後に同じ手順で 202 を見る |
| K3 | ほかの会社の人は、スイッチが ON でも今までどおり 202 で止まる | 試験 `test_meta_review_other_tenant_still_202`・既存 `backend/tests/test_new_device_approval.py` が全部緑 |
| K4 | 印の無い会社は、データベースの決まりで ON にできない。印を付けられる会社は1社だけ | 試験 `test_meta_review_check_rejects_unmarked_tenant`・`test_meta_review_marker_unique`（PostgreSQL） |
| K5 | スイッチを動かせるのは super admin だけ。ほかの人は 403。会社006の中の super admin の人には効かない | 試験 `test_meta_review_switch_forbidden_for_non_super_admin`・`test_meta_review_not_for_super_admin_user` |
| K6 | ON にしてから14日たつと、何もしなくても OFF に戻る（画面も OFF を出す） | 試験 `test_meta_review_auto_off_after_14_days` |
| K7 | OFF にした後、ログイン中の画面も15分以内に入り直しを求められる | 試験 `test_meta_review_refresh_after_off_401` |
| K8 | ON の間に入った組では、パスキーと予備の合言葉を作れず、ほかの人の機械も許可できない | 試験 `test_meta_review_session_cannot_enroll_passkey`・`test_meta_review_session_cannot_create_recovery_codes`・`test_meta_review_session_prompt_not_auto`（can_auto と show_prompt の両方が偽）・`test_meta_review_session_cannot_approve_tenant_request` |
| K9 | 利用者管理のメニューで「ログインの許可待ち」の下に「Meta審査用」が出て、押すと Meta審査用の画面が開く | フロントの試験 `UserManagementSubMenu.test.tsx`（足す）・`MetaReviewPage.test.tsx`（新規） |
| K10 | 画面で今の ON／OFF が切替スイッチと色の札で分かり、スイッチで切り替えられる（確かめの小窓を出してから） | フロントの試験 `MetaReviewPage.test.tsx`。本番: PO が目で見る |
| K11 | 画面のログイン履歴に、日時（日本時間）・メールアドレス・結果（成功／失敗／許可待ち）・理由・機械が新しい順に出る。成功は緑、失敗は赤の札 | 試験 `test_meta_review_history_lists_attempts`・`MetaReviewPage.test.tsx`。本番: 入った後に1行増えるのを見る |
| K12 | スイッチを動かすたびに、誰がいつ ON／OFF にしたかが会社006の監査記録に残る | 試験 `test_meta_review_switch_audited` |
| K13 | 部品は金型だけ・直書き0件・文字は全部 t() | `ui-governance` と i18n の必須チェックが緑 |

## 3. 作り方（What／How）

### 3-1. データ（SSOT）

置き場は会社の正本 `public.tenants` に列を2つ（会社だけに効く機能なので、会社の行に置く）。新しい表は作らない。

| 列 | 型 | 意味 |
|---|---|---|
| `meta_review_tenant` | `BOOLEAN NOT NULL DEFAULT false` | Meta 審査用の会社の印 |
| `meta_review_login_until` | `TIMESTAMPTZ NULL` | スイッチ。今より後なら ON、NULL か過去なら OFF |

データベースの決まり（PO の条件3「ほかの会社に展開禁止」を機械で守る）:

- `CHECK (meta_review_login_until IS NULL OR meta_review_tenant)` … 印の無い会社は ON にできない。
- `CREATE UNIQUE INDEX ... ON public.tenants ((meta_review_tenant)) WHERE meta_review_tenant` … 印を付けられる会社は1社だけ。
- 会社の行の書き込みは、もともと運営の文脈（`app.is_operator = 'true'`）のときだけ通る（recon:K）。会社の人がアプリから書く道は無い。

ON／OFF の値はこの1列だけに置く。画面・設定ファイル・人の行に写さない。

印を付ける会社は「会社006」だけにする。番号の 6 をプログラムや移行に書かない（数字の直書きをしない）。印は本番のデータの変更として1回だけ付ける（4 の手順）。

### 3-2. 判定の関数（1か所）

`backend/app/auth/devices.py` に足す:

```python
META_REVIEW_MAX_DAYS = 14

def is_meta_review_on(until: datetime | str | None) -> bool:
    """Meta 審査用の会社のスイッチ（ADR-1055 What 11）。期限が今より後のときだけ True。
    SQLite は時刻を文字列で返すので、既存と同じく _as_utc を通してから比べる。"""
    value = self_tokens._as_utc(until)
    return value is not None and value > _now()

async def meta_review_until(db: AsyncSession, user_id: int) -> datetime | str | None:
    """その人に効くスイッチの値。印の会社の人で、super admin でないときだけ値を返す。"""
    return (
        await db.execute(
            text(
                "SELECT t.meta_review_login_until FROM public.users u "
                "JOIN public.tenants t ON t.id = u.tenant_id "
                "WHERE u.id = :id AND t.meta_review_tenant AND NOT u.is_super_admin"
            ),
            {"id": user_id},
        )
    ).scalar_one_or_none()
```

- `_now` は `backend/app/auth/devices.py:78`、`_as_utc` は `backend/app/auth/self_tokens.py:146-154`。
- `public.users`・`public.tenants` の読み取りは、どちらも会社の文脈なしで全行読める（`migrations/20261016_180000_add_users_write_rls.sql:9-10`・`migrations/20261016_170000_add_tenants_write_rls.sql:9-10`）。
- 条件（印の会社・super admin でない）は、この関数1つにだけ書く。ログイン・更新・4つの口は全部これを呼ぶ。

### 3-3. パスワードのログイン

`backend/app/routers/auth.py:438` の `elif`（D5）の前に足す:

```python
        elif devices.is_meta_review_on(await devices.meta_review_until(db, user_row.id)):
            # ADR-1055 What 11: Meta 審査用の会社のスイッチが ON。機械は登録しない（OFF の後に残らない）
            audit_reason, audit_new_device = "meta_review", True
            background_tasks.add_task(
                send_new_device_mail,
                user_row.email,
                when=devices.jst_text(),
                device=devices.describe_user_agent(request.headers.get("user-agent")),
                location=geo.lookup(ip),
                note="Meta 審査用のスイッチが ON のためログインしました。 / Signed in while the Meta review switch is ON.",
            )
```

- `trusted_device_id` は None のまま。トークンの組に機械は付かない。
- 並びは「いつもの機械 → Meta 審査用のスイッチ → D5 → 許可依頼」。D5 より前に置くのは、一度もログインしていない人でも、最初の機械が180日残る登録（first_login）を作らないため。
- 印の会社でない人は `meta_review_until` が None を返すので、今と1つも変わらない。ただし、その人にも SELECT が1回増える（`backend/app/routers/auth.py:404-405` の SELECT に足さないのは、条件を1か所にまとめるため）。

### 3-4. トークンの更新

`backend/app/routers/auth.py:552-570` を次の形にする（変更前は `elif devices.is_enforced():` の直下が `cutoff = ...` と `if cutoff ...: 登録 / else: 401`）:

```python
    elif devices.is_enforced():
        cutoff = devices.bootstrap_cutoff()
        if devices.is_meta_review_on(await devices.meta_review_until(db, user_id)):
            # ADR-1055 What 11: スイッチが ON の間だけ、機械の無い組の更新を通す
            audit_reason = "meta_review_refresh"
        elif cutoff is not None and rotated.family_created_at is not None and rotated.family_created_at < cutoff:
            ...（今の bootstrap の登録。中身は1字も変えない）
        else:
            ...（今の 401。中身は1字も変えない）
```

- 記録の名前は、ログインは `meta_review`、更新は `meta_review_refresh`（19字・上限50字）に分ける。
- OFF にすると、次の更新（アクセストークンは最長900秒）で今までどおり 401 になる＝K7。

### 3-5. OFF の後に残る入口を作らせない

パスキーのログイン（`backend/app/routers/auth.py:1188-1200`）と予備の合言葉（`backend/app/routers/auth.py:1553-1640`）は、知らない機械でも通す。ON の間にこれを作られると、OFF の後も入れてしまう。パスワードで入った直後は、画面がパスキーを自動で作ろうとする（`frontend/src/pages/login/LoginPage.tsx:151-153`）。

そこで、次の4つの口で「スイッチで入った組」を断る:

| 口 | 変更前 | 変更後 |
|---|---|---|
| `GET /passkey/prompt`（`backend/app/routers/auth.py:939`） | `can_auto`・`show_prompt` を返す（`backend/app/routers/auth.py:954-957`） | `PasskeyPromptStatus(can_auto=False, show_prompt=False)` |
| `POST /passkey/register/options`・`/passkey/register/verify`（`backend/app/routers/auth.py:978`・`:1007`） | 登録できる | 403 `meta_review_session_no_enroll` |
| `POST /recovery-codes`（`backend/app/routers/auth.py:1884`） | 作れる | 403 `meta_review_session_no_enroll` |
| `POST /tenant/login-requests/{id}/approve`（`backend/app/routers/tenant_login_requests.py:68-76`） | 会社のオーナーなら許可できる | 403 `meta_review_session_no_enroll` |

- 判定は devices.py の `async def is_meta_review_session(db, request, user) -> bool` 1つ。中の順:
  1. `is_enforced()` が偽なら False
  2. `is_meta_review_on(await meta_review_until(db, user.id))` が偽なら False
  3. 真のときだけ `resolve_current_session(request, db, user)`（`backend/app/auth/dependencies.py:707-724`）を呼ぶ。sid の無いトークンの 403・組の失効の 401 はそのまま外へ出す（印の会社の人で ON のときだけ起きる）
  4. `trusted_device_id is None` なら True、あれば False
- 4つの口は、どれも `request`・`current_user`・`db` を持っている（前の版の3回目の審査で確かめ済み）。
- 画面の自動作成の道は 403 でも何もしない（今も黙って飛ばす作り）。設定画面から手で作ろうとして 403 になったときは、ADR-1071 の出し方で `auth.error.metaReviewSessionNoEnroll` を出す。文面: 「Meta審査用の入り方では、パスキーと予備の合言葉は作れません。いつもの機械で入り直してから作ってください。」

### 3-6. 触らない場所

- パスワードの変更（`backend/app/routers/auth.py:769-779`）: 今までどおり 403。審査員にパスワードを変えさせない。
- パスキーのログイン・予備の合言葉のログイン: 変えない（作らせないので、使える物が無い）。
- `AUTH_DEVICE_APPROVAL`・deploy.yml・締切: 変えない。

### 3-7. 管理の口（super admin だけ）

新規ファイル backend/app/routers/super_admin_meta_review.py に作り、`backend/app/main.py` の既存の super admin の口と同じ所で読み込む。守りは `require_super_admin`・`require_app_origin`（`backend/app/routers/super_admin_login_requests.py:166-168` と同じ）。

| 口 | 中身 | 断る場合 |
|---|---|---|
| `GET /super-admin/meta-review` | `{tenant_name, is_on, until}`。印の会社が無ければ `tenant_name: null, is_on: false` | super admin でない 403 |
| `PUT /super-admin/meta-review` 本文 `{on: bool}` | ON: `until = 今 + 14日`。OFF: `until = NULL` | super admin でない 403／印の会社が無い 409 `meta_review_tenant_missing` |
| `GET /super-admin/meta-review/logins?limit=100` | ログイン履歴（3-9） | super admin でない 403 |

書き込みの順（会社の表は運営の文脈のときだけ書ける。recon:K）:

1. `set_operator_context(db)`（`backend/app/auth/dependencies.py:458`）
2. `UPDATE public.tenants SET meta_review_login_until = :until WHERE meta_review_tenant RETURNING id, tenant_name`。0行なら rollback して 409 `meta_review_tenant_missing`（黙って成功にしない）
3. `_record_auth_audit(...)`（`backend/app/routers/auth.py:282`。会社は印の会社の id。`event: meta_review_on|meta_review_off`・`until`・操作した人 `user_id=current_user.id`）
4. `db.commit()`
5. `finally: reset_operator_context(db)`（`backend/app/auth/dependencies.py` の set の直後の関数）

- `_record_auth_audit` の中で会社の文脈を付けると `app.is_operator` が空に戻る（`backend/app/auth/dependencies.py:328`）。そのため UPDATE は必ず手順3より前に置く。
- SQLite の試験では文脈が効かないので、PostgreSQL の試験 `test_meta_review_switch_updates_under_rls` を `backend/tests/test_users_rls.py` に置く（3-11）。

「あなた（Opus）」が切り替えるときも、この同じ口だけを使う。PO の Chrome で super admin としてログイン済みの画面を開き、スイッチを押す。データベースを直接書き換える別の道は作らない（書き込みの道を1本にし、監査記録を必ず残すため）。Opus が押すのは、PO がチャットで「ON にして」「OFF にして」と頼んだときだけ。

### 3-8. 画面

| 置き場 | 変更 |
|---|---|
| `frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx:39-45` | 2つ目の組の `login-requests` の下に `{ key: "meta-review", label: t("nav.superAdminMetaReview"), to: "/super-admin/users/meta-review" }` を足す。`:50` の `handleChange` は `login-requests` と同じく `meta-review` でも何もしない。`activeKey` に `"meta-review"` を渡せるよう型を広げる |
| `frontend/src/App.tsx:343-347` の下 | `<Route path="/super-admin/users/meta-review" element={<MetaReviewPage />} />` |
| 新規ファイル frontend/src/pages/super-admin/MetaReviewPage.tsx | 下の画面 |

画面の中身（`frontend/src/pages/super-admin/LoginRequestsPage.tsx:22-58` と同じ枠。`PageLayout`・`hub-shell`・`UserManagementSubMenu`・super admin でなければ `superAdmin.accessDenied`）:

1. スイッチの枠（`SectionCard`）
   - 会社の名前（印の会社の `tenant_name`）
   - `Toggle`（`frontend/src/components/Toggle.tsx`）。`aria-label` は t()
   - 今の状態の札 `Badge`（`frontend/src/components/Badge.tsx`）: ON は `variant="success"` で「ON（審査員はログインできます）」、OFF は `variant="neutral"` で「OFF（ふだんの確認に戻っています）」
   - ON のときは「自動で OFF になる日時: 〇月〇日 〇時〇分（日本時間）」
   - スイッチを押すと `ConfirmModal` で確かめてから PUT する
   - 用途の説明1行（t()）: 「Meta の審査員が登録していない機械から入れるようにする、審査の間だけのスイッチです。ほかの会社では使えません。」
2. ログイン履歴の枠（`SectionCard`＋`DataTable`）
   - 列: 日時（日本時間）・メールアドレス・結果・理由・機械
   - 結果は `Badge`: 成功 `success`／許可待ち `warning`／失敗 `danger`
   - 0件なら `EmptyState`（`frontend/src/components/EmptyState.tsx`）で「まだログインの試行はありません」
   - 30秒ごとに読み直す（審査員が入った瞬間を PO が見られるように）

- 文字は全部 `t()`。キーは `superAdmin.metaReview.*` と `nav.superAdminMetaReview` を ja.json と en.json に同じ数で足す。
- 結果と理由の文字の対応表は画面の中の1か所（`reason` → i18n キー）。色・大きさの直書きはしない（ADR-067・ADR-144）。

### 3-9. ログイン履歴（新しい表は作らない）

記録の正本は既にある `public.auth_events`（`backend/app/middleware/audit.py:215-266` が `/api/v1/auth/` の口で1行ずつ書く。列 `user_id`・`reason`・`is_new_device` は `migrations/20261101_130000_add_new_device_approval.sql:118-120`）。これを読むだけにする。

```sql
SELECT e.created_at, u.email, e.path, e.status_code, e.reason, e.user_agent
FROM public.auth_events e
JOIN public.users u ON u.id = e.user_id
JOIN public.tenants t ON t.id = u.tenant_id
WHERE t.meta_review_tenant
  AND e.path IN ('/api/v1/auth/login', '/api/v1/auth/passkey/login/verify')
ORDER BY e.created_at DESC
LIMIT :limit
```

結果の分け方（画面の札）:

| 条件 | 結果 |
|---|---|
| `status_code` が 200 | 成功 |
| `status_code` が 202 | 許可待ち（`device_approval_required`） |
| それ以外 | 失敗（理由は `reason`: `bad_password`＝パスワード違い・`inactive`・`locked`・`rate_limited` など） |

- 「どのログイン情報で」は、メールアドレスと機械（`describe_user_agent`、`backend/app/auth/devices.py:135`）で出す。パスワードは記録にも画面にも出さない。
- 限界: 会社006に無いメールアドレスで試した回は、記録に人が付かない（`backend/app/routers/auth.py:413` `user_id=None`）。この画面には出ない。打ったメールアドレスを記録に足すことはしない（打ち間違いの他人のアドレスを残さないため）。
- 本番の今の件数: id=10 の行は0件（recon:L）。最初は空の表で始まる。

### 3-10. 印を付ける（本番のデータの変更・1回だけ）

便1 の本番反映の後に、Opus が PO 合意済みの本番データ変更の手順で行う。

```sql
BEGIN;
SET LOCAL app.is_operator = 'true';
UPDATE public.tenants SET meta_review_tenant = true
 WHERE tenant_code = 'tenant-review' AND tenant_name = 'Sales Anchor App Review'
RETURNING id, tenant_code, tenant_name;   -- 1行（id 6）でなければ ROLLBACK
COMMIT;
```

- 先に読み取りで1行（id 6）だけ当たることを確かめる → DRY-RUN（ROLLBACK）→ 1行なら本実行 → 読み取りで確かめる。
- 戻し: `UPDATE public.tenants SET meta_review_login_until = NULL, meta_review_tenant = false WHERE meta_review_tenant`。
- 会社を名前と code の2つで当てる。番号を書かない。

### 3-11. 移行（危ない変更）

- 新規ファイル migrations/20261122_100000_add_tenants_meta_review_switch.sql（`ADD COLUMN IF NOT EXISTS` を2つ・CHECK・部分一意の索引・COMMENT。値の書き込みはしない）。COMMENT には用途と「ほかの会社に広げない（ADR-1055 What 11）」を書く。
- `scripts/run_all_migrations.sh` に1行足す。置き場は `scripts/run_all_migrations.sh:1478` の下・集計の行 `mr_report_summary`（`:1481`）の上。
- 試験用の表にも列を足す: `backend/tests/conftest.py` の tenants 表に2列。
- PostgreSQL の試験の土台にも移行を足す: `backend/tests/test_users_rls.py:47-57` の一覧に `_META_REVIEW_MIGRATION` を足し、`_MUST_CHANGE_MIGRATION`（`:115`）と同じ所で当てる。足さないと、self_login を呼ぶ試験（`backend/tests/test_users_rls.py:401,421,433`）が列が無くて落ちる。
- `backend/app/models.py` の Tenant には足さない（SQL で読むため）。deploy.yml の追記も要らない（`.github/workflows/deploy.yml:276-277`）。
- 列を足すだけで、既存の行は false と NULL＝今と同じ動き。ADR-136 の GO が要る。

## 4. 便の分け方（一度に1つ）

| 便 | 中身 | GO |
|---|---|---|
| 便1 | 3-1〜3-7・3-9 の裏側・3-11（裏側と移行と試験） | 要（移行を含む） |
| 印 | 3-10（本番のデータの変更） | PO 合意済み（2026-11-22 の条件1） |
| 便2 | 3-8（画面） | 画面だけ（CI 緑で可） |

便1 の後は、印も画面も無いので、誰にも効かない。K1・K2・K7・K11 の本番確認は便2 の後に、PO に頼まれて Opus が画面で ON にして行う。

## 5. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| A. 本番の設定を全員 off にする | 全員の守りが外れる |
| B. 人ごとの期限（前の版） | PO の条件1（会社006だけ）と条件6（スイッチ）に合わない。ほかの会社の人にも付けられた |
| C. 会社の番号 6 をプログラムに書く | 数字の直書き。会社を作り直すと番号がずれる。データベースで止められない |
| D. 印の付け方を移行に書く | ADR-155（移行は形だけ）。番号か名前の直書きが移行に残る |
| E. 新しい表を作って履歴を写す | 記録が2か所になる。auth_events が既に全ログインを持つ |
| F. ON を無期限にする | 消し忘れると穴が開いたままになる。14日で自動で戻す（PO の条件4「審査期間のみ」） |

## 6. 弊害と対処

| 弊害 | 対処 |
|---|---|
| パスワードが漏れると ON の間は機械の確認なしで入れる | 会社006だけ・最長14日・入るたびに記録と知らせメール・履歴を画面で見られる |
| OFF の消し忘れ | 14日で自動で OFF（K6） |
| OFF の直後もアクセストークンが最長15分残る | 15分で切れる（K7） |
| 会社006に super admin がいた場合 | その人には効かない（3-2 の条件） |
| 全員のログインで SELECT が1回増える | 主キーでの1行の読み取り。印の会社でなければ値は None |

## 7. 外部・過去事例の参照と我々への応用

- Meta の申請の手引きは、審査員がアプリに入れるテスト用のログイン情報を求める（[submission guide](https://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/app-review/submission-guide)・2026-11-21 閲覧）。→ 審査員の入口は必須。
- 2段階の確認がある口座で審査員が入れず、確認なしの口座で出し直した開発者の報告がある（[Meta 開発者コミュニティ](https://developers.secure.facebook.com/community/threads/442251551600133)）。個人の報告・数値なし。成功の証明には使わない。
- 自社の前例: ADR-1055 の締切と D5 は、例外を「期限と条件で自動で閉じる」形で作った。今回も14日で自動で閉じる。

## 8. 実装カードに渡す試験の一覧

新規ファイル backend/tests/test_meta_review_switch.py に、K1〜K8・K11・K12 の試験名どおりの関数を作る。K4 と書き込みの RLS の試験は `backend/tests/test_users_rls.py` に置く（3-11）。既存の `backend/tests/test_new_device_approval.py` の準備（enforce の setenv・人の作り方）を使う。

## 維持の仕組み

- 守り手: .github/workflows/test.yml（`pytest-run-internal` が新規の試験と `backend/tests/test_new_device_approval.py` を毎回流す）
- 守り手: .github/workflows/migration-test.yml（移行の SQL を毎回流す）
- 守り手: データベースの CHECK と部分一意の索引（印の無い会社は ON にできない・印は1社だけ）
- 対象: ほかの会社に広がらないこと（K3・K4）、OFF で必ず戻ること（K2・K6・K7）、OFF の後に入口を残さないこと（K8）、super admin だけが動かせること（K5）
- まだ無いもの: 審査が終わった後に ON が残っていないかを知らせる定期の見張り（14日で自動で OFF になるので、害は最長14日）
