# 段11 便2 recon（実装後の実物。file:line は便2 の HEAD 基準）

設計: `docs/handoff/gas-viewer-fresh-fast/design.md`（段11、11-10 が優先）。審査: `docs/handoff/gas-viewer-fresh-fast/stage11/review_design.md`・`docs/handoff/gas-viewer-fresh-fast/stage11/review_design2.md`。着手前の実物は `docs/handoff/gas-viewer-fresh-fast/stage11/recon.md`・`docs/handoff/gas-viewer-fresh-fast/stage11/recon2.md`。

## 読む処理の位置（B-2：後戻りできない処理より前に読む）
- 申込コード入力：`backend/app/discord_gateway/viewer_trial.py:282` で room_welcome を読む（申込コードを使用済みにする DELETE は `backend/app/discord_gateway/viewer_trial.py:294`）。差し込みは `backend/app/discord_gateway/viewer_trial.py:339`（commit は `backend/app/discord_gateway/viewer_trial.py:400`）。
- 部屋の作り直し：`backend/app/discord_gateway/viewer_trial.py:198` で room_recreated を読む（commit は `backend/app/discord_gateway/viewer_trial.py:219`）。
- 申込コードの作り直し：`backend/app/routers/super_admin_viewers.py:320` と `backend/app/routers/super_admin_viewers.py:321` で2本文を読み、`backend/app/routers/super_admin_viewers.py:325` の reissue_signup_code より前に置く。無ければ 503。
- 申込のお願い：`backend/app/routers/super_admin_viewers.py:171`（db 依存を追加。無ければ 503）。
- 延長・本登録・停止（API）：`backend/app/routers/super_admin_viewers.py:248` で文を作り、commit は `backend/app/routers/super_admin_viewers.py:249`、送るのは `backend/app/routers/super_admin_viewers.py:255`（commit の後）。
- 延長・本登録・停止（CLI）：`backend/app/viewer_admin_cli.py:29`（作る）→`backend/app/viewer_admin_cli.py:30`（commit）→`backend/app/viewer_admin_cli.py:32`（送る）。
- 部屋のお知らせの共通部：`backend/app/services/viewer_room_notice.py:49`（prepare_notice）・`backend/app/services/viewer_room_notice.py:69`（notify_prepared。no_template を返す）。
- 面談のお願い：`backend/app/discord_gateway/viewer_interview_notice.py:73` で run_once の最初に1回読む。

## 台帳
- 読み出し・差し込み・保存：`backend/app/services/viewer_message_templates.py`（load_body / render / load_rendered / save_body）。PUT は `backend/app/routers/super_admin_viewers.py` に追加。

## 画面
- 編集・保存：`frontend/src/pages/super-admin/ViewerTemplatesPage.tsx`。no_template の表示：`frontend/src/pages/super-admin/ViewerAccountsPage.tsx`。

## 削除の確認
- 9定数の残り：`git grep -n -E "^(SIGNUP_REQUEST|REISSUE_NOTICE|REISSUE_NOTICE_NO_INVITE|ROOM_WELCOME|ROOM_RECREATED|NOTICE_EXTENDED|NOTICE_ACTIVATED|NOTICE_SUSPENDED|INTERVIEW_REQUEST) =" HEAD -- backend/app` は0件。viewer_template_cli への残参照は migration の SQL コメントと docs のみ（migration は触らない）。
