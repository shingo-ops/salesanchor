<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 会社の持ち主が自社の社員のログインを許可する／会社の分け方の見張り

**対象ADR**: ADR-1063（新規）、ADR-1055（改訂）  
**recon**: docs/handoff/tenant-owner-login-approval/recon.md  
**KGI**: docs/handoff/tenant-owner-login-approval/kgi.md（PO 承認済み 2026-11-05「1」）  
**日付**: 2026-11-05  
**担当**: Planner（Claude Opus）  
**状態**: 設計審査済み（3回目 APPROVE・推奨3件反映）。PO 実装承認済み（2026-11-06 チャット。画面の動き・止める仕組み・新しいスタッフの最初のログインの説明のあと、「1. このまま作り始める」に「1」と回答）。便2 は別に PO の「GO #番号」、便7 は別に PO が `!` で流す ruleset の台本が要る（承認はこれらを兼ねない）。

---

## 0. 目的（PO の言葉）

- 「テナントオーナーが自分の社員の許可は権限を持って責任持ってい対応する」
- 「この仕組みを標準化して管理定着させて継続させるための機械的な仕組み」
- しんごさんがいなくても、締め出された社員をその会社のオーナーが入れられる。1社の事故が他社に広がらない作りを、機械が毎回・毎日確かめる。

---

## 外部・過去事例の参照と我々への応用

- 事例1: GitHub 公式文書「Events that trigger workflows」（docs.github.com、2026-11-05 閲覧）。pull_request はPRのマージ用の写しで動き、pull_request_target は基のリポジトリの既定ブランチの定義で動く。PRのコードを動かすなら pull_request_target は避けよ、と警告がある → 我々への応用: K10 の見張りは pull_request_target で動かし、PR のコードは一切 checkout・実行しない（変わったファイルの名前を GitHub API で読むだけ）。これで PR が自分の見張りを外せない。
- 事例2: 社内の前例 ADR-1055（いつもの機械で番号を選ぶ許可）と運営の許可画面 → 我々への応用: 許可の UPDATE・監査・知らせの流れをそのまま共通化し、許可する人の範囲だけ「同じ会社のオーナー」に広げる。新しい状態や新しい許可の種類は作らない。
- 事例3: 社内の前例 `backend/app/tasks/master_required_fields_monitor.py`（定期で管理者用 Discord に送る）→ 我々への応用: K9 の毎日点検は同じ形で、緑のときも毎日1通送る（黙っているのが「合格」なのか「止まっている」のか区別するため）。
- 数値の外部事例は使わない。理由: 本件の合否は自社の試験と本番の観測（K1〜K11）で決まり、他社の数値は判定の根拠にならない。

---

## 1. 対象と対象外

対象（便ごと・一度に1つ変更して測る）:

| 便 | 内容 | KGI | 危険パス |
|---|---|---|---|
| 1 | スタッフ登録の文言で他社在籍が分からないようにする | K7 | なし |
| 2 | 依頼に「会社の管理者に頼んだ時刻」の列を足す（migration のみ） | K5 の土台 | migrations/ → PO「GO #番号」 |
| 3 | バックエンド: オーナー専用の判定・頼むボタンの受け口・オーナーの一覧と許可・知らせ・許可の共通化 | K1〜K6 | なし |
| 4 | 画面: 待ち画面の「会社の管理者に頼む」・管理センター「ログインの許可待ち」・鈴 | K1・K3・K5 | なし |
| 5 | CI: 会社の列があるのに RLS が無い public の表を止める | K8 | なし |
| 6 | 本番の毎日点検 → Discord | K9 | なし（本番へは通常のデプロイ） |
| 7b | AI が PO の名前で GO を書く操作と、同じ名前の検査を足す操作を止める（手元とクラウドの見張り）。便7 の前に合流 | K10 の補い | なし（手元の見張りの導入は共通の台本） |
| 7 | 見張りのファイルを変える PR を止める（pull_request_target）＋必須チェックへの登録 | K10 | .github/workflows/ ＋ Ruleset 変更 → PO が `!` で台本を流す |
| 8 | 決まりの文書に「何を守るか／どの見張りか」の表 | K11 | なし |

対象外: 接続の使い回しの隙・Meta の Page 重複登録（report.md 穴2・穴3）。運営の許可画面は残す。オーナーが「見送る（拒否）」ボタンは作らない（放っておけば30分で切れる。拒否は本人のいつもの機械か運営で行う。必要になったら別件）。

---

## 2. 変更の前後（便ごと）

### 便1: スタッフ登録の文言（K7）

- 場所: `backend/app/routers/staff.py:78` 〜 89
- 前: 他社なら 409「このメールアドレスは他の会社で使われています」、自社の重複なら 409「このメールアドレスのスタッフはすでに登録されています」
- 後: どちらも 409「このメールアドレスは登録できません。別のメールアドレスを使ってください。」（1つの定数にし、2か所から使う）
- 試験: `backend/tests/test_staff_create_users.py:115` の期待を新しい文言に変え、「他の会社」を含まないことも確かめる。自社の重複の試験も同じ文言を期待する。
- 残る弱み（受け入れる）: メールは全社で1つのため、「登録できない」こと自体から誰かが使っていると推測はできる。文言で会社の別を言わないところまでを本件とする（ADR-1063 に記録）。

### 便2: 列の追加（migration）

- 新ファイル: migrations/20261106_100000_add_login_request_admin_requested_at.sql（時刻は実装時に最新の migration より後にする）
- 中身: `ALTER TABLE public.auth_login_requests ADD COLUMN IF NOT EXISTS admin_requested_at TIMESTAMPTZ NULL;` と、オーナーの一覧用の部分索引 `CREATE INDEX IF NOT EXISTS ix_auth_login_requests_admin_requested ON public.auth_login_requests (admin_requested_at) WHERE status = 'pending' AND admin_requested_at IS NOT NULL;`
- 足すだけ・NULL 可・既定値なし → 既存の行は書き換わらない。ロック待ちは ADR-1037 の決まり（lock_timeout）に従う。
- ai_ro の見せ方: timestamptz は素通し（`migrations/20261024_100000_create_ai_cloud_meta.sql:124`）。`backend/tests/ops/test_ai_cloud_views.py:622` の試験が通ることを確かめる。
- 戻し方: `ALTER TABLE public.auth_login_requests DROP COLUMN IF EXISTS admin_requested_at;`（索引も一緒に消える）。便3 が出る前なら使う人はいない。

### 便3: バックエンド（K1〜K6）

