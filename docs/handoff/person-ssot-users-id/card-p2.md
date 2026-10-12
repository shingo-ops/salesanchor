# 実装カード P2: 残りの「人」を指す列を public.users(id) 参照にする（ADR-1008）

- 設計: docs/handoff/person-ssot-users-id/design.md §4（PO 承認 2026-10-13「y」）・§4-P2 補足
- 根拠: docs/handoff/person-ssot-users-id/recon-p2.md（全行番号の出典。origin/main 8a421f22c 基準）
- ブランチ: release/person-ssot-users-id-p2（origin/main 起点の新しい worktree。P1 #4174 とは別 PR）
- 実装役: Sonnet。設計者: Opus。

## 設計判断（実装役は変えない）

1. **列名は変えない（案A）**。理由: scripts/run_all_migrations.sh は毎デプロイ全件を流し直す（:12）。列名を変えると migrations/041:42,47・migrations/20260602_200000:14 が旧名列を作り直し、migrations/050:145-146 の索引作成が列なしで失敗してデプロイが止まる（recon-p2.md §0-1）。列名の変更は ADR-1005（1回だけ流す方式）の後に別途行う。
2. 列の中身を staff.id から users.id に変える。外部キーを public.users(id) に付け直す。名簿の氏名などが要る箇所は `staff s ON s.user_id = <列>` で結ぶ。
3. 書き込み側は、メールから staff を引く処理をやめ、`current_user.id`（ログイン中の users.id）を直接使う（backend/app/routers/discord_oauth.py:115 が前例）。
4. 画面で人を選ぶ部品は、GET /staff の応答の `user_id` を値に使う（backend/app/schemas/staff.py:147-150 に含まれる）。user_id が null の名簿行は選択肢から外す（D1 実行後は 0 行）。
5. API の項目名（owner_staff_id・staff_id・connected_by_staff_id など）は変えない。ただし `PATCH /calendar/owners/{staff_id}` のパス引数は `{user_id}` に改め、users.id を受ける。
6. 外部キーの ON DELETE: bots.owner_staff_id は NO ACTION（現状どおり。NOT NULL のため）、order_commissions.staff_id は SET NULL、calendar_owner_settings.staff_id は CASCADE、tenant_meta_config.connected_by_staff_id・meta_messages.sent_by_staff_id・seen_by_staff_id は SET NULL（前例 migrations/076_add_google_calendar_config.sql:21）。

## 変更するファイル

### migration（新規1本・構造のみ・冪等）
`migrations/20261013_110000_repoint_person_columns_to_users.sql`
- 全テナント（pg_namespace `^tenant_[0-9]+$`）で、表が存在するときだけ（to_regclass で確認、無ければその表を飛ばす）:
  - bots(owner_staff_id)、order_commissions(staff_id)、calendar_owner_settings(staff_id)、tenant_meta_config(connected_by_staff_id)、meta_messages(sent_by_staff_id)、meta_messages(seen_by_staff_id)
  - 表があっても列が無ければ飛ばす（information_schema.columns で確認。CI の .github/workflows/migration-test.yml は列の無い表を事前に作ることがある。P1 #4174 のレビュー HIGH-1 と同じ）。
  - その列の外部キーのうち参照先が staff(id) のもの（pg_get_constraintdef が `FOREIGN KEY (<列>) REFERENCES` で始まり `staff(id)` を含む）を外す。
  - 名前 `fk_<表>_<列>_user` の外部キーが無ければ `REFERENCES public.users(id)`＋上記 ON DELETE で付ける。
- 値の INSERT/UPDATE/DELETE は書かない（値の付け替えは D3）。
- P1 の migration（migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql）と同じ書き方にそろえる。
- `scripts/run_all_migrations.sh` 末尾に登録（P1 の行の後）。P1 #4174 が先に main に入るので、ブランチ作成は P1 マージ後の origin/main から。

### backend/app/services/tenant.py（新規テナントのひな形）
- :678 bots.owner_staff_id → `REFERENCES public.users(id)`（索引 :688 はそのまま）
- :1086 tenant_meta_config.connected_by_staff_id → `REFERENCES public.users(id) ON DELETE SET NULL`

### backend/app/routers/bots.py（recon-p2.md §2-1）
- JOIN（:89,110,183,202,232,263,278）`s.id = b.owner_staff_id` → `s.user_id = b.owner_staff_id`
- :126-134 存在確認を `SELECT id FROM public.users WHERE id = :uid AND tenant_id = :tid` に。文言は「指定の担当者はこのテナントに存在しません」。更新（PATCH）で owner_staff_id が来るときも同じ確認を通す（現状 PATCH に確認が無ければ足す）。

### backend/app/routers/order_commissions.py（§2-2）
- JOIN（:162,183,212,230,518）`s.id = oc.staff_id` → `s.user_id = oc.staff_id`
- :240-250 `_validate_staff` を users（同テナント）の確認に。
- :160 の is_employee は引き続き staff から（`s.user_id = oc.staff_id`）。

