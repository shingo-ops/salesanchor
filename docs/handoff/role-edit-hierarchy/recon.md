# recon: ロール画面の編集の決まり（誰がどのロールを変えられるか）

基準: origin/main 2a1f1b68b（2026-11-08 fetch 後の worktree）。本番は reader 鍵で読み取りのみ。

## PO の言葉（2026-11-08）

- 「権限の編集ができない」
- 要件: オーナーの権限はオーナーだけが編集。システム管理者はオーナー以外を編集。マネージャーはオーナーとシステム管理者以外を編集。その他のロールはロールページを見られない。
- 追加の合意: 「オーナーとシステム管理者はそもそもロールに表示しなくて良い、点検用もページに表示する必要はない」（Opus が合意と返答）。
- 「2」= 設計ができた時点で一度見せる。

## 既存 ADR の検索

`git grep -l -i -E "system_key|compute_permission_keys|is_system" docs/adr` → ADR-147 / ADR-1007 / ADR-1048 / ADR-1063。

- `docs/adr/ADR-147-common-6roles-standardization.md:22-23` オーナー=全権限、システム管理者=system.manage 以外の全権限。
- `docs/adr/ADR-147-common-6roles-standardization.md:60` システム管理者は運営者用。super admin 以外には一覧に見せない。見分けは roles.system_key='admin'。
- `docs/adr/ADR-1017-smoke-auth-least-privilege.md:39` スモークの専用ユーザーには必要な権限だけを付ける運用。
- `docs/adr/ADR-1051-prod-ui-black-box-check.md:34,45` 点検用の人は見るだけの役割。
- `docs/adr/ADR-1053-prod-page-speed-record.md:40` 見るだけの人なので多くの画面は 403。判定なしの記録。

## 観測事実（コード）

- `backend/app/auth/system_roles.py:8-14` system_key は owner / admin だけ。隠す集合 TENANT_HIDDEN_SYSTEM_KEYS={admin}。
- `backend/app/auth/system_roles.py:27-42` compute_permission_keys: owner=全キー、admin=全キー−system.manage、他=保存行そのまま。
- `backend/app/auth/dependencies.py:569-572` owner / admin のときだけ計算を足す。
- `backend/app/routers/roles.py:178-203` GET /roles は全ロール（admin は super admin 以外に隠す）を priority 降順。
- `backend/app/routers/roles.py:278-286` PATCH: is_system なら 403。対象 priority ≥ 自分の最大 priority なら 403。
- `backend/app/routers/roles.py:431-442` PUT permissions: is_system なら 403「システムロールの権限は変更できません」。対象 priority ≥ 自分の最大なら 403。
- `backend/app/routers/roles.py:459-468` 自分が持たない権限は付与できない（エスカレーション防止）。
- `frontend/src/pages/roles/RolesPage.tsx:117` 一覧は `/roles`。
- `frontend/src/pages/roles/RolesPage.tsx:169` canEditPerms = roles.update を持つ かつ is_system でない。
- `frontend/src/pages/staff/StaffEditPage.tsx:107` / `frontend/src/pages/staff/StaffPage.tsx:118` スタッフ画面も `/roles` を使う（オーナーを付ける操作に必要）。
- `frontend/src/constants/menuPermissions.ts:65` ロールのメニューは roles.view か roles.create で出る。
- `frontend/src/constants/menuPermissions.ts:125,218` 行の固定表示は "always" / "ownerOnly" の2種。
- `frontend/src/constants/menuPermissions.ts:169-172` 「ロール」行の鍵 = roles.view/create/update/delete/assign。
- `migrations/20261005_150000_add_roles_system_key.sql:39-45` system_key 列と部分一意索引（テナント内一意）。値は別手順で入れる（ADR-155）。
- 前例: `docs/handoff/roles-system-key-data/apply.sql` 名前で1件を確かめて system_key を入れ、audit_log に記録した。
- `tests/prod-check/prod-ui.spec.ts` / `tests/prod-check/device-accept.spec.ts` に roles 画面は無い（role の語は getByRole だけ）。`tests/prod-check/page-speed-targets.ts:55,124` だけが /roles と /management-center/roles を開く（判定なし）。

## 観測事実（本番・2026-11-08 reader 鍵）

ロール（priority / is_system / system_key）:

| 会社 | ロール |
|---|---|
| t001 | オーナー 1000 True owner / システム管理者 900 True admin / マネージャー 500 / 仕入れ 450 / 発送 350 / 点検用（見るだけ） 300 / 営業 300 / CS 300 |
| t003 | オーナー / システム管理者 / マネージャー / 仕入れ / 発送 / CS / 営業 |
| t004 | 上と同じ ＋ スモーク専用 100 |
| t005, t006 | オーナー / システム管理者 / マネージャー / 仕入れ / 発送 / CS / 営業 |

マネージャー・点検用・スモーク専用の system_key は全部空。

roles.* の保存行: オーナー・システム管理者は roles.view/create/update/delete/assign。マネージャーは roles.view だけ（t001・t003・t004・t005・t006。t005・t006 は 2026-11-09 の読み直しで追記。11-08 の調べで見落とした）。t001 の点検用も roles.view。

本番画面（PO の画面・2026-11-08）: オーナー・システム管理者を選ぶと切替 126 個のうち 96 個が押せず「権限編集は不可」。マネージャー・営業は 126 個のうち 4 個だけ押せない（行ごとの「表示のみ」が無い行）。

## 未確認

- なし（点検用が 403 になっても判定のある点検は落ちないことは上の grep で確かめた）。
