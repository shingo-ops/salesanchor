# 予定の設定の画面 — 現在地（recon・2026-11-25・origin/main ea800930e 基準）

## 1. 要件の有無
- 仕様書 docs/specs/schedule/（README・ideal-state・kgi・to-be・track-record）に設定の画面の記載は 0 件（「設定」「settings」「歯車」で検索）。
- docs/adr/FEATURE-INDEX.md:52 のカレンダーの行にも設定の画面の記載なし。

## 2. 画面の今
- 道: frontend/src/App.tsx:297 `/schedule/settings` → frontend/src/pages/schedule/ScheduleSettingsPage.tsx（243行）
- 入口: frontend/src/pages/schedule/SchedulePageImpl.tsx:1516-1526 歯車（`staff.view` の権限がある人だけ・:831）
- 中身: 人ごとに「色・表示・共有（自分だけ/見られる/直せる）」と保存ボタン（ScheduleSettingsPage.tsx:149-235）
- 手作りの部品: 色の欄 `<input type="color">`（:155・:211）、目次の `<button>`（:117・:125）。ui-allow の注記なし。決まった部品 ColorSwatchPicker・NavItemList・SectionCard は frontend/src/components/ にある

## 3. 設定が効いているか
- 色: 効いている。予定の画面の左の人の一覧の印に使う（SchedulePageImpl.tsx:570・:599）
- 表示: 保存はされる（backend/app/routers/calendar.py:329-330）。予定の画面は読まない（SchedulePageImpl.tsx に owner.visible の参照 0 件・最初は自分だけを表示 :927）
- 共有: 保存はされる（calendar.py:331-337）。どこでも使われない（backend/app で share_mode は calendar.py の保存と返しと、表の定義 backend/app/services/tenant.py:1613・:1616 だけ）
- 保存先: 会社ごとの表 calendar_owner_settings（tenant.py:1609-1619）

## 4. Google 連携
- 「Google とつなぐ」ボタンは予定の画面の上の帯（SchedulePageImpl.tsx:1447-1458・会社の管理者だけ）。つないだ後は灰色で押せない（:1453）
- 押すとすぐ Google の画面へ（:960-969）。つなぐ直前の知らせ 0 件
- 外す口 DELETE /google-calendar/connect（backend/app/routers/google_calendar.py:217-232）は画面から呼ばれない（frontend/src で 0 件）。許可の取り消しなし・知らせの登録も止めない・取り込んだ予定は残す
- 知らせの登録を止める処理 stop_webhook は backend/app/services/google_webhook.py:164 にある（呼び元は calendar.py:705 の取り込み方の変更だけ）
- 取り込み方の口 GET/PATCH /calendar/sync-mode（calendar.py:647・:663）は画面から呼ばれない

## 5. PO の決定
- 2026-11-25「2」: 外したら Google の許可を取り消す。取り込んだ予定は残す
- 2026-11-25: 外すボタンは歯車の設定の画面に置く。設定の画面は要件から整える

## 6. Google の決まり（2026-11-25 全文を読んだ）
- 要らない許可は取り消し、記録も消す（developers.google.com/identity/protocols/oauth2/policies）
- 扱いを全部書く・見方と消し方の案内・頼まれたら消す・画面の中でつなぐ直前に知らせる（developers.google.com/workspace/workspace-api-user-data-developer-policy）
- 外したら消す義務はなし

## 7. 決め打ちの値（設定にできる候補）
- 開いたときの表示の形: 週で固定（SchedulePageImpl.tsx:838 `useState<ScheduleView>("week")`。形は day/threeDay/week/month/list の5つ schedule-utils.ts:4）
- 週の始まり: 日曜で固定（SchedulePageImpl.tsx:1615 `weekStart={0}`。部品の初期値は月曜 CalendarView.tsx:68）
- 開いたときに出す人: 自分だけで固定（SchedulePageImpl.tsx:927）
- 新しい予定の長さ: 1時間で固定（schedule-utils.ts:301・:455）
- Meet: 毎回手で付ける（ScheduleDraftFields.tsx:60-80）
- 時刻の目盛り: 1時間で固定（CalendarView.tsx:253）

## 8. ほかの画面の予定の設定
- アカウント設定・API連携の画面に予定の設定は 0 件（frontend/src/pages/account-settings・integrations を calendar/schedule/予定 で検索）
- API連携には Google ドライブの画面がある（frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx・つなぐ/外すあり :66・:79）

## 9. PO の方針（2026-11-25）
- 予定の画面に関わる設定だけを、この設定の画面に集める。設定を変えるときはこの画面で完結させる（1か所）。初期値と Google 連携を設定する画面

## 10. 外部事例
- Google カレンダーの設定（support.google.com/calendar/answer/6084644）: 歯車→設定→全般に、週の始まり・表示の形・予定の長さの初期値・時間帯を置く。予定の長さは利用者の設定が会社の設定より優先（support.google.com/a/answer/9347087）。いずれも検索結果の要約で、本文の日付は未確認

## 11. 予定の種類と共有（2026-11-25 追記）
- 種類は7つで固定: 商談 meeting・個人 personal・仕入 procurement・発送 shipping・請求 billing・発売 release・休み holiday。一覧が2か所にある: 画面 frontend/src/features/schedule/calendars.config.ts:3-62 と、表の決まり backend/app/services/tenant.py:1579（calendar_events_category_check）
- 種類ごとの色: 画面の札の色で固定（calendars.config.ts の badgeVariant）。予定そのものの色は1件ずつ Google の24色から選ぶ（color_key・tenant.py:1581・ADR-1081）
- 共有の今: 予定1件ごとに「社員にも見せる」（ScheduleDraftFields.tsx:391-412）→ 見せる=社内の全員（calendar_type shared）・見せない=自分だけ（personal）。これは効いている（backend/app/services/calendar_service.py:242-244 で他人の personal は返さない）
- 種類を「個人」にすると自動で「見せない」になる（ScheduleDraftFields.tsx:288）。ほかの種類は決まりなし
- 人を選んで共有する仕組みは無い（全員か自分だけの2つ）

## 12. PO の希望（2026-11-25）
- 種類の設定と、種類ごとの色分けをしたい。何に時間を多く使っているか分かるように
- 共有も設定できるようにし、種類ごとに「だれと共有するか」の初期値を付けたい

## 13. 種類ごとの共有を DB で持てるか（2026-11-25 追記）
- 見せ方の値 calendar_type（shared/personal）を使う場所: backend 5 ファイル（routers/assistant.py・routers/calendar.py・schemas/assistant.py・services/tenant.py・services/calendar_service.py）、frontend 8 ファイル（秘書チャット 3・予定の画面 5）
- 共有の相手にできる集まりは既にある: teams（tenant.py:530）・team_members（:542）・roles（:494）・user_roles（:520）
- calendar_owner_settings（tenant.py:1609-1619）の share_mode（self/view/edit）は人ごとの値で、種類ごとではない。どこからも読まれない（§3）
- 種類の一覧は画面（calendars.config.ts）と表の決まり（tenant.py:1579）の2か所に重なっている → 種類を1つの表にまとめれば、1か所になる

## 14. PO の決定（2026-11-25）
- 共有の相手は「自分だけ」「全員」「チームを選ぶ」の3つ（PO「1」）
- チームは既にある: 表 teams・team_members（tenant.py:530-548）、管理の画面 frontend/src/pages/teams/TeamsPage.tsx・TeamEditPage.tsx、口 backend/app/routers/teams.py。1人が複数チームに入れる（UNIQUE(team_id, user_id)）
