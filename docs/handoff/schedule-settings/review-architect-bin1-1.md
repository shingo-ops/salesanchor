# 審査（architect・第1回）— schedule-settings 便1

- 審査した物: `origin/release/google-calendar-disconnect` の `docs/handoff/schedule-settings/` requirements・recon・design（§1〜§5）・card-bin1
- 実物の基準: `origin/main` 88c3fccd1（作業場所を作った時点）
- 方法: 読むだけ。製品のコード・DB・本番・secrets には触れていない。試験は流していない（未確認）

## 判定: REVISE

1. 裏側（取り消しの関数・解除の順・戻り先）は実物と合い、このまま作れる。直す点は無い。
2. 画面に 1 件、作ると壊れる穴がある。管理者で `staff.view` が無い人が設定ページに入ると、読み込みの丸が出たまま止まり、Google 連携の区画が出ない（R1）。K1 が満たせない。
3. 行番号の食い違いが 2 か所あり（L1・L2）、カードだけで作る人が探す場所を誤る。R1 を直せば作れる。

## 必須の直し（R）

### R1 管理者で `staff.view` が無い人は、設定ページが読み込み中のまま止まる

- 実物: `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:42-44` 持ち主一覧の問い合わせは `hasPermission("staff.view")` のときだけ動く。`:45-51` の `loading = !ready && !ownersQ.isError` は、問い合わせが止まっていると `data` が無いまま `ready` が false のままになる（`frontend/src/lib/query/useSeededForm.ts:36` `ready = data !== undefined && …`）。`:121` 付近は `loading` のとき `<LoadingBlock />` だけを出し、画面の本体（左の並び・各区画）を出さない。
- 設計: `design.md` §4-2 の 1 は、入れる条件を `hasPermission("staff.view") || isTenantAdmin` に広げ、持ち主一覧の問い合わせは「今どおり staff.view のときだけ」と書く。§4-2 の 3 は Google 区画を同じ画面の本体に置く。
- 起きること: 管理者（`isTenantAdmin`）で `staff.view` が無い人は、`:96` の関門を通っても `loading` が true のままで、Google 区画が出ない。歯車を管理者にも出す変更（§4-1）は、この人にとって「止まった画面へ入る入口」を増やすだけになる。K1・K2・K3 はこの人で満たせない。
- 直し方（`design.md` §4-2 の 1 に足す）:
  - `loading` を持ち主一覧の区画だけに使う。例: `const ownersEnabled = !permsLoading && hasPermission("staff.view")` を作り、問い合わせの `enabled` と `loading = ownersEnabled && !ready && !ownersQ.isError` の両方に使う。
  - 画面の本体（`SubMenu`・Google 区画）は `loading` で包まず、持ち主の 2 区画（マイ・他）だけを `loading ? <LoadingBlock /> : …` にする。
  - 左の並びの「マイカレンダー」「他のカレンダー」は `ownersEnabled` のときだけ出す（管理者だけの人に空の項目を出さない）。
  - `ScheduleSettingsPage.test.tsx` に「管理者・`staff.view` なし → Google 区画が出て、読み込みの丸が残らず、`/calendar/owners` を呼ばない」を足す（`design.md` §5 の K1 の行）。
- なお、`frontend/src/lib/query/batch3bPages.test.tsx:35` は `usePermissions` を `{ hasPermission: () => true, loading: false }` で差し替えている。`isTenantAdmin` が無いので、直し後も「持ち主の一覧が出る」点は変わらない（K1 の管理者側はこの試験の範囲外）。

## 軽い指摘（L）

