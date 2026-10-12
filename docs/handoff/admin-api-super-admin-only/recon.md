# recon: 会社作成・利用者登録 API を super admin 専用にする

> この文書は何か: 今のコードで「誰が会社を作れるか・誰が利用者を登録できるか」を実コードで確かめた記録。
> 親: [docs/specs/auth-roles/README.md](../../specs/auth-roles/README.md)
> 子: [design.md](design.md)

実測時の基準: 作業ブランチの起点 49acb712f41b53ccbd8ee7cc7c1ebdf8a660bfa7（origin/main の祖先であることを `git merge-base --is-ancestor` で確認）

## 既存 ADR 検索
- `git grep -i "admin/tenants\|auth/register" docs/adr/` の結果: docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md:21 と :50（`POST /auth/register` の再設計・廃止判断は別件と明記）
- `git grep -il require_super_admin docs/adr`: ADR-084, ADR-129, ADR-145（いずれも本件の権限境界を定めた記述ではない）
- 関連する仕様書: docs/specs/auth-roles/README.md（ロールと運営者 super admin の境界）

## 事実
- backend/app/main.py:247-252: admin.router は prefix="/api/v1/admin"、dependencies=[Depends(get_current_tenant), Depends(get_current_admin)] でマウント
- backend/app/auth/dependencies.py:409-418: get_current_admin は current_user.role != "admin" なら 403
- backend/app/auth/dependencies.py:455-483: require_super_admin は getattr(current_user, "is_super_admin", False) が偽なら 403
- backend/app/routers/admin.py:39-43: register_tenant の関数内で role != "admin" を判定
- backend/app/routers/auth.py:43-47: register_user の関数内で role != "admin" を判定
- backend/app/routers/admin.py: @router は POST /tenants の1本のみ（`grep -n "@router"` の結果）
- get_current_admin の使用箇所（`git grep -n get_current_admin -- backend`）: dependencies.py:409（定義）、main.py:12 と :251、super_admin_tenants.py:9（docstring のコメントのみ）
- frontend/src から /admin/tenants と /auth/register を呼ぶ箇所: なし（`git grep` 0件）
- scripts/security_check.sh:137: 未認証で拒否されることだけを確認
- backend/tests/test_security.py に、一般ユーザーのテナント作成が 403 で、detail に「管理者」を含む前提の assert があった
