<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ -->
# design — role-ssot-user-roles

この文書は、権限の判定を `user_roles`（system_key）だけに一本化する設計です。

親: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)

**対象ADR**: ADR-147
**recon**: docs/handoff/role-ssot-user-roles/recon.md
**仕様書**: docs/specs/auth-roles/README.md
**日付**: 2026-10-12
**担当**: 設計 Opus／実装 Sonnet

## 目的
テナントのオーナーとシステム管理者（user_roles の system_key が owner / admin）が、カレンダー同期モード・Google カレンダー接続・Google Drive／配送業者／PayPal の連携設定・他人のカレンダー予定の編集削除を行える。それ以外は 403。`users.role` は判定に使わない。目標設定画面が開ける。

## 変更内容
1. `backend/app/auth/system_roles.py` に `is_tenant_admin(system_keys)`。`backend/app/auth/dependencies.py` に `get_user_system_keys(db, user_id)` と FastAPI 依存 `require_tenant_admin`（403 文言は既存の「この操作は管理者のみ実行できます」）。`load_user_permissions` は共有関数を使う。
2. `backend/app/routers/calendar.py`、`backend/app/routers/google_calendar.py`、`backend/app/routers/integrations.py` の `_require_admin` を削除し、`Depends(require_tenant_admin)` に置換。予定の編集削除は「作成者本人 または is_tenant_admin」。
3. `backend/app/auth/dependencies.py` と `backend/app/routers/roles.py` の `users.role` 救済を削除。
4. `/me/permissions` に `user_id` と `is_tenant_admin` を追加（`response_model` が無くスキーマは `{}` のため `frontend/api-contract/openapi.json` に差分なし）。
5. `frontend/src/pages/goal-setting/GoalSettingPage.tsx` の `/auth/me` を `/me/permissions` に置換。`frontend/tests-e2e/goal-setting-advisor.spec.ts` のモックも同じ形に直す。UI 部品・文言・色の追加なし。
6. テスト: `backend/tests/test_tenant_admin_ssot.py`（新規）、`backend/tests/test_google_calendar.py`（旧 `_require_admin` 前提を置換）、`backend/tests/test_roles.py` と `backend/tests/test_roles_hidden_system_admin.py`（救済に依存していたため、user_roles で優先度を付与）、`backend/tests/conftest.py`（client で依存を差し替え）。

## 触らない
`users.role` 列の DDL、migrations、scripts、`staff.role_id`、`backend/app/routers/analytics.py`、担当者列、`get_current_admin` 系（#4162 で扱い済み）、`backend/app/routers/auth.py:79` の書き込み。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1: `users.role` による権限判定が 0 件 | `git grep -n -P "\.role\b.*admin|SELECT role FROM public.users" -- backend/app frontend/src` が 0 件（exit=1） |
| K2: owner / admin は通り、それ以外は 403（`users.role='admin'` でも 403） | `backend/tests/test_tenant_admin_ssot.py`、`backend/tests/test_google_calendar.py` |
| K3: 目標設定画面が `/me/permissions` を呼ぶ | `npx tsc --noEmit` ＋ `frontend/tests-e2e/goal-setting-advisor.spec.ts` のモック |
| K4: 本番 10 人の可否変化は user 9 の不可→可だけ | 本番反映後に読み取りで確認（ロール 0 件の人 0 は recon の事実） |

## 外部・過去事例
該当なし。理由：社内の判定元を一本にするだけで、他社事例に依存する判断が無い。過去事例は #4012（system_key による権限計算）と #4162（admin API の super admin 化）で、本 PR は同じ方向。

## 弊害・戻し方・測り方
- 弊害: ロール 0 件で `users.role='admin'` の人は権限を失う（本番 0 人）。
- 戻し方: PR を revert（DB 変更なし）。
- 測り方: 未認証の `/api/v1/me/permissions` が 401、K1 が 0 件、デプロイ後の health 200 とバックエンドエラー 0。

## 維持の仕組み
- 守り手: backend/tests/test_tenant_admin_ssot.py
- 対象: 管理者専用ルート 9 本が `require_tenant_admin` に依存していること、救済が戻らないこと。
