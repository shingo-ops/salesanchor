# design: 会社作成・利用者登録 API を super admin 専用にする

> この文書は何か: 会社の新規作成と利用者の登録を、運営者（super admin）だけができるようにする変更の設計。
> 親: [docs/specs/auth-roles/README.md](../../specs/auth-roles/README.md)
> recon: [recon.md](recon.md)
> 対象ADR: ADR-023（POST /auth/register の再設計・廃止判断は本件の対象外）

## 目的
POST /api/v1/admin/tenants と POST /api/v1/auth/register を、public.users.is_super_admin = true の人だけが使えるようにする。今は users.role = 'admin' なら通るため、テナントのオーナーが新しい会社を作ったり、他社の tenant_code を指定して利用者を入れたりできる。

## 変更
- backend/app/main.py: admin ルーターの依存を get_current_admin から require_super_admin に替える（get_current_tenant は残す）
- backend/app/routers/admin.py: 引数 current_user を Depends(require_super_admin) にし、関数内の判定を is_super_admin に替える（二重の防御）
- backend/app/routers/auth.py: register_user も同様
- backend/app/auth/dependencies.py: get_current_admin を削除（呼び出し元が無くなるため）
- backend/tests/test_admin_api_super_admin_only.py: 新規。両 API で、非 super admin は 403、super admin は権限判定を通過、未認証は 401/403
- backend/tests/test_security.py: 403 の文言が変わるため assert を「権限」に更新

触らない範囲: calendar、integrations、google_calendar の _require_admin、dependencies.py の救済処理、roles.py（別 PR）。frontend。

## 外部・過去事例の参照と我々への応用
- 該当なし。既存の require_super_admin（super-admin 系ルーターで使用中）をそのまま流用する小規模変更のため。

## 受け入れ基準と検証
|基準|検証方法|
|---|---|
|role='admin' かつ is_super_admin=False は両 API で 403|backend/tests/test_admin_api_super_admin_only.py::test_tenant_admin_without_super_admin_gets_403|
|is_super_admin=True は権限判定を通る（403/401 にならない）|同 test_super_admin_passes_permission_check|
|未認証は 401 または 403|同 test_unauthenticated_is_rejected、既存 backend/tests/test_security.py|
|関数内の判定でも非 super admin を拒否（二重防御）|同 test_register_function_body_rejects_non_super_admin、test_register_tenant_function_body_rejects_non_super_admin|
|get_current_admin の参照が backend に残らない|`git grep -n "def get_current_admin\|import.*get_current_admin" -- backend`が0件|

## 戻し方
このPRを revert する（DB・設定の変更なし）。

## 維持の仕組み
- 守り手: backend/tests/test_admin_api_super_admin_only.py
- 対象: 非 super admin が会社作成・利用者登録を実行できてしまう退行
- 関所なしの場合: 該当なし（上のテストが CI の backend テストで実行される）