(1) オーナーの判定（1か所）
- `backend/app/auth/system_roles.py` に `is_tenant_owner(system_keys) -> bool`（`ROLE_KEY_OWNER in system_keys` のみ。admin は入れない）。
- `backend/app/auth/dependencies.py` に `require_tenant_owner`（`require_tenant_admin` の隣。get_current_user と get_current_tenant を通したうえで、`get_user_system_keys` に owner が無ければ 403 `owner_only`）。
- `/me/permissions`（`backend/app/routers/roles.py:145` 付近）の返り値に `is_tenant_owner` を足す。

(2) 許可の共通化（運営とオーナーで同じ UPDATE を1か所に）
- `backend/app/auth/devices.py` に `approve_request_as_admin(db, *, request_id, approver_user_id, note, tenant_id: int | None, require_admin_requested: bool) -> (target_user_id, target_tenant_id)` を置く。HTTP の例外は投げず、結果の種類（`not_found`・`own_request`）を返すか専用の例外にし、受け口で今と同じ 404・403 に直す（運営の受け口の返事は変えない）。
  - 判定の順番（運営の今の順 `backend/app/routers/super_admin_login_requests.py:117` 〜 161 と同じ）:
    1. 依頼と依頼した人を `public.auth_login_requests r JOIN public.users u ON u.id = r.user_id WHERE r.id = :id` で引く。`tenant_id` が渡されたら `AND u.tenant_id = :tenant_id`、`require_admin_requested` が真なら `AND r.admin_requested_at IS NOT NULL` を付ける。無ければ 404（他社の依頼・頼まれていない依頼は「無い」扱い）。
    2. 依頼した人が許可する人と同じなら 403 `cannot_approve_own_request`（UPDATE より前）。
    3. `UPDATE … SET status='approved', decided_at=now, decided_via='admin', decided_by_user_id=:approver, decided_note=:note WHERE id=:id AND status='pending' AND expires_at > now`（オーナー用は同じ `admin_requested_at IS NOT NULL` も WHERE に入れる）。0 行なら 404。
  - 運営は `tenant_id=None, require_admin_requested=False`、オーナーは `tenant_id=今の会社, require_admin_requested=True` で呼ぶ（ADR-1055 改訂行「社員が頼んだ依頼だけ」と一致させる）。
- 運営の受け口 `backend/app/routers/super_admin_login_requests.py:107` はこの関数を `tenant_id=None` で呼ぶ形に置き換える（動きは同じ。既存の試験がそのまま通ることで確かめる）。
- decided_via は既存の 'admin' を使う（制約の変更なし）。オーナーか運営かは監査の event 名と decided_by_user_id で分かる。

(3) 頼むボタンの受け口（待っている社員の画面から）
- `POST /auth/login-requests/ask-admin`（`backend/app/routers/auth.py` の poll の隣）。poll（`backend/app/routers/auth.py:1378`）と同じく、最初に `_require_issuance_enabled()` と `_require_app_origin(request)` を通す。認証は待ち中 Cookie（`_load_login_request`、`backend/app/routers/auth.py:1318`）。
- Cookie が無い・依頼が引けないときは poll と同じく `{"status":"expired"}` を返して Cookie を消す（`_pending_closed("expired")`。画面は待ちを終える）。依頼が pending かつ期限内でなければ 409 `not_pending`。
- `UPDATE … SET admin_requested_at = now WHERE id=:id AND status='pending' AND expires_at > now AND admin_requested_at IS NULL RETURNING id`。0 行（もう頼んだ）なら知らせを出さずに `{"status":"already_requested"}` を返す（連打で知らせが増えない）。
- 依頼した人の会社は `public.users` から引く（Cookie の依頼の user_id → tenant_id）。会社の roles・user_roles は RLS で `app.tenant_id` を見る（`migrations/003_add_phase1_tenant_tables.sql:176` 〜 214）ため、`set_tenant_context(db, tenant_id)` を張ってから `_owner_user_ids`（`backend/app/services/user_notices.py:73`）で取り、取り終えたら `clear_tenant_context(db)` で外す（この受け口はログイン前で、もともと会社の文脈が無い）。依頼した本人を除く。
- 試験で「会社の文脈を張らないと 0 人になる」「張ると正しい人数」を salesanchor_app の実 PostgreSQL で確かめる（文脈の張り忘れを試験で止める）。
  - 0 人なら `{"status":"no_owner"}` を返す（画面は「会社の管理者が見つかりません。運営に連絡してください。」）。列は付けたまま（運営の一覧で分かる）。
  - 1 人以上なら、各オーナーに `publish_user_change(owner_id, TOPIC_AUTH_LOGIN_REQUEST)`（鈴を生で取り直させる）と、メール `send_staff_login_help_mail`（新設・`backend/app/services/auth_mail.py:192` の形に合わせ、リンク・番号・Cookie を入れない。中身は社員の名前・メール・時刻・機械・場所）を BackgroundTasks で送る。`{"status":"requested"}`。
- 監査: `_record_auth_audit` で event `login_request_admin_asked`（request_id・人数）。

(4) オーナーの一覧と許可
- 新ファイル backend/app/routers/tenant_login_requests.py（main.py に登録）。
- `GET /tenant/login-requests`（`require_tenant_owner`）: 自社（`u.tenant_id = 今の会社`）・pending・期限内・`admin_requested_at IS NOT NULL`・依頼した人が自分でない、を新しい順に。返す項目は運営の一覧と同じ形（名前・メール・機械・場所・時刻・期限）に、`admin_requested_at` を足す。
- `POST /tenant/login-requests/{id}/approve`（`require_tenant_owner`・`require_app_origin`）: 本文 `note`（本人確認の方法。1〜200 文字・必須）。(2) の関数を `tenant_id=今の会社` で呼ぶ。監査 event `login_request_approved_owner`。commit の後に `reset_tenant_context`（ADR-072 Rule C）。`publish_user_change(依頼した人)` で待ち画面の poll を起こす。
- 待っている機械は既存の poll（`backend/app/routers/auth.py:1378`）がそのまま機械を登録して入れる（変更なし）。

(5) 鈴の数
- `GET /login-approvals/pending`（`backend/app/routers/login_approvals.py:45`）は変えない。鈴は、オーナーのときだけ `GET /tenant/login-requests` も生で取り、件数を足して表示する（写しの行を user_notices に作らない＝SSOT）。

### 便4: 画面（K1・K3・K5）