- L1 `design.md` §3-3 の「今 `:121`」は誤り。実物は `backend/app/routers/google_calendar.py:106` に `frontend_schedule = …`、`RedirectResponse` は `:112`・`:115`・`:118`・`:154`・`:156` の 5 か所（数は設計どおり）。
- L2 `design.md` §5 の K8 の行「『connect button』3 本（`:53-80`）」は誤り。実物は `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:128-155`（`describe("SchedulePage Google calendar connect button"`）。`?connected=` の試験は `:1356-1384`（S5 の 2 本と G28）で、設計の「`:1340` 付近〜`:1380`」はほぼ合う。
- L3 `design.md` §4-1 の行番号は少しずれる。歯車は `frontend/src/pages/schedule/SchedulePageImpl.tsx:1517-1526`（設計は `:1514-1523`）、`?connected=` を読む処理は `:943-957` 付近。見出しのつなぐボタン `:1448-1458`・`handleGoogleConnect` `:960-969`・`gcalStatusQ` `:832`・`banner` `:842` は合う。探す手がかりは名前で足りるので直しは不要。
- L4 `design.md` §3-1: `backend/app/services/google_calendar.py` は `import httpx` を持たず、`text` も各関数の中で `from sqlalchemy import text` している（`:303`・`:330`・`:360`）。設計は「無ければ足す」と書いているので足りるが、`httpx` は先頭の取り込み（`:27-38`）に足し、`text` は他の関数に合わせて関数の中で取り込むと迷わない。
- L5 `design.md` §3-1: 合鍵が読めない（`decrypt` が失敗）または空のとき、何も取り消さずに戻り、解除は進んで行が消える。画面は「Google 側の許可も取り消しました」（`disconnectSuccess`）と出す。Google 側に許可が残る可能性がある。設計が意図した割り切り（鍵が読めない行は二度と使えない）なので R にはしないが、§9 の危うさの表に 1 行足し、本番の目視（K3）で確かめる範囲を明記するとよい。
- L6 `connectBtnError`（`frontend/src/locales/ja.json:3626`・`en.json:3626`）は、`frontend/src` のどのファイルからも使われていない（grep で json 以外 0 件）。設計は `connectBtn`・`connectBtnConnected` だけを消す。同時に消すか、残すかをカードに書くとよい（どちらでも壊れない）。
- L7 `connectNoticeBody`（`design.md` §4-3）は「・」で区切った 1 つの文字列。`ConfirmModal` の `message`（`frontend/src/components/ConfirmModal.tsx:27` 付近）は 1 つの段落になり、箇条書きに見えない。読めはするので R にはしない。見やすくするなら文字キーを 2〜3 本に分ける。
- L8 `ScheduleSettingsPage` の `useApiQuery("/google-calendar/status", { enabled: isTenantAdmin })`: 実物の `useApiQuery` は `options?.enabled ?? true`（`frontend/src/lib/query/apiQuery.ts:69`）。`batch3bPages.test.tsx` の差し替えは `isTenantAdmin` を返さないので `undefined` となり、その試験では取りに行く。回答は空の一覧で返る（同ファイル `answer`）ため落ちない見込みだが、未確認。`enabled: isTenantAdmin === true` と書くと確実。

## 見る点ごとの結果

### (1) 行番号と変更前の形
- 裏側は合う。`backend/app/routers/google_calendar.py:217-239` の `disconnect`（関数は `:222`、`DELETE FROM tenant_google_calendar_config` → `commit` → `reset_tenant_context` の形）、`backend/app/services/google_webhook.py:164`（`stop_webhook`）・`:181`（`_get_service` の呼び出し）、`backend/requirements.txt:18`（`httpx==0.28.1`）。
- 画面は L1〜L3 のとおりずれがあるが、名前で探せる。

### (2) 解除の順・失敗の扱い・`calendar_events`
- 順序は正しい。`stop_webhook` は `backend/app/services/google_webhook.py:181` で `cal_svc._get_service` を呼び、設定行の合鍵を読む。行を先に消すと止められないため、①が先でなければならない。
- `stop_webhook` は止めるのに失敗しても例外を出さず警告を残し（`:182-190`）、`google_webhook_subscriptions` の行を消して commit し、`reset_tenant_context` まで行う（`:191-197`）。取り消し（②）の失敗後も設定行は残り、`/calendar/sync-mode` からの登録し直しの道は今のまま。設計の記述と合う。
- ②成功後に③の DELETE が落ちても、やり直しで②は 400 `invalid_token`（取り消し済み）となり成功扱い、③が進む。やり直しが安全。穴は無い。
- `calendar_events` は消す対象に無い。③の DELETE は `tenant_google_calendar_config` だけ。`tenant_google_calendar_config` を参照する外部キー・連鎖削除は `backend/app` に無い（同表の参照は `calendar_service.py:53,65`・`google_webhook.py:261`・`backend/app/tasks/google_calendar_sync.py:47`・`backend/app/routers/calendar.py:655,685` の SELECT/UPDATE のみ）。K4 は満たせる。
- RLS: `stop_webhook` は最後に `reset_tenant_context` を呼ぶので、続く `revoke_tenant_token` の SELECT（`tenant_google_calendar_config`）は会社の文脈で読める。

### (3) Google の取り消し口
- 設計の扱い（宛先 `https://oauth2.googleapis.com/revoke`・本文 `token=`・200 成功・400 `invalid_token` は取り消し済み・それ以外は失敗）は、設計が引く公式文書の記述と整合する。この審査では外部へ照会していない（設計 §3-1 の引用を信頼した。未確認）。
- 取り消す対象は合鍵（`refresh_token_encrypted`）。認可の要求は `include_granted_scopes="false"`（`backend/app/services/google_calendar.py:160`）なので、この合鍵が別の範囲の許可を巻き添えにする心配は無い。

