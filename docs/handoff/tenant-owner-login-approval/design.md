<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 会社の持ち主が自社の社員のログインを許可する／会社の分け方の見張り

**対象ADR**: ADR-1063（新規）、ADR-1055（改訂）  
**recon**: docs/handoff/tenant-owner-login-approval/recon.md  
**KGI**: docs/handoff/tenant-owner-login-approval/kgi.md（PO 承認済み 2026-11-05「1」）  
**日付**: 2026-11-05  
**担当**: Planner（Claude Opus）  
**状態**: 設計案作成済み。設計審査1回目 REVISE（必須6・推奨4）を反映済み（§審査の反映）。再審査前。PO の実装承認前。

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
| 7 | 見張りのファイルを変える PR を止める（pull_request_target）＋必須チェックへの登録 | K10 | .github/workflows/ ＋ Ruleset 変更 → PO の permit-danger |
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

- 待ち画面 `frontend/src/pages/login/LoginPage.tsx:300` 付近: 「会社の管理者に頼む」ボタンを、いつもの機械や控えの番号の有無にかかわらず出す（社員が自分の機械を持っていないときもあるため）。既存の `Button`（variant="outline" size="auth" shape="pill" fullWidth）を使う。押した後は結果の文を `Callout` で出す（requested / already_requested / no_owner の3つ）。いつもの機械も控えも無いときの文 `login.deviceApproval.noTrustedDevice` は「会社の管理者に頼むか、運営に連絡してください。」に改める。
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
  - 起動は `pull_request_target`（types: opened, synchronize, reopened, edited, labeled）。基のブランチ（main）の定義だけが動く。
  - PR のコードを checkout しない・実行しない。`gh api repos/{repo}/pulls/{n}/files --paginate` で変わったファイル名だけを読む。権限は `contents: read`・`pull-requests: read`。
  - 守るファイルの一覧はこの workflow の中に直接書く（PR 側から変えられない場所に置くため）: `.github/workflows/test.yml`・`.github/workflows/lint-tenant-schema.yml`・`.github/workflows/migration-test.yml`・`.github/workflows/workflow-lint.yml`・`.github/workflows/process-artifacts-gate.yml`・.github/workflows/guard-files-gate.yml 自身・`scripts/lint_tenant_schema.py`・`scripts/check-process-artifacts.js`・`scripts/migration-dryrun-report.py`・`scripts/migration-guard/dryrun-exclusions.tsv`・scripts/check_public_tenant_rls.py・backend/app/ops/tenant_rls_allowlist.py・backend/app/tasks/tenant_isolation_daily_check.py・K2 の試験 backend/tests/test_tenant_login_requests.py・K8 の試験 backend/tests/test_check_public_tenant_rls.py。
  - 一覧のファイルが変わっていたら、PR に shingo-ops が書いた「GO #番号 <SHA>」のコメントがあるときだけ通す。番号はその PR と一致し、SHA（7文字以上）は今の PR の head の SHA（`github.event.pull_request.head.sha`）の先頭と一致すること。GO の後に push すると head が変わるので、新しい GO が要る（古い GO で後から足した変更を通さない）。無ければ落ちる。コメントの書き手は API の `user.login` で確かめる（本文の文字だけで信じない）。
  - コメントを書いても pull_request_target は動き直さない。GO のコメントの後は、落ちた実行を `gh run rerun` でやり直す（やり直しは同じ PR の検査として結果が付く）。issue_comment で起動する形は、結果が PR の最新の写しに付かないため使わない。この点は設計審査で GitHub の文書と照らして確かめる。
  - 必須チェックに登録: ruleset 15777895 の必須一覧に「guard-files gate」を足す。Ruleset の変更は CLAUDE.md の危険操作 → PO に `bash scripts/permit-danger.sh` を頼み、Opus が `gh api` で足す。足す前後の ruleset を生で保存する。
  - この workflow 自身を足す PR は、まだ main に無いので自分を守れない → この PR は PO の「GO #番号」で合流する（危険 PR として扱う）。
- 戻し方: ruleset の必須一覧から外す（permit-danger）→ workflow を消す PR。

### 便8: 決まりの文書（K11）

- `docs/specs/tenant-rls/README.md:1` に「守り続ける仕組み」の表を足す: |守るもの|見張り|どこで・いつ|落ちたとき|。行は K2（実 PostgreSQL 試験・pytest 必須）・K8（便5・マイグレーションSQL 実行テスト）・K9（便6・毎日 Discord）・K10（便7・guard-files gate）・既存の3つ（生 SET search_path 禁止・ADR-072 lint・salesanchor_app での RLS 試験）。
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
| K10 見張りを外す PR を止める | 見本の PR（守るファイルを1行変える下書き PR）で guard-files gate が赤、PO の「GO #番号」コメント後に緑。ruleset の必須一覧に名前がある（gh api の生出力） |
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
- 必須チェックが増え、守るファイルを触る PR は PO の GO が要る → 受け入れる（PO の言葉「機械的な仕組み」どおり。対象は見張りのファイルだけ）。
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
| 9 | 便7 guard-files gate → PO「GO #番号」で合流 → PO の permit-danger で必須に登録 → 見本 PR で赤を確かめる | クラウド Sonnet・Opus・PO |
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

審査で未確認として残った点: クラウドから docs.github.com に届かず、pull_request_target と rerun の動きの公式文書の照合は審査役ができなかった。手元では公式文書を 2026-11-05 に直接確かめた（事例1）。`gh run rerun` で GO 後に緑にできるかは、便7 の見本 PR（K10 の検証）で実測して確かめる。
