# 実装カード P4a: スタッフ画面のロール＝権限の正本（user_roles）にする・ロール画面から人への付与を外す（ADR-1008）

- 設計: docs/handoff/person-ssot-users-id/design.md §4-P4、ADR-1008 決定4。PO 決定（2026-10-13）:
  - P4 の進め方「y」（1段目＝読み書きを正本へ切り替え・列は残す、2段目＝列削除は PO の GO #番号）
  - 「スタッフ画面で各スタッフのロール権限を設定する、ロール画面はロールごとに出来る権限を設定するページ…」に合意
  - ロール画面から人にロールを付ける部分を外す「y」
- 根拠: /tmp/CC報告ファイル/user-ssot/recon-p4.md §1・§5-6・§9、recon-p4-roles-page.md（origin/main 基準の行番号。必ず実物で確かめる）
- ブランチ: release/person-ssot-p4a-roles（origin/main 起点の新しい worktree）
- 実装役: Sonnet。設計者: Opus。

## 設計判断（実装役は変えない）

1. **名簿のロールの正本は user_roles**。staff.role_id は読まない・書かない（列は P4c まで残す）。
2. **ロールの付与は1か所の関数に集める**（新規 `backend/app/services/role_assignment.py` に `assign_single_role(db, tenant_id, current_user, target_user_id, role_id)`）。中身:
   - ロールが同テナントに存在し、隠すロールでない（今の `_ensure_assignable_role` backend/app/routers/staff.py:124-136 の検査をここへ移す）
   - 付与するロールの priority が自分の最大 priority 以上なら 403（今の PUT /users/{id}/roles backend/app/routers/roles.py:558-563 と同じ。`_max_priority_for_user` roles.py:98-105 を使う）
   - 対象の人の今の最大 priority が自分の最大 priority 以上なら 403（同格以上の人のロールは変えられない。新規）
   - 対象の人の「見えるロール」をすべて外し、指定の1つにする（見えないロール＝super admin 向けの隠しロールは触らない。roles.py:566-573 と同じ考え方）
   - 監査ログ（roles.py:583 と同じ形）と権限キャッシュの破棄（invalidate_user_permissions）
   - commit はしない（呼び出し側のトランザクションで commit）
3. **POST /staff**（staff.py:580-650 付近）: users を決めた後、staff を role_id なしで作り、`assign_single_role` でロールを付ける。staff.role_id には書かない。
4. **PATCH /staff/{id}**（staff.py:665-718 付近）: role_id が来たら `assign_single_role(対象の staff.user_id)`。staff.role_id は更新しない（`_UPDATABLE` から role_id を外す）。role_id の変更には roles.assign 権限も要る（無ければ 403。owner/admin は持っている: 本番確認済み）。
5. **名簿のロール表示**（role_id・role_name の返し方）: staff.role_id の JOIN（staff.py の10か所 :277,359,397,437,545,565,656,671,722,734 付近）をやめ、user_roles から「見えるロールのうち priority が最も高い1つ」を出す。SQL は1か所の共通断片（例 `LEFT JOIN LATERAL (SELECT r.id, r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = s.user_id AND <見えるロールの条件> ORDER BY r.priority DESC, r.id LIMIT 1) rr ON true`）にまとめ、10か所はそれを使う。見えるロールの条件は roles.py の `_visible_role_sql` を使う（同じ判定を2か所に書かない）。レスポンスの項目名 role_id・role_name は変えない。
6. **migration（構造のみ・冪等）**: 全テナントの staff.role_id の NOT NULL を外す（列と外部キーは残す）。tenant.py のひな形（:610）も NOT NULL を外す。値は変えない（本番は staff.role_id と user_roles の食い違い 0 件: recon-p4.md §6）。
7. **ロール画面**（frontend/src/pages/roles/RolesPage.tsx）: 「利用者番号でロールを付ける」部分（状態 :121-124、関数 :306-328、ボタン :367-371、モーダル :549-572）を外す。使わなくなる i18n キー（roles.assignUsers・roles.targetUserId・roles.grantRoles）は、ほかで使っていないことを確かめてから ja.json・en.json の両方から外す。PUT /users/{id}/roles の API は残す（API の形を変えない）が、中身は `assign_single_role` と同じ検査を使う形に寄せられるなら寄せる（複数ロールを受ける形はそのまま。寄せられない場合は触らず報告）。
8. **スタッフ画面**（frontend/src/pages/staff/）: 送る値・表示はそのまま（role_id を送り role_name を出す）。変更不要のはず。変更が要ると分かったら止まって報告。

## 触らない範囲
- staff.primary_email・firebase_uid・users.role（P4b）。列の削除（P4c）。
- ロール画面の「ロールごとの権限」編集（PUT /roles/{id}/permissions）。マネージャーの roles.view（PO「残す」）。
- 本番 DB のデータ。

## 試験
- 新規 test_role_assignment.py（または既存の近い試験ファイル）:
  - スタッフ作成で user_roles に1件でき、staff.role_id は NULL のまま、名簿の role_name は user_roles のロール名
  - PATCH でロール変更 → user_roles が置き換わる（見えるロールは1つ）、権限キャッシュが消える、staff.role_id は変わらない
  - 自分以上の priority のロールを付けようとすると 403、同格以上の人のロールを変えようとすると 403、roles.assign が無いと 403
  - 隠しロールは super admin 以外には付けられない（既存 test_roles_hidden_system_admin.py:156-192 の期待を新しい経路に合わせて更新）
- staff.role_id を前提にした既存試験（recon-p4.md §1-4 の一覧）を新しい意味に合わせて更新。
- frontend: RolesPage の該当部分の試験があれば更新。`npm run lint`・関係する vitest。
- tests/qa-smoke/scene-06.spec.ts:75,79 が `UPDATE tenant_006.staff SET role_id` を直接実行している。この試験が何を確かめているか読み、名簿のロール表示に依存しているなら user_roles を書き換える形に直す。どこで実行される試験か（本番に対してか）分からなければ触らずに報告。

## 手順
1. `bash scripts/new-worktree.sh release/person-ssot-p4a-roles --claude`（~/worktrees/salesanchor/release-person-ssot-p4a-roles）→ `./scripts/dev/executor-preflight.sh`。
2. 実装 → 試験・lint の生出力を残す。
3. `git -C <wt>` 形式で commit（`feat: staff role writes user_roles and roles page drops per-user assign (ADR-1008 P4a)`、末尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）→ push。ruff が見つからなければ PATH に Python の bin を足す（--no-verify 禁止）。PR は作らない。

## 止まる条件
- フック・分類器に止められた → 言い換えず止まって報告。
- 実物がカードと違う／カードに無い staff.role_id の読み書きが見つかった／スタッフ画面の変更が要る → 報告して止まる。
- 試験が範囲外の理由で失敗 → 止まって報告。
最終報告: git diff --stat、試験の生出力、push 結果、commit SHA。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容>。
