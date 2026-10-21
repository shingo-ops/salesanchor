# recon: 閲覧者管理の詳細欄に「送る文を選んでコピー」を置く

基準: `origin/main` 67e5ea6b9（2026-10-21 fetch 後）。調査は Sonnet、要点の照合は Opus。生出力: /tmp/CC報告ファイル/template-copy-recon/（recon_raw.md・stage10_11.md・pr4581.diff）、/tmp/CC報告ファイル/template-drawer-recon/。

## PO の依頼（原文、2026-10-21）
「データブロックの行をクリックしたときの下部の余白にテンプレートをコピーするボタンを設置してその人専用のメッセージを送れるように出来る？」→ 案の提示に PO「1」（一番下に「送る文を選ぶ」欄と「コピー」ボタンを1つずつ。対象はその人の内容で埋められる6つ）。

## 既存の決め（ADR・設計）
- 文面ひな形の正本は DB `public.viewer_message_templates`（`backend/app/services/viewer_message_templates.py:3-4`）。設計の正本は `docs/handoff/gas-viewer-fresh-fast/design.md` 段10（:838-892）・段11（:905-1012）。
  - :838 管理画面は API が返す出来上がりの文を表示・コピーするだけで、フロントに文面を持たない。
  - :941 行が無い・読めないときは 503「テンプレートが見つかりません」。コードの定数へ戻す道は作らない。
- ADR-1019（閲覧ページ別アカウント）に文面ひな形の記述は無い。ADR-144（UI 金型）・ADR-027（i18n）が画面側の決め。
- `git grep -i "viewer_message_templates" origin/main -- docs/adr` は 0 件。

## 文面の台帳（`backend/app/services/viewer_message_templates.py`）
- :39-49 LEDGER 9件。差し込み項目: signup_request(signup_url) / room_recreated(email) / notice_extended(until_date) / notice_activated() / notice_suspended() / interview_request(expires_date) / reissue_notice(line_name,code,expires,invite_url) / reissue_notice_no_invite(line_name,code,expires) / room_welcome(email,password)。
- :66-89 validate（差し込み項目の集合が台帳と完全一致・書式指定なし・1800字まで）。:92-104 build_copy_text は signup_url だけ埋め、他は `{…}` のまま。
- main には 1 つの鍵を読んで差し込む関数が無い。

## 並行中の PR #4581（段11 便2、別セッション、OPEN・2026-10-20 15:27Z 起票）
- 同じ service・router・`frontend/src/pages/super-admin/ViewerAccountsPage.tsx`・locales・tests を触る（pr4581.diff）。
- 追加される関数: `load_body(db,key)`・`render(key,body,**values)`・`load_rendered(db,key,**values)`（pr4581.diff:463-517）。行なし・検査不合格・差し込み失敗は None。自動送信の文は差し込み後 2000 字超で None。
- 自動送信側（延長・本登録・停止・面談・部屋の作り直し・はじめの案内）を DB 読みに替え、申込のお願い API も DB 読み＋行なしは 503 にする（pr4581.diff:315-322）。
- → 本機能はこの `load_rendered` を使うのが筋。#4581 のマージ後に main から作る。

## 自動送信が入れる値（コピーの文を自動送信と同じにする条件）
- `backend/app/discord_gateway/viewer_bot_texts.py:121` format_jst_date = JST「M月D日」（ゼロ埋めなし）。:68 SIGNUP_URL。
- 延長: `backend/app/services/viewer_room_notice.py:44-57` until_date=format_jst_date(trial_expires_at)、期限なしは文なし。
- 面談: `backend/app/discord_gateway/viewer_interview_notice.py:80` expires_date=format_jst_date(trial_expires_at)。
- 部屋の作り直し: `backend/app/discord_gateway/viewer_trial.py:206` email=viewer_accounts.email そのまま。
- 本登録・停止: 差し込みなし。

## 1 人分のデータ（`backend/app/routers/super_admin_viewers.py`・`backend/app/services/viewer_admin.py`）
- 全エンドポイント `require_super_admin`。ViewerAdminItem :47-61（email・line_name・status・trial_expires_at(datetime|None) ほか）。
- 1 人を取る関数 `viewer_admin._get_item(db, viewer_id)`（viewer_admin.py:121、無ければ ViewerAdminError("not_found")→404）。再発行の処理（router :279）が直接呼ぶ前例あり。1 人分の GET は無い。
- 申込コードは sha256 のみ保存（復元不可）、招待リンクは保存しない、初期パスワードは argon2 のみ → 作り直し案内 2 種・はじめの案内は埋められない（対象外）。

## 本番データ（reader 鍵、2026-10-20 15:33Z）
- `SELECT key, length(body), updated_at FROM ai_ro.public__viewer_message_templates` → 9 行すべてあり（rows=9、updated_at 2026-10-20 14:49:22Z）。

## 画面（`frontend/src/pages/super-admin/ViewerAccountsPage.tsx`）
- 詳細の Drawer :425-515、footer :429-443 は保存ボタン（data-testid viewers-detail-save）だけ。
- コピーの仕組み: copyText :188-196（clipboard→copiedKey 2 秒）、copyButton :361-365。
- Select は未使用。金型 `frontend/src/components/Select.tsx`（options{value,label,disabled?}・placeholder・size・error・helperText）。使用例 `frontend/src/pages/leads/LeadsPage.tsx:304-312`。
- i18n: `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の superAdmin.viewerTemplates（:2668〜、names.<鍵> に 9 件の名前あり）、superAdmin.viewers（:2723〜、copy・copied・genericError ほか）。
- テスト: `frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx`（api の get/post/patch を mock、get は path で分岐、未知の path は {items:[]}）、`backend/tests/test_super_admin_viewers.py`（ROUTES :36-44 が全ルートの 403 を検査、実 DB は _prepare :135・_api :210）。
