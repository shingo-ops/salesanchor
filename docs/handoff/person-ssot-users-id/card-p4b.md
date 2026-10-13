# 実装カード P4b: 名簿のメールはログイン用のメールを表示だけ・名簿の Firebase 識別と users.role の使用をやめる（ADR-1008）

- 設計: docs/handoff/person-ssot-users-id/design.md「P4 の決定」、ADR-1008 決定4。PO 決定（2026-10-13）:
  - P4 の進め方「y」（1段目＝読み書きを正本へ・列は残す、2段目＝列削除は PO の GO #番号）
  - スタッフ画面のメールは表示だけ（書き換え不可）「y」。表示はログイン用の表のメール（users.email）
- 根拠: /tmp/CC報告ファイル/user-ssot/recon-p4.md §2〜§4（origin/main 基準の行番号。P4a #4206 のマージ後は staff.py の行がずれているので必ず実物で確かめる）
- 前提: P4a #4206 が main に入っていること（`gh pr view 4206 --json state` が MERGED。違えば止まって報告）
- ブランチ: release/person-ssot-p4b-email（P4a マージ後の origin/main 起点の新しい worktree）
- 実装役: Sonnet。設計者: Opus。

## 設計判断（実装役は変えない）

1. **メール（staff.primary_email）**
   - 読む: 名簿のメールはすべて users.email（`JOIN public.users u ON u.id = s.user_id`。staff.user_id は NOT NULL）。API の項目名 primary_email は変えない（中身を users.email にする）。
     - backend/app/routers/staff.py の共通列（_STAFF_COLS）・一覧の検索（ILIKE、:535 付近）
     - backend/app/routers/calendar.py:59,172,249,294 付近（名簿・表示名のフォールバック）
     - backend/app/routers/meta_inbox.py:720,737 付近（氏名が空のときのフォールバック）
   - 書く: POST /staff の staff 行には primary_email を書かない（users.email には今までどおり入る）。PATCH /staff で primary_email が来たら 400「メールアドレスはここでは変更できません」（POST の user_id 400 と同じ流儀）。`_UPDATABLE` から外す。
   - migration（構造のみ・冪等・新規1本）: 全テナントの staff.primary_email の NOT NULL を外す。v_senders ビュー（tenant.py:709-719・migrations/020:70-77）の contact_email を users.email の結合で作り直す（`CREATE OR REPLACE VIEW`。列の名前・順・型を今と同じにする。型が違えば今の型にそろえる。作り直せない場合は止まって報告）。tenant.py のひな形の staff 定義（NOT NULL を外す）とビュー定義も同じに。
2. **Firebase の識別（staff.firebase_uid）**
   - 判定・照合に使う箇所は 0 件（recon-p4.md §3-2）。API の入力・出力から外す（schemas/staff.py の StaffCreate・StaffUpdate・StaffResponse の firebase_uid）。_STAFF_COLS・_UPDATABLE・INSERT から外す。値は書かない。
   - frontend: StaffPage・StaffEditPage の型・フォーム状態・送信・入力欄から firebase_uid を外す。使わなくなる i18n キーがあれば ja.json・en.json の両方から外す（他で使っていないことを確かめる）。
3. **古いロール欄（users.role）**
   - 書かない: backend/app/routers/auth.py:79,96 と staff.py の users INSERT（role 'user' の固定値）から外す（列には既定値 'user' がある）。
   - ORM の User モデル（backend/app/models.py:30）から role を外す。schemas/auth.py の UserResponse.role・TokenData.role は、使っている箇所を確かめ、使っていなければ外す（使っていれば止まって報告）。
4. **スタッフ画面のメール欄**（frontend/src/pages/staff/）
   - 編集フォームのメール欄は表示だけ（既存の入力部品の disabled／読み取り専用の属性を使う。新しい部品・色・文言は作らない）。PATCH の送信からメールを外す。
   - 作成フォームのメール欄はそのまま（ログイン用の表のメールになる）。

## 触らない範囲
- 列の削除（P4c）。staff_emails（副メール）。PUT /roles 系。本番 DB のデータ。
- scripts/ と tests/qa-smoke/（P4c の前に別カードで直す）。

## 試験
- 名簿・/staff/me・カレンダーの名簿・Meta チャネル一覧で、メールが users.email から出る（staff.primary_email と違う値を入れた試験で確かめる）
- PATCH /staff で primary_email を送ると 400、users.email は変わらない
- POST /staff で staff.primary_email に書かれない（NULL）、users.email は入る
- firebase_uid を送っても保存されない・応答に出ない
- users の INSERT に role が無くても動く（既定値）
- 既存の試験を新しい意味に合わせて更新（recon-p4.md §2-4・§3-4・§4-4 の一覧）。試験用スキーマの NOT NULL も外す。
- frontend: 関係する vitest（StaffFormButtonMigration 等）、`npm run lint`、`npm run check:i18n-missing-keys`。e2e のモックは API の項目名を変えないので原則そのまま（firebase_uid を含むモックがあれば外す）。
- openapi.json: 変わる部分だけを手で直す（全体再生成はしない）。CI「API contract is up to date」の差分が出たら、その行だけ直す。

## 手順
1. P4a マージを確かめる → `bash scripts/new-worktree.sh release/person-ssot-p4b-email --claude`（作業場所作成後に起動される Claude は止めてよい）→ `./scripts/dev/executor-preflight.sh`。
2. 実装 → 試験・lint の生出力を残す。
3. migration を scripts/run_all_migrations.sh の末尾に登録（P4a の行の後）。
4. `git -C <wt>` 形式で commit（`feat: staff email from users, drop firebase_uid and users.role usage (ADR-1008 P4b)`、末尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）→ push。ruff が見つからなければ PATH に Python の bin を足す（--no-verify 禁止）。PR は作らない。

## 止まる条件
- フック・分類器に止められた → 言い換えず止まって報告。
- 実物がカードと違う／カードに無い読み書きが見つかった／ビューを作り直せない／TokenData.role・UserResponse.role を使っている箇所がある／文言の追加が要る → 報告して止まる。
- 試験が範囲外の理由で失敗 → 止まって報告。
最終報告: git diff --stat、試験・lint の生出力、push 結果、commit SHA。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容>。