### backend/app/routers/calendar.py（§2-3）
- :174-186・:296-305 `cos.staff_id = s.id` → `cos.staff_id = s.user_id`
- :215-217 パス `/calendar/owners/{user_id}`、:249-258 対象の名簿行を `WHERE user_id = :user_id` で引く。:267-284 の INSERT は staff_id 列に user_id の値を入れる。
- レスポンス（OwnerRosterItem・OwnerRosterResponse）は形を変えない。
- `_current_staff_row`（:56-）は触らない（P3）。

### backend/app/routers/meta_inbox.py（§2-4）
- :311・:457 の `_resolve_staff_id(...)` 呼び出しを `current_user.id`（その関数で使えるログイン中の users.id）に置き換え、`_resolve_staff_id`（:106-126）を削除（呼び出し元はこの2か所だけ）。
- :748・:765 の JOIN を `s.user_id = tmc.connected_by_staff_id` に。

### backend/app/routers/leads.py（§2-5）
- mark-read :1167-1180、Meta テキスト :1931-1944、Meta 画像 :2705-2717 の「メール→staff.id」を `current_user.id` に置き換える（SQL の引き直しをやめる）。
- Discord テキスト :2217-2223・添付 :2390-2396: `_resolve_staff_identity` は送信者名と avatar のために残す。sent_by_staff_id に入れる値だけを `current_user.id` にする（identity.staff_id を入れない）。
- 読み出し（:990-1038）は項目名・形とも変えない。

### backend/app/routers/staff.py
- :713 付近の 409 の文言に `bots.owner_staff_id` とあるなら、外部キーの変更後も意味が通る文言に（「この担当者は他のデータから参照されているため削除できません」）。

### 試験（backend/tests）
- conftest.py:397（bots）・:613（order_commissions）の REFERENCES を users に。
- test_order_commissions.py: 指定値を「staff の id」から「その staff の user_id（users.id）」に。同テナント外の users → 422 を1件追加。
- test_message_send.py:699・test_messages.py:489（メール→staff 解決を検証していた試験）を「current_user.id が入る」検証に書き換え。
- test_meta_channels.py:361 など値の意味が変わるもの。
- test_calendar_owner_api.py: パス引数が user_id になったことに合わせる。
- test_rls_tenant_meta_config.py:111 の FK 行。
- 追加: bots の作成で別テナントの users → 422、同テナント → 成功（bots の API 試験は現在無い。新規 test_bots_owner_users.py）。

### frontend（金型・デザイントークン順守。新しい部品・色・文言は作らない）
- frontend/src/pages/bots/BotFormFields.tsx:22-27 BotStaff に `user_id: number | null`。:47-50 options を `staff.filter(s => s.user_id != null).map(s => ({ value: String(s.user_id), ... }))`。
- frontend/src/pages/bots/BotsPage.tsx:250-252 の option も同じく user_id を value に、null を除外。
- frontend/src/pages/bots/BotEditPage.tsx: 値の扱いは BotFormFields に従う（:52 の初期値はサーバーの owner_staff_id＝users.id のまま）。
- frontend/src/components/CommissionPanel.tsx:51-57 StaffMini に `user_id`、:111-116 value を user_id、null 除外。
- frontend/src/pages/schedule/ScheduleSettingsPage.tsx:88-92 PATCH パスを `owner.userId` に。userId が null の行は保存操作を出さない（既存の disabled の仕組みがあればそれを使う。無ければ保存処理の先頭で何もしない）。
- 試験: SharedButtonMigration.test.tsx:42・frontend/tests-e2e/order-commission.spec.ts の staffList に user_id を足し、選ぶ値を user_id に。BotFormButtonMigration.test.tsx は値の意味のみ（必要なら）。
- frontend/api-contract/openapi.json: パス `/api/v1/calendar/owners/{staff_id}` → `{user_id}` の部分。CI「API contract is up to date」のログの差分の行だけを直す（全体再生成はしない）。

### 文書
- docs/handoff/person-ssot-users-id/recon-p2.md（/tmp/CC報告ファイル/user-ssot/recon-p2.md をコピーして add）、card-p2.md。

## 触らない範囲
- 列名の変更（RENAME）、既存 migration ファイルの編集
- staff_emails・staff_ui_preferences（名簿の付属表）
- calendar.py の `_current_staff_row`、staff.py の名簿の引き方、POST /staff（P3）
- public.tenant_discord_config（すでに users.id が入っている。列名は ADR-1005 後に）
- 本番 DB

## 手順
1. P1 #4174 が main に入っていることを `gh pr view 4174 --json state` で確かめる。入っていなければ止まって報告。
2. `bash scripts/new-worktree.sh release/person-ssot-users-id-p2 --claude`（作業場所は ~/worktrees/salesanchor/release-person-ssot-users-id-p2）。`./scripts/dev/executor-preflight.sh`。
3. 実装 → backend の関連試験（bots・order_commissions・calendar・meta・messages・discord）と frontend の `npx tsc --noEmit`・関係する vitest・`npm run lint`（frontend/package.json の scripts に従う）を流し、生出力を残す。
4. commit（`feat: repoint person columns to public.users (ADR-1008 P2)`、末尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）→ push。PR は作らない。

## 止まる条件
- フック・分類器に止められた → 言い換えず止まって報告。
- 実物がカードの行番号・内容と違う／カードに無い参照箇所が見つかった → その箇所を報告して止まる（自分で範囲を広げない）。
- 試験が範囲外の理由で失敗 → 止まって報告。