- 待ち画面 `frontend/src/pages/login/LoginPage.tsx:300` 付近: 「会社の管理者に頼む」ボタンを、いつもの機械や控えの番号の有無にかかわらず出す（社員が自分の機械を持っていないときもあるため）。既存の `Button`（variant="outline" size="auth" shape="pill" fullWidth）を使う。押した後は結果の文を `Callout` で出す（requested / already_requested / no_owner の3つ）。受け口が `{"status":"expired"}` を返したときは、poll の expired と同じ既存の表示に移る（新しい文を作らない）。409 `not_pending` のときは、その場で poll を1回呼び、poll の結果（入れた・断られた・期限切れ）の既存の表示に従う（依頼の状態の判断を poll の1か所に保つ）。いつもの機械も控えも無いときの文 `login.deviceApproval.noTrustedDevice` は「会社の管理者に頼むか、運営に連絡してください。」に改める。
- 管理センター: `frontend/src/pages/management-center/ManagementCenterPage.tsx:28` のメニューに「ログインの許可待ち」を `isTenantOwner` のときだけ足す。`frontend/src/App.tsx:393` の入れ子に `login-requests` を足す。画面は新ファイル frontend/src/pages/management-center/LoginRequestsPage.tsx。運営の画面 `frontend/src/pages/super-admin/LoginRequestsPage.tsx:1` と同じ部品（一覧・ConfirmModal・メモ欄）を使い、表の行の部品は2画面で共有する（同じ見た目の部品を2つ書かない）。
- `frontend/src/hooks/usePermissions.ts:1` に `isTenantOwner` を足す。
- 鈴 `frontend/src/components/NoticeBell.tsx:1`: isTenantOwner のときだけ社員の依頼の件数を足し、押すと管理センターの画面へ移る。
- 文言は全部 `t()`。ja.json と en.json に同じ鍵（`managementCenter.loginRequests.*`・`login.deviceApproval.askAdmin*`）。色・余白はトークンのみ。生の select/input/自作タブは使わない（ADR-144）。

### 便5: CI の見張り（K8）

- 新ファイル scripts/check_public_tenant_rls.py: DB に入って `public` の表のうち `tenant_id` 列を持ち `relrowsecurity = false` のものを数え、許可一覧に無いものがあれば名前を出して exit 1。
- 許可一覧は1か所: 新ファイル backend/app/ops/tenant_rls_allowlist.py（表名 → 理由の dict）。CI のスクリプトと便6の毎日点検の両方がここを読む（データを分散させない）。
- 置く場所: job「マイグレーション全件ドライラン（実DB）」（`.github/workflows/migration-test.yml:1352`）の最後の手「全件ドライラン（失敗したら止める）」（`.github/workflows/migration-test.yml:2071`）の直後に1手を足し、全件を流し終えた報告用 DB `jarvis_report` を見る。1周目（`.github/workflows/migration-test.yml:2002`）は 2026-06 までの migration しか流さないため使わない。この job の結果は必須チェック「マイグレーションSQL 実行テスト（実DB）」（`.github/workflows/migration-test.yml:2087` のまとめの job）に集まる。job は Python 3.12 と backend の依存を入れ済み（`.github/workflows/migration-test.yml:1383` の setup-python と `.github/workflows/migration-test.yml:1393` の依存の導入）なので、スクリプトは `PYTHONPATH=backend` で許可一覧を import できる。
- 起動の条件: `.github/workflows/migration-test.yml:40` の paths-filter に scripts/check_public_tenant_rls.py と backend/app/ops/tenant_rls_allowlist.py を足す（一覧やスクリプトだけを変える PR でも点検が動く）。
- 限界: `scripts/migration-guard/dryrun-exclusions.tsv` で外された migration の表は見えない → この除外一覧も K10 で守る（便7）。
- 最初の数え方: 最初の PR は「数えて出すだけ」の形で CI に流し、出た表の一覧（生出力）を Opus が1件ずつ理由を確かめて許可一覧に入れる。一覧の中身は PR に載せて PO に報告する。そのあと「落とす」形に切り替える（同じ PR の2つ目のコミット）。推測で一覧を作らない。
- 試験（落ちる見本と通る見本）: backend/tests/test_check_public_tenant_rls.py を実 PostgreSQL（`RLS_ADMIN_DATABASE_URL`）で動かす。一時の表 public.ci_rls_probe（tenant_id 付き・RLS なし）→ スクリプトが 1 を返す。RLS を付ける → 0。最後に表を消す。

### 便6: 本番の毎日点検（K9）

- 新ファイル backend/app/tasks/tenant_isolation_daily_check.py。`backend/app/celery_app.py:21` の include と `backend/app/celery_app.py:69` の時間割（毎日 09:05 JST）に登録する。
- 見るもの:
  1. 今の接続役が superuser でも BYPASSRLS でもない（`pg_roles` の自分の行）。
  2. BYPASSRLS を持つ役の一覧が、許可一覧（同じ backend/app/ops/tenant_rls_allowlist.py の `BYPASSRLS_ROLES`）と一致する。
  3. public の tenant_id 付きで RLS の無い表が、許可一覧の表と一致する。
