# recon: オーナー / システム管理者の権限を、チェック時に権限マスタから計算する（2026-10-06）

基準: origin/main a9140777d に、roles.system_key の列を足す PR（#3986）を積んだ状態。値（件数・権限キー名）だけを記載する。元の調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- 検索語: role / permission / system role / ADR-155 / ADR-136。関係する ADR: ADR-155（マイグレーションで値を操作しない。この PR は migration を足さない）、ADR-136（認可に関わる危険 PR の GO）。

## 1. 事実：今の権限の決まり方
1. backend/app/auth/dependencies.py:485-529 load_user_permissions が唯一の計算元。user_roles → role_permissions → public.permissions の和集合（:505-513）。保存済みの付与が空で public.users.role が admin のときだけ全キー（:518-527）。結果は Redis に 300 秒キャッシュ（backend/app/cache.py:18）。
2. 同じ関数を使う側: require_permission（dependencies.py:532-558）、GET /me/permissions（backend/app/routers/roles.py:112-148）、roles.py:424 の権限昇格の検査、calendar.py・inventory_aggregated.py・inventory_search.py の直接呼び出し。フロントは /me/permissions を usePermissions（frontend/src/hooks/usePermissions.ts:25）で読む。
3. オーナー / システム管理者の権限は、作成時に backend/app/services/tenant.py の _assign_permissions_to_role（ALL / ALL_EXCEPT_SYSTEM_MANAGE）で role_permissions に書かれ、その後に増えた権限キーは migrations/025_resync_owner_admin_all_permissions.sql の毎デプロイ再実行でしか届かない。
4. role_permissions を読む他の場所（roles.py:353-376、tenant_admin_inventory_visibility.py:71,162）は、保存済みの行を表示するだけで、認可には使わない。
5. 本番（2026-10-05 読み取り）: 5 テナントとも、オーナーは全 123 キー、システム管理者は 122 キー（system.manage を除く）。4 人の admin ユーザーは全員オーナーのロールを持つ。roles.system_key の列は #3986 のデプロイ後に存在し、値の設定は別手順（docs/handoff/roles-system-key-data/、未実行）。

## 2. 事実：新テナントの作成が移行頼みだった 3 点（同じ PR で直す）
- 080 の phase: backend/app/services/tenant.py の tenant_settings の INSERT が 'A'（080 が次のデプロイで B にする）。'B' を直接書く。
- 023 の is_system: システム管理者が False で作られていた（023 が True にする）。True にする。
- 075 の goals 付与: マネージャー・営業・CS・仕入れ・発送に goals.view、マネージャーに goals.edit が role_permissions に無かった（075 が付ける）。DEFAULT_ROLES に足す。本番の 5 テナントはすでにその形（確認済み）。

## 3. 事実：デプロイ順と順序の条件
- .github/workflows/deploy.yml:376（新しいコードが先）→ :500（migration が後）。この PR のコードは roles.system_key の列を読むので、列を足す PR（#3986）のデプロイと、5 テナントへの値の設定が済んでから出す。
- 値が付く前にデプロイされても、system_key を持つロールが無いので計算の分岐に入らず、今の和集合の結果と同じになる（保存済みの owner/admin の行はそのまま残す）。

## 4. 事実：試験
- 実関数 load_user_permissions は、backend/tests/conftest.py:1596-1604 の自動モックで全試験が差し替えている。実関数を流す試験は今まで無い。
- 今回の PG 試験は、CI が実際に設定する RLS_ADMIN_DATABASE_URL でゲートする（backend/tests/test_rls_bootstrap_ordering.py と同じ形）。CI の .github/workflows/test.yml:222,224 は RLS_TEST_DATABASE_URL と RLS_ADMIN_DATABASE_URL を設定し、TEST_PG_URL は設定しない（TEST_PG_URL だけでゲートする試験は CI で実行されない）。
- ローカルで動く試験（DB 不要）: backend/tests/test_system_roles.py（計算の純関数と、新テナントの状態）。

## 5. 未確認・実施していないこと
- PG 試験はローカルでは skip（実行は CI）。tests の bootstrap で 070 を流す順序が通るかは、CI での確認待ち。
- 手元で SQL を流しての確認はしていない（書き込みを防ぐフックが手元の DB 実行も止める）。
