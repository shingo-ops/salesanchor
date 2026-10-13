# recon P4: ロール画面の閲覧範囲とロール付与の入口 (基準: origin/main)

## 1. ロール画面の入口と API 権限
### 画面の入口
- ルート: frontend/src/App.tsx:252 `/roles`、frontend/src/App.tsx:371 `/management-center/roles`。どちらも ProtectedRoute（ログイン済みかだけ見る。frontend/src/components/ProtectedRoute.tsx:10-22）の下。**ルートに権限ガードは無い**（直打ちで開ける。API 側で弾く）。
- 管理センター左メニュー表示条件: frontend/src/pages/management-center/ManagementCenterPage.tsx:38 `hasAny("roles.view","roles.create")`。
- 管理センター入口自体の表示条件: frontend/src/components/DesktopShell.tsx:182-187 `hasAny("staff.view","teams.view","roles.view",...)`（いずれか1つ）。
- 画面内の出し分け: 「+新規」= roles.create（RolesPage.tsx:341）、「ユーザーを割り当て」= roles.assign（RolesPage.tsx:367）。
### API と必要な権限キー（backend/app/routers/roles.py）
| API | 行 | 権限 |
|---|---|---|
| GET /roles | :175-179 | roles.view |
| GET /permissions | :114 | ログイン済みなら誰でも（権限チェック無し。:120 docstring） |
| GET /roles/{id}/permissions | :373-376 | roles.view |
| POST /roles | :203-207 | roles.create |
| PATCH /roles/{id} | :259-262 | roles.update |
| DELETE /roles/{id} | :332-335 | roles.delete |
| PUT /roles/{id}/permissions | :403-405 | roles.update |
| GET /users/{id}/roles | :486-489 | roles.view |
| PUT /users/{id}/roles | :520-522 | roles.assign |
権限キー定義: migrations/002_add_permissions_master.sql:28-32（roles.view/create/update/delete/assign）。
画面の初回ロードは GET /roles と GET /permissions（RolesPage.tsx:129-130）。roles.view が無いと GET /roles が拒否され画面はエラー表示。

## 2. どのロールが権限を持つか
- 既定ロール定義: backend/app/services/tenant.py:50-185（DEFAULT_ROLES）。
  - オーナー(system_key=owner, 1000): "ALL"（:57）。システム管理者(admin, 900): "ALL_EXCEPT_SYSTEM_MANAGE"（:66）。付与処理 tenant.py:1527-1542。
  - owner/admin は check 時にも全権限を計算（backend/app/auth/system_roles.py:22-37。owner=全キー、admin=全キー-system.manage）。
  - マネージャー(500): `roles.view` のみ（tenant.py:81）。roles.create/update/delete/assign は無し。
  - 営業(300, :100-122)・CS(300, :125-146)・仕入れ(450, :148-164)・発送(350, :167-184): roles.* を一切持たない（リスト内に roles. の文字なし。grep で roles.view は tenant.py:81 の1件のみ）。
- 結論（既定値ベース）: roles.assign / roles.update / roles.create / roles.delete = オーナー・システム管理者のみ。roles.view = オーナー・システム管理者・マネージャー。営業・CS は持たない。
- 注意: 既存ロールは「権限のカスタマイズを上書きしない」（tenant.py:1588 docstring）。各テナントの実際の付与は画面で編集可能なので既定と違う可能性あり（本番 DB は未確認）。migrations/ に roles.* を role_permissions へ付与する SQL は検出されず（git grep 'roles\.' *.sql は 002 のマスタ定義のみ）。
- システム管理者(admin)ロールは super admin 以外には非表示（system_roles.py:14 TENANT_HIDDEN_SYSTEM_KEYS）。よってテナント側で実際に roles.* を使えるのは owner（と、画面で roles.* を付与されたロール）。

## 3. 「利用者番号でロールを付ける」部分
- 範囲: frontend/src/pages/roles/RolesPage.tsx
  - 状態: :121-124 `userAssignOpen` / `targetUserId` / `selectedRoleIds`
  - 関数: :306 `toggleUserRole`、:312-323 `saveUserRoles`（:314 `api.put(/users/${targetUserId}/roles, {role_ids})`）、:324-328 `closeUserAssign`
  - 開くボタン: :367-371（roles.assign 条件）
  - モーダル: :549-572（:556-558 数値入力 TextFieldControl、:559-567 `roles.map` のチェックボックス＋priority 表示、:568-571 保存/キャンセル）
  - i18n キー: roles.assignUsers（ja.json:1987 / en.json:1987）、roles.targetUserId（:2013）、roles.grantRoles（:2014）。共通キー common.cancel / common.save / common.saveError は共用。