- 送り方: 結果を毎日1通 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` に送る（緑でも送る）。崩れたら赤で、崩れた項目の名前を書く。値（鍵・接続の文字列）は書かない。
- 最初の値: 便6 の初回実行の結果（BYPASSRLS の役の一覧）を Opus が読み、PO に報告してから許可一覧に固定する（推測で入れない）。固定までは「黄（一覧未固定）」で送る。
- 試験: 実 PostgreSQL で、役と表の状態を変えて緑・赤が切り替わることを確かめる（Discord はモックで送信内容を見る）。

### 便7: 見張りを外す PR を止める（K10）

- なぜ今の仕組みでは足りないか: `.github/workflows/process-artifacts-gate.yml:8` は pull_request で動くため、設定もスクリプト（`scripts/check-process-artifacts.js:51`）も PR 側のものが動く。PR がスクリプトと一覧を同時に書き換えれば自分で見張りを外せる。workflow-lint（`.github/workflows/workflow-lint.yml:1`）も同じで、しかも必須チェックではない。
- 後: 新ファイル .github/workflows/guard-files-gate.yml。
  - 起動は `pull_request_target`（types: opened, synchronize, reopened, edited, labeled, ready_for_review）。基のブランチ（main）の定義だけが動く。
  - PR のコードを checkout しない・実行しない。`gh api repos/{repo}/pulls/{n}/files --paginate` で変わったファイル名だけを読む。名前を変えたファイルは新しい名前が `filename`、元の名前が `previous_filename` に入るため、守る一覧との照合は両方で行う（名前を変えて一覧から外す抜け道を止める）。権限は `contents: read`・`pull-requests: read`。
  - 判定と守るファイルの一覧は新ファイル scripts/guard-files-gate.js に書き、workflow は基のブランチの commit（`ref: ${{ github.sha }}`）だけを checkout して動かす（PR 側から変えられない場所に置くため。既存の guard-authoring-gate.yml の evaluate と同じ形）。pull_request_target の job の結果は PR の head の検査として付く（2026-11-20 実測: PR #5610 の head 6dab4234 に「evaluate guard authoring from main」success）。一覧は2つの組に分ける（PO 2026-11-20「1」。理由は下の「2つの組に分けた理由」）。
    - 組A（PO 本人の GO だけで通る・合わせて22件。ここに最初の17件、足した5件は下）: `.github/workflows/lint-tenant-schema.yml`・`.github/workflows/workflow-lint.yml`・`.github/workflows/process-artifacts-gate.yml`・.github/workflows/guard-files-gate.yml・.github/workflows/guard-files-gate-unit.yml・scripts/guard-files-gate.js・scripts/tests/test-guard-files-gate.js（この見張り自身の4件。試験は別の workflow に分ける。同じ workflow に pull_request を足すと、gate の job が skipped として同じ名前で付き、必須チェックの抜け道になるため）・`scripts/lint_tenant_schema.py`・`scripts/migration-dryrun-report.py`・`scripts/migration-guard/dryrun-exclusions.tsv`・scripts/check_public_tenant_rls.py・backend/app/ops/tenant_rls_allowlist.py・backend/app/ops/tenant_rls_checks.py・backend/app/tasks/tenant_isolation_daily_check.py・K2 の試験 backend/tests/test_tenant_login_requests.py・K8 の試験 backend/tests/test_check_public_tenant_rls.py・K9 の試験 backend/tests/test_tenant_isolation_daily_check.py。
    - 組B（PO 本人か、POの委任に基づく Opus の GO で通る・合わせて11件。ここに最初の3件、足した8件は下）: `.github/workflows/test.yml`・`.github/workflows/migration-test.yml`・`scripts/check-process-artifacts.js`。
    - 設計の後に増えた2件（tenant_rls_checks.py・test_tenant_isolation_daily_check.py）は便6（#5593）で生まれた。tenant_rls_checks.py は CI の点検と本番の毎日点検の両方が読む SQL の唯一の正本（`backend/app/ops/tenant_rls_checks.py:3-5`・`scripts/check_public_tenant_rls.py:21`・`backend/app/tasks/tenant_isolation_daily_check.py:23`）。ここを書き換えると両方の見張りが同時に目隠しされるので組A に入れる。2件とも 2026-10-20〜11-19 の変更は #5593 の1回だけで、その PR は組A の tenant_isolation_daily_check.py も変えているため、PO の GO の回数は増えない（数え方は下）。
    - 審査1回目（中5）を受けて足したもの（2026-11-20）:
      - 組A に5件: 便7b の AI 側の見張り（scripts/agent-hooks/go-identity-guard/guard.py・guard-manifest.json・test_guard.py、scripts/agent-hooks/cloud/go_comment_guard.py・test_go_comment_guard.py）。どれも便7b で新しく作るので、先月の変更は0回。
      - 組B に3件: `backend/pyproject.toml`（pytest の addopts で試験を外せる。先月0回）・`scripts/agent-hooks/cloud/dispatch.sh`（クラウドの見張り全部の入口。先月2回）・`.github/workflows/agent-hooks-test.yml`（見張りの試験を回す。先月3回）。
      - 審査2回目（中2・中3）を受けて足したもの（2026-11-20）:
        - 組B に `.claude/settings.json`。クラウドの見張りの入口（dispatch.sh）を道具に結び付ける場所で、dispatch.sh を組B に入れた理由がそのまま当てはまる。先月3回。
        - 組B に、今は無い4件: `backend/pytest.ini`・`backend/.pytest.ini`・`backend/pytest.toml`・`backend/.pytest.toml`。作られると backend/pyproject.toml の pytest の設定より先に読まれ、設定は混ぜられない（pytest 公式「Finding the rootdir」: "the first match wins"。Context7 /websites/pytest_en_stable で 2026-11-20 確認）。`.github/workflows/test.yml:259` は backend で引数なしの `pytest -q --tb=short` を流すので、backend の直下が対象になる。tox.ini と setup.cfg は pyproject.toml より後に探されるので入れない。今の pytest は 8.3.5（`backend/requirements-dev.txt:9`）で、pytest.toml を読むかは確かめていない。無くても困らないので守る側に入れる。
      - 組A は 22件、組B は 11件（在る7件と、今は無い4件）。
    - 入れないもの（理由つき）:
      - `scripts/check_tenant_template_shape.py` とその試験。新しい会社の型の点検で、ADR-1063 の見張りではない。
      - `backend/tests/conftest.py`（先月28回）と `backend/tests/rls_bootstrap.py`（先月13回）。中で RLS の役（salesanchor_app）を決めていない（役は `.github/workflows/test.yml:198-240` で作って繋ぐ。組B で守る）。守ると月に約41回 GO が増える。conftest の `collect_ignore` や `pytest_collection_modifyitems` で外した試験は skipped と出ず、ログに残らない（審査2回目の中3）。`backend/tests/` の下に pytest.ini などを足して設定を差し替える道も、見張りの外に残る。これはファイルを指して流す実行（`.github/workflows/migration-test.yml:2295`）で効く。どちらも限界として「守る仕組み」の表に書く。
      - `.github/workflows/migration-guard.yml`・`scripts/migration-guard/rewrite-allowlist.tsv`。migration を凍らせる見張りで、ADR-1063 の見張りではない。
      - `.github/CODEOWNERS`。ruleset 15777895 の `require_code_owner_review` が false なので、合流の判定に効かない（2026-11-20 に ruleset の生の値で確認）。
  - 判定（守るファイルが変わっているとき）。実装の順と番号は card-7.md「decide(input) の決まり」の1〜9 を正とする。下の8 は card の判定4 にあたる（審査2回目の軽5）:
    1. 変わった守るファイルに組A が1件でもあれば、GO を書けるのは `shingo-ops` だけ。組B だけなら `shingo-ops` か `shingo-cc`（POの委任に基づく Opus の名義）。書き手は API の `user.login` で確かめる（本文の文字だけで信じない）。
    2. GO のコメントは1行目が `GO #<この PR の番号> <SHA 7〜40文字>` で始まる（後ろに文を続けてよい）。SHA は、この PR の commit の一覧（`gh api repos/{repo}/pulls/{n}/commits --paginate`。GitHub の上限 250件）の中でちょうど1件の先頭と一致すること。一致した commit の 40文字の SHA を、下の 3 の中身の照合に使う（審査1回目の軽7。contents API に短い SHA を渡さない）。
    3. GO の SHA の時点と今の head（`github.event.pull_request.head.sha`）の時点で、変わった守るファイルの中身が全部同じであること（`gh api repos/{repo}/contents/{path}?ref=<sha>` の blob の `sha` を比べる。無いファイルは「無い」同士で一致）。GO の後に守るファイルを1行でも変えると中身が違うので落ちる（古い GO で後から足した変更を通さない）。守らないファイルだけの push や、main を取り込む `gh pr update-branch` では、守るファイルの中身が同じなら GO は生きたまま。
    4. 条件を満たす GO が1件でもあれば通す。無ければ落ち、どの組の誰の GO が要るかを出す。
    5. 書き直された GO は使わない。REST のコメントの `updated_at` が `created_at` と違えば候補から外す。理由は審査1回目の重3。書き込みの権限がある人は他人のコメントを書き換えられ、そのとき `user.login` は元の書き手のまま残る。GitHub 公式の文書で `updated_at` は「書き直した時刻。書き直していなければ作った時刻」とされている（Context7 /github/docs で 2026-11-20 に確認）。絵文字の反応で `updated_at` が変わるかは、まだ確かめていない。変わる場合は正しい GO も外れるが、通してしまう側には倒れない。そのときは GO を新しく書き直す。
    6. 読んだファイルの数が PR の `changed_files` と違えば落とす（審査1回目の中4）。GitHub の files の一覧は 3000件で切れるため。
    7. commit の数が 250件以上なら落とす。commit の一覧の上限が 250件のため。
    8.（card-7.md の判定4）守る一覧の外でも、`.github/workflows/` の下で足したり変えたりしたファイルは中身を読む。読むのは head の中身を contents API で読むだけで、動かさない。文に「guard-files gate」（大文字と小文字、空白の数は問わない）を含み、guard-files-gate.yml 以外のものがあれば、GO があっても落とす。理由は審査1回目の重2。同じ名前の検査が2つ付くと、どちらが効くかを GitHub は決めていない（公式の文書: "Using the same job name in multiple workflows can cause ambiguous status check results"）。偽物が緑を付けると本物の赤が隠れるおそれがある。この判定だけでは隠れを防ぎきれないので、AI 側の見張り（便7b）でも止める。除外は完全な道 `.github/workflows/guard-files-gate.yml` との一致だけで判定する（審査2回目の軽6）。この判定で付く赤も同じ名前の検査になる。偽物の緑と本物の赤が並んだときに合流が止まるかは、GitHub の公式文書に書かれていない（未確認・審査2回目の中1）。そこで見本C で、PR が合流できない（`mergeStateStatus` が `BLOCKED`）ことを生出力で確かめる。止まらなければ PO に上げ、判定4 の作り方を考え直す。
    - head 一致から中身一致へ変えた理由: main の ruleset は「main に追いついていること」を求める（strict）。main が忙しく、合流の前に何度も update-branch が要る。head 一致のままだと、そのたびに PO 本人の GO のやり直しが要る。守りたいのは守るファイルの中身なので、中身の一致で縛る。
  - コメントを書いても pull_request_target は動き直さない。GO のコメントの後は、落ちた実行を `gh run rerun` でやり直す。やり直しは元の起動と同じ `GITHUB_SHA` と同じ出来事の中身で動く（GitHub 公式「Re-running workflows and jobs」: "The workflow will also use the same GITHUB_SHA ... of the original event"、Context7 /github/docs で 2026-11-20 確認）。そのため結果は元の head に付く。やり直しの時点で PR の今の head が出来事の head と違えば「新しい push の実行を待つ」と出して落ちる。issue_comment で起動する形は、結果が PR の最新の写しに付かないため使わない。
  - 2つの組に分けた理由（2026-10-20〜11-19 の main への合流で数えた。生の数え: recon の「便7 の数え」）: 15件を全部 PO 本人の GO にすると 43回（週10回ほど）。多いのは migration-test.yml 26回（migration ごとに前提の移行を1手足す形）と check-process-artifacts.js 11回。組A だけなら 8回。組B を Opus の GO で通すと、うっかりの書き換えは止まる。ただし機械は Opus の GO とほかの AI が shingo-cc で書いた GO を区別できないので、わざとの書き換えは組B では止まらない。PO はこれを承知で「1」を選んだ。
  - 守りの強さ（PO 2026-11-20「1」＝間違いを止める関所）:
    - 審査1回目の重1 で分かった事実が2つある。クラウドの GitHub の道具は shingo-ops の名前で動く（get_me の結果）。手元の gh にも shingo-ops の鍵が入っている（`gh auth status` の結果）。
    - このため機械は、AI が shingo-ops の名前で書いた GO と PO 本人の GO を区別できない。
    - PO は3つの案から「1」を選んだ。この関所はうっかりの書き換えを止めるためのもので、AI がわざと PO の名前を使う道は残る。この限界を承知のうえでの選択である。AI 側では便7b の見張りで、その道を使う操作を止める。
    - 選ばなかった案の2は「AI から shingo-ops の鍵を外す」。今の委任の流れ（shingo-ops 名義の Approve。memory の opus_approve_delegation）が壊れるため、採らなかった。
  - 必須チェックに登録: ruleset 15777895 の必須一覧に「guard-files gate」を足す。`integration_id` は 15368（github-actions。2026-11-20 に PR #5610 の head の検査の `app.id` で確認）にする。ほかのアプリや個人が同じ名前の状態を付けても数えない（審査1回目の重2。公式の文書: 「Any person or integration with write permissions ... can set the state of any status check」）。Ruleset の変更は CLAUDE.md の危険操作。PO の名前の鍵で書き込む操作なので、AI は流さない。便7b の手元の見張りは命令の文字しか見ないので、台本のファイルを `bash` で流す道までは止められない（審査3回目の中3。下の便7b の限界に書く）。そのため、Opus は足す前の ruleset を生で保存してから、足した後の JSON と1本の台本を scratchpad に用意する。PO がその台本を `!` で流す（台本は `gh api -X PUT` の1行と、前後の生の保存だけ。PO が `!` で流す書き込みは台本のファイルにする決まり）。流した後に、Opus が必須一覧と integration_id を読むだけの `gh api` で確かめる。
  - 台本の中身（審査2回目の中4）:
    1. 前の保存: `gh api repos/shingo-ops/salesanchor/rulesets/15777895` を shingo-ops の鍵（`GH_TOKEN="$(gh auth token --user shingo-ops)"`）で読み、生で保存する。`bypass_actors` は、その ruleset に書く権限がある人にだけ返る（GitHub 公式 REST「Get a repository ruleset」。Context7 /websites/github_en_rest で 2026-11-20 確認）。PO の鍵なので返る。返りに `bypass_actors` の欄が無ければ、台本は書き込まずに止まる。欄が無いまま PUT したときに bypass_actors が消えるかは確かめていないので、止める側に倒す。続けて、いま読んだ6欄を、Opus が台本を作るときに保存した「前」の6欄と `diff` する。差が1字でもあれば、PUT せずに止まる（Opus が写しを取ってから PO が流すまでに ruleset が変わっていたとき、古い値で上書きしないため。審査3回目の中2）。
    2. PUT で送る欄は、公式「Update a repository ruleset」の本文の6つ（name・target・enforcement・bypass_actors・conditions・rules）だけ。id・source_type・source・node_id・_links・created_at・updated_at・current_user_can_bypass は外す。rules の `required_status_checks` の並びに `{"context": "guard-files gate", "integration_id": 15368}` を1件足すだけで、ほかは前の値のまま。Opus は前の6欄と後の6欄の差がその1件だけであることを `diff` の生出力で確かめてから、台本を PO に渡す。
    3. 鍵: PO が `!` で流すので、PO の手元の gh の shingo-ops の鍵（1 と同じ書き方）。
    4. 後の保存: 1 と同じ GET を流して生で保存する。Opus が2つの保存を `diff` し、差が必須一覧の1件だけであることを確かめる。
    5. 登録の時点で開いている main 向けの PR には、この検査がまだ付いていない。必須の検査が「待ち」のままになり、合流できない。この検査は新しい push か PR の変更（edited・labeled）で動く。Opus は登録の直後に `gh pr list --base main --state open` で一覧を取る。検査が付いていない PR には、shingo-cc の名前でラベル `guard-files-recheck` を付けてから外す（labeled で動く）。ラベルは台本を渡す前に、Opus が1度だけ作る。
  - この workflow 自身を足す PR は、まだ main に無いので自分を守れない → この PR は PO の「GO #番号」で合流する（危険 PR として扱う）。
