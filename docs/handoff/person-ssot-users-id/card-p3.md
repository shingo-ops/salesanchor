# 実装カード P3: 名簿の行を user_id で引く・スタッフ追加で users と user_roles も作る・staff.user_id を必須に（ADR-1008）

- 設計: docs/handoff/person-ssot-users-id/design.md §3・§4-P3（PO 承認 2026-10-13「y」）、docs/adr/ADR-1008-person-ssot-users-id.md 決定2・5
- 根拠: /tmp/CC報告ファイル/user-ssot/recon-p3.md（origin/main 基準・行番号の出典。実物で必ず確かめる）
- ブランチ: release/person-ssot-users-id-p3（origin/main 起点の新しい worktree）
- 実装役: Sonnet。設計者: Opus。

## 設計判断（実装役は変えない）

1. **名簿の行は user_id で引く**（current_user.id）。メールの一致で引く処理は残さない。本番の6行は全行 email 一致かつ user_id ありなので、引ける行は今と同じ（recon-p3.md §6）。
2. **スタッフ追加（POST /staff）は1つのトランザクションで**:
   - primary_email と同じ email の users を探す（大文字小文字を区別しない: `lower(email) = lower(:email)`）。
     - 同じテナントにあり、その user_id の名簿行がまだ無い → その users に紐付ける（新しく作らない）。
     - 同じテナントにあり、すでに名簿行がある → 409（既存の重複 409 と同じ流儀の文言）。
     - 別のテナントにある → 409「このメールアドレスは他の会社で使われています」。
     - 無い → users を作る: tenant_id=現テナント、email=primary_email、username と full_name = `surname_jp || ' ' || given_name_jp`、role='user'（旧列の既定値）、is_active=true。
   - staff を user_id 付きで作る（リクエストの user_id は使わない。受け取っても無視せず、指定があれば 400「user_id は指定できません」）。
   - user_roles に (user_id, role_id) が無ければ追加する。
   - Firebase のアカウントは作らない（範囲外。ログインできるようにする手順は従来どおり）。
3. **staff.user_id を NOT NULL に**（migration＋ひな形）。
4. **やらない**: staff.status と users.is_active の連動、名簿行の削除時の users の扱い、PATCH /staff の role 変更と user_roles の同期、Firebase アカウント作成。理由: 意味が別（在籍とログイン可否）でPO判断が要る／P4 の重複列の整理で扱う。

## 変更するファイル

### migration（新規1本・構造のみ・冪等）
`migrations/20261013_120000_staff_user_id_not_null.sql`
- 全テナント（pg_namespace `^tenant_[0-9]+$`）で、staff 表と user_id 列があるときだけ:
  - user_id が NULL の行が1行でもあれば `RAISE WARNING` で件数を出してそのテナントは飛ばす（デプロイを止めない。反映後に設計者が本番で is_nullable を確かめる）。
  - 0 行なら `ALTER TABLE %I.staff ALTER COLUMN user_id SET NOT NULL`（すでに NOT NULL なら何も起きない）。
- `scripts/run_all_migrations.sh` 末尾に登録（P2 の行の後）。

### backend/app/services/tenant.py
- staff の CREATE（:600 付近）の `user_id INTEGER UNIQUE REFERENCES public.users(id)` に NOT NULL を付ける。
- **先に確認**: テナント作成（create_tenant_schema とその呼び出し元 backend/app/routers/admin.py）で staff 行を INSERT しているか。しているなら止まって報告（user_id を入れる設計が要る）。

### backend/app/routers/staff.py
- GET /staff/me（:239-250）、PATCH /staff/me/profile（:332-343）、`_my_staff_id_and_token`（:398-412）: `primary_email = :email` → `user_id = :uid`（current_user.id）。メール空の 401 分岐は不要になる（user_id は必ずある）。
- locale・theme の読み書き（:120, :130, :277, :301）: users を email で引いている箇所を `id = :uid` に。
- POST /staff（:556-623）: 設計判断2のとおり。既存の 400（role_id 不正）・409（重複）はそのまま。
- 新しい文言は backend の HTTPException の detail（日本語1文・既存の流儀）だけ。frontend の文言は増やさない。

### backend/app/schemas/staff.py
- StaffCreate の user_id（:59-90 の中）は残す（API の形を変えない）が、POST で指定されたら 400（設計判断2）。

### backend/app/routers/leads.py
- `_resolve_staff_identity`（:2077-2083）: 引数を email から user_id に変え、`WHERE user_id = :uid`。呼び出し元 :2192・:2363 は `current_user.id` を渡す。

### backend/app/routers/calendar.py
- `_current_staff_row`（:56-69）: `user_id = :uid OR primary_email = :email` → `user_id = :uid` のみ。

### 試験（backend/tests）
- conftest.py:343 の staff.user_id を `INTEGER NOT NULL`（UNIQUE・REFERENCES は SQLite 側の既存の書き方に合わせる）。
- user_id を入れずに staff を INSERT している試験（test_discord_inbox.py:406、test_discord_staff_send.py:111、test_order_commissions.py:399、test_staff_avatar.py:61、test_staff_me.py の5か所）に user_id を入れる（その試験のログインユーザーの id か、試験内で作る users の id）。
- test_staff_me.py: email 引き前提の3本を user_id 引きの検証に書き換え。
- 追加（test_staff_create_users.py 新規）: POST /staff で
  - 新しいメール → users 1行・staff 1行・user_roles 1行ができ、staff.user_id = 新 users.id、users.is_active = true
  - 同テナントの既存 users（名簿なし）のメール → users は増えず、その id に紐付く
  - 同テナントで名簿ありのメール → 409
  - 別テナントの users のメール → 409、users・staff・user_roles とも増えない
  - user_id 指定 → 400
- 試験用スキーマで staff に user_id 列が無いもの（recon-p3.md §5 の7ファイル）は、その試験が名簿を引く処理を通るなら列を足す。通らないなら触らない（失敗した試験だけ直す）。

### 文書
- docs/handoff/person-ssot-users-id/card-p3.md（本カード）・recon-p3.md（/tmp/CC報告ファイル/user-ssot/ からコピー）を add。

## 触らない範囲
- frontend（StaffPage は user_id を送っていないので変更不要。新しい文言・部品なし）
- staff.status と users.is_active、DELETE /staff、PATCH /staff の role、Firebase、/auth/register
- scripts/data_migration/migrate_staff_from_sheet.py（過去の一回限りの移行スクリプト。触らない）
- 既存 migration ファイル、列名、本番 DB

## 手順
1. `bash scripts/new-worktree.sh release/person-ssot-users-id-p3 --claude`（~/worktrees/salesanchor/release-person-ssot-users-id-p3）→ `./scripts/dev/executor-preflight.sh`。
2. 実装 → backend の関係する試験（staff・staff_me・staff_avatar・staff_create_users・discord_inbox・discord_staff_send・order_commissions・calendar・message 系）を流し、生出力を残す。可能ならローカル PostgreSQL の使い捨て DB で migration を2回流す（NULL 行ありのテナントで WARNING・飛ばすことも確かめる）。
3. commit（`feat: staff rows keyed by user_id and created with users (ADR-1008 P3)`、末尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）→ push。PR は作らない。

## 止まる条件
- フック・分類器に止められた → 言い換えず止まって報告。
- 実物がカードと違う／カードに無い「メールで名簿を引く」箇所が見つかった／テナント作成で staff を INSERT している → その箇所を報告して止まる。
- 試験が範囲外の理由で失敗 → 止まって報告。
最終報告: git diff --stat、試験の生出力、push 結果、commit SHA。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容>。
