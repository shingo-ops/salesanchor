# 実装カード: ロール画面の編集の決まり

正本の設計: `docs/handoff/role-edit-hierarchy/design.md`（§4・§5）。迷ったら design を正とし、合わなければ止めて BLOCKED: を返す。

ブランチ: `release/role-edit-hierarchy`（この枝に足す。main へは PR）。作業前に `./scripts/dev/executor-preflight.sh`。

## 手順（この順）

1. `backend/app/auth/system_roles.py`: design §4-1 の定数と compute_permission_keys をそのまま入れる。既存の定数・関数名は変えない。
2. `backend/app/auth/dependencies.py:569-572`: `if is_tenant_admin(...)` を外し、毎回 compute_permission_keys を通す（§4-2）。
3. `backend/app/routers/roles.py`:
   - GET /roles に `scope: Literal["role_page"] | None = Query(None)`。role_page のときは ROLE_PAGE_HIDDEN_KEYS を super admin でも除く（§4-3）。scope 無しの SQL・結果は変えない。
   - PUT /roles/{id}/permissions: §4-4 の 1〜5。is_system と「対象 priority ≥ 自分」の2つの止めは外す（マネージャーがマネージャー自身を直せるため）。
   - GET /roles/{id}/permissions: 対象が ROLE_PAGE_HIDDEN_KEYS なら 404。
   - DELETE / PATCH / PUT /users/{id}/roles: §4-4b の止めを足す。既存の止めは消さない。
4. `backend/app/services/tenant.py`: マネージャーに `"system_key": ROLE_KEY_MANAGER`、permissions から `"roles.view"` を外す（§4-5）。
5. 画面: §4-6 のとおり。i18n は ja/en 両方。新しい部品・色の直書き禁止。
6. 試験:
   - `backend/tests/test_system_roles.py:65-69` を直す。
   - compute_permission_keys の単体試験（owner/admin/manager/その他・roles.* の付け外し）。
   - roles ルーターの HTTP 試験: design §2 K3/K4/K5/K7 の表（4つの役割 × 一覧 scope・権限保存・削除・名前変更・割当）。既存の roles 試験の作り方に合わせる。
   - 画面: `menuPermissions.test.ts`・`rolePermissionRows.test.ts` を新しい固定表示に合わせる。
7. 一度きりのデータ SQL: `docs/handoff/role-edit-hierarchy/data/` に precheck / dryrun / apply / postcheck / rollback と README を、前例 `docs/handoff/roles-system-key-data/` の形で作る（§5 の表の7件＋ roles.* の保存行の削除4行）。`migrations/` には何も足さない（ADR-155）。
8. `docs/adr/ADR-147-common-6roles-standardization.md` に Amendment（2026-11-09）を1節足す: 「ロール画面を開いて直せるのはオーナー・システム管理者・マネージャー（system_key=manager）。画面に出さないのは owner/admin/inspector/smoke」。そのあと `node scripts/generate-adr-index.js`。

## 触らない

- `_visible_role_sql` / `TENANT_HIDDEN_SYSTEM_KEYS` / `staff.py`・スタッフ画面。
- 本番のデータ・SSH。SQL は書くだけで流さない。
- `migrations/`・`deploy.yml`・`.github/`。

## 想定分岐

- テストで `load_user_permissions` の計算が増えて既存試験が落ちた → 落ちた試験名と生出力を返して止める（期待値を勝手に変えない）。ただし「マネージャーの roles.view が保存行から来る」前提の試験は計算から来るよう直してよい。
- roles.* の鍵名が `public.permissions` に無いものがある → 止める。
- 一覧 scope の型で FastAPI が 422 以外を返す → 生出力を返して止める。

## 返し方

DONE / BLOCKED: / NEEDS_DECISION: のどれか。commit と push までして、変えたファイルの一覧と試験の生出力を返す。PR は作らない（Opus が作る）。

## 追加カード2（Opus 審査で見つけた入れ忘れ・2026-11-09）

設計の入れ忘れ: サーバーが返す新しい6つの印（role_not_editable_here ほか）を画面の文に直す表に入れていなかった。今のままだと画面に英字の印がそのまま出る（例: マネージャーがスタッフ画面でマネージャーのロールを付けようとしたとき）。

手順:

1. `frontend/src/lib/apiErrorReason.ts` の `API_ERROR_REASON_KEYS` に下の6行を足す（既存2行の後ろ・この順）。
2. `frontend/src/locales/ja.json` と `en.json` の `apiError` に下の文を足す（文は一字も変えない）。
3. `backend/tests/test_api_error_reason_sync.py` の `test_table_rows_are_read` の期待値に6つを同じ順で足す。
4. `frontend/src/lib/apiErrorReason.test.ts` の最初の試験に `expect(apiErrorReasonKey("role_not_assignable")).toBe("apiError.roleNotAssignable");` を1行足す。
5. 試験: `backend` で `pytest tests/test_api_error_reason_sync.py tests/test_error_detail_guard.py tests/test_roles_edit_hierarchy.py -q`、`frontend` で `npx vitest run src/lib/apiErrorReason.test.ts` と `npx tsc --noEmit -p .`。生出力を `docs/handoff/role-edit-hierarchy/impl-checks-2.txt` に保存。
6. commit・push（同じ枝）。

| 印 | 鍵 | ja | en |
|---|---|---|---|
| role_not_editable_here | apiError.roleNotEditableHere | このロールはロール画面では直せません。直したいときはオーナーに頼んでください。 | This role can't be changed on the Roles page. Ask the owner to change it. |
| role_not_deletable | apiError.roleNotDeletable | このロールは仕組みで使っているため、消せません。使わないときは、人からこのロールを外してください。 | This role is used by the system and can't be deleted. Remove it from people instead. |
| role_permissions_edit_forbidden | apiError.rolePermissionsEditForbidden | ロールの権限を直せるのは、オーナー・システム管理者・マネージャーだけです。直したいときは、この人たちに頼んでください。 | Only the owner, system admin or manager can change role permissions. Ask one of them. |
| role_permissions_not_editable_here | apiError.rolePermissionsNotEditableHere | このロールの権限はロール画面では直せません。直したいときはオーナーに頼んでください。 | This role's permissions can't be changed on the Roles page. Ask the owner to change them. |
| role_page_keys_not_savable | apiError.rolePageKeysNotSavable | ロール画面を開ける人は役割で決まるため、保存できませんでした。画面を開き直してから、もう一度保存してください。 | Who can open the Roles page is set by role, so this was not saved. Reload the page and save again. |
| role_not_assignable | apiError.roleNotAssignable | このロールを付けられるのは、オーナーとシステム管理者だけです。付けたいときはオーナーに頼んでください。 | Only the owner or system admin can give this role. Ask the owner to give it. |

触らない: 上の4ファイルと impl-checks-2.txt 以外。返し方は上と同じ。