- 戻し方: ruleset の必須一覧から外す（Opus が台本を用意し、PO が `!` で流す）→ workflow を消す PR。

### 便7b: AI が PO の名前で GO を書く操作を止める（便7 の前に合流）

- なぜ要るか: 便7 の関所は書き手を `user.login` で確かめる。けれども AI も shingo-ops の名前で書ける（便7「守りの強さ」）。便7 の関所は、同じ名前の偽物の検査が付く道も防ぎきれない（便7 の card の判定4）。そこで AI の操作そのものを、操作の前に止める。
- 置き場所は2つ。どちらも今ある仕組みの形に合わせる。
  - 手元（Mac の Opus）の見張り: 新しいフォルダ scripts/agent-hooks/go-identity-guard/（guard.py・guard-manifest.json・test_guard.py）。入れ方は今ある共通の台本 install-guard.sh を使う（docs/handoff/guard-add-by-ai/design.md §6）。形は scripts/agent-hooks/install-form-guard/ と同じ。
    - Bash の `gh auth switch` は全部止める。これを使うと、その後の命令が黙って shingo-ops で動くため。鍵を直接出す道（`gh auth status --show-token`・キーチェーンの `find-generic-password`・`~/.config/gh/hosts.yml`）も止める。`-u shingo-ops` の短い書き方も、`-ushingo-ops` の詰めた書き方も `--user` と同じに扱う。`gh auth token` を含む命令は、名前の有無にかかわらず下の2つの形だけを通す（審査3回目の中5）。
    - Bash の命令に `--user shingo-ops` があるとき、通すのは2つの形だけ。
      - (a) 1つの命令だけの `GH_TOKEN="$(gh auth token --user shingo-ops)" gh pr review <番号> --approve` に、単引用符の `--body '…'` か `--body-file <道>` を付けた形。今の委任の Approve の形で、本文に「GO #」の文字が無いもの。`--body-file` のときはファイルを読んで確かめる。二重引用符の本文は通さない。中の `$(` と `` ` `` をシェルが実行するため（審査2回目の中1）。
      - (b) 読むだけの `gh api`。引数は、決まった少しの印（`--jq`・`-q`・`--paginate`・`--slurp`・`-i`・`--include`・`--silent`・GET だけの `-X`/`--method`）と道の1つだけを許す。それ以外の印が1つでもあれば止める。`-fbody=`・`-XPOST`・`--method=POST` のような詰めた書き方も止まる（審査2回目の中2）。引用符の外の `|` の後ろは別の命令として扱い、PO の鍵は渡らない。引用符の中の `|` では分けない（審査3回目の中4）。
      - これ以外は止める。
    - 見張りの本文は、共通の台本の語の検査（`scripts/dev/consent-audit.py` の `_ga_words_ok`）に当たる語を含まない形で書く。当たると台本が入れない（審査3回目の重1）。
    - Write・Edit で `.github/workflows/` の下の guard-files-gate.yml 以外のファイルに「guard-files gate」の文字を書く操作は止める（便7 の card の判定4 と同じ）。
    - 内部エラーのときは止める。install-form-guard は止めない形（fail-open）だが、この見張りは PO の名前を守るものなので、止める側に倒す。
  - クラウド（Sonnet）の見張り: 新しいファイル scripts/agent-hooks/cloud/go_comment_guard.py。scripts/agent-hooks/cloud/dispatch.sh の PreToolUse の並び（`for G in python_version_guard.py subagent_bash_wait_guard.py`）に1語足す。
    - `mcp__github__` で始まる道具のうち、入力の文字の値（入れ子も）のどこかに `GO #<数字>`（`\bGO\s*#\s*\d`）があれば止める。行の頭に限らない。クラウドが GO を書くことは無いので、道具の名前で絞らない。そのため、名前が変わっても抜けない。
    - Bash の命令に `gh` か `api.github.com` があり、`GO #<数字>` もあれば止める。
    - 同じ命令が本文をファイルで渡すとき（`--body-file`・`-F`/`--field` の `=@`・`--input`・curl の `-d @`/`--data @`/`--data-binary @`/`-T`）は、そのファイルを読んで同じく確かめる。読めないとき、または標準入力（`-`）のときは止める。本文をファイルで渡すのは普段の手順なので、うっかりでも抜けないようにする（審査2回目の中3）。`gh pr comment -F f.md` の短い形も読む（審査3回目の中3）。相対の道は入力の cwd を基に読み、普通のファイルだけを読む（審査3回目の中8）。
    - 書き込みの形の gh・curl の命令に `$(` か `` ` `` があれば止める。`--body "$(cat f.md)"` は命令に GO の文字が出ないため（審査3回目の中10）。
    - Write・Edit の `.github/workflows/` の書き込みは、手元と同じ「guard-files gate」の決まりで止める。Bash には当てない。`grep "guard-files gate" .github/workflows/` のような読むだけの命令を誤って止めないため。Bash で書いたものは、合流の前に便7 の判定4 が落とす。
    - 試験のファイル（scripts/tests/test-guard-files-gate.js）に「GO #12 abc1234」のような文を Write で書くのは止めない。Write の対象は、上の workflow の決まりだけにする。
  - 試験: `.github/workflows/agent-hooks-test.yml` に job を2つ足す（今の install-form-guard test の形と同じ）。作業の指示: card-7b.md。
- 止めきれないもの（限界）:
  - AI が命令を偽装する。たとえば鍵の値を別の変数に移してから `curl` で書く。見張りは文字の形で判定するので、わざと形を変えれば抜けられる。これは PO が「1」で承知した限界と同じ。workflow の名前を `${{ format('guard-files {0}', 'gate') }}` のような式で組み立てると、便7 の判定4 も便7b も文字では見つけられない（審査2回目の軽7）。これも同じ限界に入る。台本のファイルに PO の鍵を使う命令を書き、`bash 台本.sh` で流す道も、命令の文字にファイルの中身が出ないので見張りは止められない（審査3回目の中3）。YAML の二重引用符の中のエスケープ（`"guard-files\x20gate"` など）で名前を書く道も、判定4 の文字の比べでは見つけられない（審査3回目の軽6。推測で、試していない）。どちらも同じ限界に入る。
  - クラウドの MultiEdit は見張りに届かない（`.claude/settings.json:81` の matcher が `Write|Edit`）。手元には GitHub の MCP の道具が無い（2026-11-20 `claude mcp list`）ので札に入れない。後から入れると見張りの外になる（審査3回目の中9・軽）。
  - これを補う後からの点検: PO の名前のコメントのうち「GO #」で始まるものを数え、PO の覚えと合うかを確かめる。今回は作らず、便8 の決まりの文書に「月に1回、Opus が一覧を PO に出す」と書く。
- 戻し方: 手元は settings.json の控えから戻す（install-guard.sh は外す処理を持たないので、PO が `!` で戻す。design.md §8 と同じ）。クラウドは dispatch.sh から1語外す PR を出す。
- 受入: 試験（agent-hooks-test.yml の2つの job が緑）。手元は install-guard.sh で入れた後に、shingo-ops で GO を書こうとする命令を試しに流す。止まることを Opus が生出力で確かめる。止まる命令なので、何も書かれない。

### 便8: 決まりの文書（K11）

- `docs/specs/tenant-rls/README.md:1` に「守り続ける仕組み」の表を足す: |守るもの|見張り|どこで・いつ|落ちたとき|。行は K2（実 PostgreSQL 試験・pytest 必須）・K8（便5・マイグレーションSQL 実行テスト）・K9（便6・毎日 Discord）・K10（便7・guard-files gate）・K10 の補い（便7b・AI が PO の名前で GO を書くのを止める手元とクラウドの見張り）・既存の3つ（生 SET search_path 禁止・ADR-072 lint・salesanchor_app での RLS 試験）。表の下に、守りきれないもの2つを書く。1つ目は、AI がわざと形を変えて PO の名前を使う道（便7「守りの強さ」）。補いとして、月に1回 Opus が PO の名前の「GO #」のコメントの一覧を PO に出す。2つ目は、backend/tests/conftest.py と rls_bootstrap.py が見張りの外にあること（月の合流が約41回で、GO の手間が見合わない。RLS の役を作る test.yml は組B で守る）。
- `docs/ai-agents/executor-checklist.md:1` と `backend/CLAUDE.md` に、その表への1行のリンクを足す（本文は書き写さない）。backend/CLAUDE.md は行数の上限を確かめる。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 オーナーが自社の社員を許可して入れる | 本番: 点検用の会社で社員が新しい機械でログイン→「会社の管理者に頼む」→オーナーが管理センターで許可→社員が入る。依頼が completed・decided_by_user_id がオーナー（ai_ro で読む） |
| K2 他社の依頼は見えない・押せない | `pytest backend/tests/test_tenant_login_requests.py`（実 PostgreSQL・salesanchor_app）: A社オーナーの一覧に B社の依頼 0 件・許可は 404。社員が頼んでいない自社の依頼も一覧に 0 件・許可は 404 |
| K3 オーナー以外は使えない | 同じ試験で一般社員と admin 役は 403。画面の試験で isTenantOwner が偽ならメニューに出ない |
| K4 自分の依頼は許可できない | 同じ試験で 403 `cannot_approve_own_request`。一覧にも自分の依頼は出ない |
| K5 オーナーに知らせが届く | 試験: 頼むと publish とメール送信がオーナーごとに1回、2回目は 0 回。本番: PO の画面で鈴の数字とメール |
| K6 記録が残る | 試験: decided_by_user_id・decided_note・audit_logs の event `login_request_approved_owner` が1行 |
| K7 他社在籍が分からない | `pytest backend/tests/test_staff_create_users.py`: 他社・自社の重複とも同じ文言で「他の会社」を含まない |
| K8 鍵の無い新しい表を止める | `pytest backend/tests/test_check_public_tenant_rls.py`（落ちる見本・通る見本）と、migration-test の新しい手が緑 |
| K9 本番を毎日点検 | 管理者用 Discord に毎日1通。7日続けて緑。数え方: PO が管理者用 Discord の7日分の投稿を画面で見て ○×（Opus が Discord を読めるかは未確認のため、PO の目視を正とする） |
| K10 見張りを外す PR を止める | 見本の下書き PR を2本使う。見本A（組A の allowlist に1行のコメント）: GO 無しで赤／shingo-cc の GO では赤のまま／PO の「GO #番号 <SHA>」の後のやり直しで緑／その後に守るファイルへ1行足して push すると古い GO では赤／守らないファイルだけの push では緑のまま。見本B（組B の migration-test.yml に1行のコメント）: GO 無しで赤／shingo-cc の GO の後のやり直しで緑。守るファイルの名前を変えるだけの見本でも赤。守るファイルを触らない PR では緑。見本C（新しい workflow に「guard-files gate」の名前の job を書く）: PO の GO があっても本物の gate は赤。見本C は PO が `!` で作る（AI 側の見張りが止めるため）。GO を書いた後に書き直したコメントは数えない（見本A で GO を1字直してやり直すと赤）。ruleset の必須一覧に名前があり、integration_id が 15368（gh api の生出力）。見本の PR は確かめた後に閉じる（合流しない） |
| K10 の補い（便7b） | agent-hooks-test.yml の2つの job が緑。手元: shingo-ops で GO を書く命令・`gh auth switch`・workflow に同じ名前を書く操作が止まり、今の委任の Approve の形と読むだけの gh api は通る（Opus が生出力を保存）。クラウド: 見張りの試験を流して同じ確かめ（クラウドの実行記録） |
| K11 文書から見張りに辿れる | tenant-rls README の表の見張りの名前が、ruleset・workflow の名前と一致（Opus が突き合わせ） |
| 運営の許可が壊れていない | 既存の運営の許可の試験がそのまま緑 |
| i18n・UI の決まり | 必須チェック UI governance gate・Lint & Dark Mode が緑。ja/en の鍵が同じ |

---

## 技術 How・KPI

- KPI: 上の K1〜K11 の ○ の数（11/11）。K9 は「7日続けて緑」。
- 技術選択:
  - 会社の絞り込みは依頼の表に列を足さず、public.users と JOIN（理由: 人の正本は public.users・ADR-1008。会社の列を2か所に持たない）。
  - 鈴は表から生で数える（理由: 写しの行を作ると、許可や期限切れのたびに写しを消す処理が要り、ずれる）。
  - 頼んだ印は時刻の列1つ（理由: 状態を増やさない。NULL＝頼んでいない、で足りる）。
  - K10 は pull_request_target（理由: PR 側から変えられない場所で動く仕組みは、GitHub ではこれと Ruleset だけ）。

---

## 弊害・トレードオフ

- オーナーが不正に社員を入れられる → 対策: オーナーは元々その会社の全権を持つ（社員の作成・停止もできる）ため、新しい権限の広がりは無い。記録（K6）と、依頼した本人にも既存の知らせが届くことで後から分かる。
- 社員の場所（だいたいの地域）がオーナーに見える → 対策: 社員がボタンを押したときだけ（PO 決定2）。
- 頼むボタンの悪用（他人の待ち Cookie）→ 対策: Cookie はその機械だけが持つ。1依頼で1回しか知らせない。
- pull_request_target の危険（PR のコードが権限つきで動く）→ 対策: checkout しない・実行しない・権限は読み取りだけ。設計審査と reviewer で workflow の全文を見る。
- 必須チェックが増え、守るファイルを触る PR は GO が要る → 組A は PO 本人（先月の数で 8回）、組B は Opus の GO で通す（PO 2026-11-20「1」）。組B は AI のわざとの書き換えを止められない → 受け入れる（PO 承知の上の選択）。組B の変更は reviewer の審査と Opus の GO 記録に残る。
- 毎日の Discord が1通増える → 受け入れる（黙っていると止まっているのか分からないため）。
- 許可一覧の表が理由なしで増える → 対策: 一覧の各行に理由の文が必須（空なら CI のスクリプトが落ちる）。一覧のファイルは K10 で守る。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 設計審査（クラウドの architect）→ 指摘を直す | Opus（審査はクラウド） |
| 2 | PO に設計と実装の承認を1回で聞く | Opus |
| 3 | 便1 実装カード → 実装 → reviewer → 合流 → 本番で文言を確かめる | クラウド Sonnet・Opus |
| 4 | 便2 migration → PO「GO #番号」→ 合流 → 本番で列があることを確かめる | クラウド Sonnet・Opus・PO |
| 5 | 便3 バックエンド → 試験 K2〜K6 緑 → 合流 | クラウド Sonnet・Opus |
| 6 | 便4 画面 → 合流 → 本番 K1・K5 を PO と確かめる | クラウド Sonnet・Opus・PO |
| 7 | 便5 CI（数える→一覧を確かめる→落とす形へ） | クラウド Sonnet・Opus |
| 8 | 便6 毎日点検（初回の値を PO に報告して固定）→ 7日数える | クラウド Sonnet・Opus |
| 8b | 便7b 手元とクラウドの見張り → 合流（Opus の GO）→ 手元は共通の台本で導入 → 止まることを生出力で確かめる | クラウド Sonnet・Opus |
| 9 | 便7 guard-files gate → PO「GO #番号」で合流 → PO が `!` で台本を流して必須に登録 → 見本 PR で赤を確かめる | クラウド Sonnet・Opus・PO |
| 10 | 便8 文書の表とリンク | クラウド Sonnet・Opus |

便ごとに「変える→本番に出す→測る」を終えてから次へ進む（一度に1つ）。

---

## 継続（維持する仕組み）

- 完了後の監視: K9 の毎日 Discord（緑も送る）。K8 は migration を含む PR のたびに必須チェックで。K10 は見張りのファイルを触る PR のたびに必須チェックで。
- 守り手: 見張りの workflow とスクリプトは便7 の guard-files gate が守る。決まりの表は `docs/specs/tenant-rls/README.md` に1か所。
- 次フェーズへの引き継ぎ: 接続の使い回しの隙・Meta の Page 重複登録（report.md 穴2・穴3）は別の札。オーナーの「見送る」ボタンは要望が出たら別件。

---

## 審査の反映（設計審査1回目 REVISE・クラウドの architect・dc92d5602）

| 指摘 | 重さ | 直したところ |
|---|---|---|
| N1 便5 の置き場所が1周目（2026-06 まで）で新しい表を見ない | 必須 | 便5「置く場所」を全件ドライランの後（jarvis_report）へ |
| N2 ask-admin で会社の文脈が無いとオーナーが0人になる | 必須 | 便3(3) で set_tenant_context → `_owner_user_ids` → clear_tenant_context。試験を追加 |
| N3 オーナーが社員の頼んでいない依頼まで許可できる | 必須 | 便3(2) に `require_admin_requested`。K2 の検証に追加 |
| N4 GO が head に結び付かず、後の push でも通り続ける | 必須 | 便7 の GO を「GO #番号 <SHA>」にし head と一致を要求 |
| N5 守る一覧に除外一覧・ドライランのスクリプト・試験が無い | 必須 | 便7 の一覧に4ファイル追加 |
| N6 ADR の状態欄の字で索引が Accepted と出る | 必須 | ADR-1063 の状態欄を直し、索引を作り直し |
| N7 共通関数の返し方と順番 | 推奨 | 便3(2) に順番と 404/403 の返し方を明記 |
| N8 paths-filter に新しいファイル | 推奨 | 便5「起動の条件」 |
| N9 ask-admin の発行停止と Cookie 無し | 推奨 | 便3(3) |
| N10 K9 の数え方 | 推奨 | 受け入れ基準 K9 を PO の目視に |

設計審査3回目（262a33216）は APPROVE。推奨3件を反映した: M1 名前を変えたファイルを `previous_filename` でも照合（便7）／M2 K10 の確かめ方を「GO #番号 <SHA>」と後からの push・名前の変更に揃えた／M3 頼むボタンの expired と 409 `not_pending` の画面の動き（便4）。

審査で未確認として残った点: クラウドから docs.github.com に届かず、pull_request_target と rerun の動きの公式文書の照合は審査役ができなかった。手元では公式文書を 2026-11-05 に直接確かめた（事例1）。`gh run rerun` で GO 後に緑にできるかは、便7 の見本 PR（K10 の検証）で実測して確かめる。
