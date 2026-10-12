<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ -->
# recon — role-ssot-user-roles

この文書は、権限の判定が `users.role` と `user_roles` の二重になっている箇所を、実物の行番号で調べた記録です。

親: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)

**日付**: 2026-10-12
**基準**: origin/main 0dc7e246c（作業開始時点）。根拠の調査は /tmp/CC報告ファイル/user-ssot/findings-20261012.md（リポジトリ外）。
**既存 ADR の検索**: `git grep -il "user_roles" -- docs/adr` は `docs/adr/ADR-147-common-6roles-standardization.md` のみ。`docs/adr/FEATURE-INDEX.md` で権限の正本を述べた ADR は他に無い。

## file:line 引用表（基準 0dc7e246c）

| 引用先 | 確認内容 |
|---|---|
| `backend/app/routers/calendar.py:44` | `_require_admin`。`users.role != "admin"` で 403。呼出 :473（同期モード変更） |
| `backend/app/routers/calendar.py:397` | 予定の編集。本人以外は `users.role == "admin"` のみ可 |
| `backend/app/routers/calendar.py:438` | 予定の削除。同上 |
| `backend/app/routers/google_calendar.py:62` | `_require_admin`。呼出 :175（connect/start）、:204（接続解除） |
| `backend/app/routers/integrations.py:77` | `_require_admin`。呼出 :184, :208, :390, :451, :557, :592, :645 |
| `backend/app/auth/dependencies.py:518` | system_key を取るクエリ（`SELECT DISTINCT r.system_key`）。権限計算にだけ使われている |
| `backend/app/auth/dependencies.py:532` | 権限が 0 件で `users.role='admin'` なら全権限を与える救済（:537 で `SELECT role FROM public.users`） |
| `backend/app/routers/roles.py:109` | ロール未割当で `users.role='admin'` なら優先度 1000 の救済（:112 のクエリ） |
| `backend/app/routers/roles.py:144` | `/me/permissions`。返す項目は permissions / is_super_admin / tenant_id / enabled_features |
| `backend/app/auth/system_roles.py:8` | `ROLE_KEY_OWNER`。:9 が `ROLE_KEY_ADMIN` |
| `frontend/src/pages/goal-setting/GoalSettingPage.tsx:543` | `/auth/me` を呼ぶ（このエンドポイントは本番に存在せず 404、2026-10-12 確認） |
| `frontend/src/pages/goal-setting/GoalSettingPage.tsx:537` | `user?.role === "admin"` でリーダー判定 |
| `frontend/tests-e2e/goal-setting-advisor.spec.ts:33` | `GET /auth/me` のモック（:123 にも同じ） |
| `backend/app/auth/dependencies.py:413` | `get_current_admin`（`users.role`）。#4162（8d0f8e103）で扱い済みのため本 PR は触らない。`backend/app/routers/admin.py:39` と `backend/app/routers/auth.py:43` も同じ |

## 本番の事実（READ ONLY、2026-10-12。出典 findings-20261012.md）
- active users 10 人全員が user_roles を持つ（ロール 0 件の人 0）→ 救済 2 か所の撤去で影響を受ける人は 0。
- user 9（tenant 1 のオーナー）は `users.role='user'`。現状は `_require_admin` で弾かれ、本 PR で通る。

## 未確認
- `users.role` を読む migrations / scripts（本 PR は触らない）。