- PUT/GET /users/{id}/roles を呼ぶ画面: frontend/src で非テストコードの呼び出しは RolesPage.tsx:314 のみ（git grep 'users/.*roles' で他に無し）。GET /users/{id}/roles を呼ぶフロントは無し。backend 側 GET は roles.py:486 に存在するが利用画面なし。

## 4. スタッフ画面のロール選択
- 部品: Select（StaffFormFields.tsx:67-74、StaffPage.tsx:262-269、StaffEditPage.tsx:185-192）。options = `roles.map(r => ({value: String(r.id), label: r.name}))`。
- 選択肢の出どころ: GET /roles（StaffPage.tsx:132、StaffEditPage.tsx:99）。= roles.view 必須・admin ロールは非表示（roles.py:180-199）。
- 送る値: `role_id: parseInt(form.role_id,10)`（StaffPage.tsx:166 作成、:193 編集、StaffEditPage.tsx:141）。staff.role_id を POST/PATCH /staff に送る。
- backend staff.py の権限: GET /staff :520-521 と GET /staff/{id} :556-557 = staff.view、POST /staff :576-577 = staff.create、PATCH :664-665 = staff.update、DELETE :728-729 = staff.delete。画面側: 作成ボタン staff.create（StaffPage.tsx:223）、編集 staff.update（:366,:377）、削除 staff.delete（:367）。staff.* は tenant.py の既定ロール（マネージャー〜発送）のリストに無い → 既定では owner/admin のみ。
- role_id の検証: staff.py:124-136 `_ensure_assignable_role` はテナント一致＋隠しロール除外のみ。**priority 上限の検査なし**。
- POST /staff は user_roles にも INSERT（staff.py:626）。PATCH /staff は staff.role_id を更新するだけで user_roles に触らない（staff.py:693-702。staff.py 内の user_roles 言及は :626 のみ）。トリガ等での同期は grep で未検出（下記未確認）。
- 副次: roles.view が無い人は GET /roles が失敗するため、staff.* を持っていてもスタッフ画面のロール選択肢が取れない（StaffPage の Promise.all が失敗する挙動かは未確認）。

## 5. PUT /users/{id}/roles の検査（roles.py:520-594）
1. 権限 roles.assign（:522）。
2. 対象ユーザーが同テナント（:533-538、なければ 404）。
3. 隠すロールは super admin 以外には「存在しない」扱い: 取得条件 `_visible_role_sql`（:546）→ missing で 400「存在しないロールID」（:552-557）。
4. priority: `my_max = _max_priority_for_user(current_user)`（:541, 定義 :92-107、user_roles の最大 priority、無ければ -1）。付与対象の各ロールで `row.priority >= my_max` なら 403（:558-563）。= **自分の最大 priority 以上（同値含む）のロールは付与不可**。したがって owner(1000) でも priority 1000 のオーナーロールは付与できない（同値）。
5. 既存割当の削除は「見えるロールのみ」（:566-573）。super admin 以外は既に持つ隠しロールを外さない。
6. 対象ユーザーの現在の priority は検査しない（自分より上位のユーザーのロールを書き換えられるかの検査は無い。:531-594 に該当コード無し）。自分自身への付与の禁止も無し。
7. 監査ログ（:583）・権限キャッシュ破棄（:592）。
- 参考: PUT /roles/{id}/permissions は is_system ロール不可（:418）・role.priority>=my_max 不可（:425）・自分が持たない権限は付与不可（:446-455）。

## 未確認
- 本番各テナントの role_permissions 実値（読み取り専用でも本番 DB 接続禁止のため未確認）。
- require_permission の実装（owner/admin の計算が実際にここを通るか）は今回読んでいない。
- PATCH /staff の role_id 変更と user_roles の不一致を DB 側で吸収する仕組みの有無（staff.py/tenant.py/migrations の grep では検出されず。完全な否定ではない）。
- StaffPage の GET /roles 失敗時の挙動。