### (4) 戻り先と `?connected=` の表示
- `connect_callback` の戻り先 5 か所を揃える変更は足りる（L1 の行番号のみ誤り）。ルート `/schedule/settings` は `frontend/src/App.tsx:297` にある。
- 帯の読み取りは設定ページの描画時に 1 回行い、読み終えたら `setSearchParams({}, { replace: true })` の形（予定ページの `:943-957` と同じ）。R1 を直せば、管理者は `staff.view` が無くても帯を見られる。
- 予定ページの試験の移し先は漏れていない: 「connect button」3 本（L2 の行）・S5 2 本・G28（`SchedulePageImpl.test.tsx:1356-1384`）のすべてを `design.md` §5 の K8 の行が扱う。`frontend/src` の `connectBtn` の使用は `SchedulePageImpl.tsx:1456` と上記試験だけ。

### (5) 管理者でない人に壊れが出ないか
- 歯車の条件を `canManageOwners || isTenantAdmin` にしても、`staff.view` が有る・無い管理者でない人の見え方は変わらない（`staff.view` が有れば従来どおり入れ、無ければ歯車が出ない）。
- 管理者でも `staff.view` が無い人: R1。
- 管理者でも `staff.view` も無い人が URL を直接開く場合は、今の文（`schedule.settingsPermissionRequired`）が出る（`ScheduleSettingsPage.tsx:96-104`）。設計 §9 の手当てと合う。
- 保存の送信を `{ color }` だけにしても、`PATCH /calendar/owners/{user_id}` は 3 つとも任意で、1 つ以上あれば通る（`backend/app/routers/calendar.py:78-82`・`:327-345`）。K9 に穴は無い。
- `ToggleMigration.test.tsx:25` の設定ページの行は外す必要がある（`<Toggle` が 0 件になると、`match(...)?.length` が `undefined` となり `toBe(0)` が落ちるため）。設計の「外す」は正しい。

### (6) 消す文字キーの使用
- `connectBtn`・`connectBtnConnected` を使うのは `frontend/src/pages/schedule/SchedulePageImpl.tsx:1456` と `SchedulePageImpl.test.tsx:132,143,152` だけ（`frontend/src` の ts・tsx・json を grep）。どちらもカードの触るファイルの中で、他では使われていない。
- 足す 8 キーは `ja.json`・`en.json` の `schedule` に既に無い（衝突なし）。使い回す既存 7 キー（`connect`・`disconnect`・`disconnectConfirm`・`statusConnected`・`connectSuccess`・`connectError`・`connectScopeMissing`）は両方にある。`settingsNavigation` も既にある。

### (7) 金型だけで作れるか
- `SubMenu`（`frontend/src/components/SubMenu.tsx`: `variant="flat"`・`onChange`・`activeKey`・`to` 無しなら `<button>`）・`SectionCard`（`title`）・`ConfirmModal`（`danger`・`confirmLoading`・`confirmLabel`）・`Button`（`danger` 有り）はいずれも実物に有る。帯の `success-message`・`error-message` は `frontend/src/components.css:412,421` に有る。
- `.schedule-settings__nav*`（`frontend/src/pages/schedule.css:788-828` 付近）は `ScheduleSettingsPage.tsx:114-125` だけが使う。消してよい。`.schedule-settings__shell` の 2 列（`:778` 付近・`minmax(15rem, var(--schedule-leftpanel-width))`）は SubMenu の置き場として残す。
- 金型に無い部品は要らない。ただし `<input type="color">` が残る点（設計 §4-2 の 6）は、既存の箇所で今回は足さないと設計が明記している。

### (8) 実装者がカードだけで迷わず作れるか
- 裏側は、設計 §3 のコードがそのまま置けて迷わない。
- 画面は R1 の読み込みの扱いが無いと、作った後に止まる。R1 を `design.md` §4-2 に足し、カード「変更5」が参照する範囲に入れれば、カードだけで作れる。
- カードの「触るファイル」は `batch3bPages.test.tsx` を含まないが、確かめの命令にはある。直す必要が出ない見込み（上の L8）で、矛盾ではない。

## 直したあとの再審査
- R1 の 1 件だけなら、`design.md` §4-2 の 1 と §5 の K1 の行を直した差分を、設計の審査役が確認すれば足りる（第2回は不要と考える）。
