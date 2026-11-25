# 設計: スケジュール設定ページの整備（Google 連携の解除を含む）

- 状態: 設計案（Opus 作成）。審査はクラウドで行い、結果を末尾「審査」に記録する
- 要件: `docs/handoff/schedule-settings/requirements.md`（PO 2026-11-25「1」で承認）
- 現在地: `docs/handoff/schedule-settings/recon.md` §1〜§14
- 関わる ADR: ADR-1003（GO 委任）/ ADR-1057（Google から取り込む同期は使わない）/ ADR-1081（予定の色 24 色）/ ADR-144（UI 金型）/ ADR-067（デザイントークン）/ ADR-027（i18n）/ ADR-072（commit 後の reset_tenant_context）/ ADR-135・136（危険 PR の GO）
- 上位の目的: Google OAuth 審査の手順4「解除のしかた」を満たす（`docs/handoff/google-oauth-verification/design.md`）。あわせて設定を 1 ページに集める

## 1 便の分け方

| 便 | 中身 | DB 変更 | GO 手順 |
|---|---|---|---|
| 便1 | Google 連携の区画（状態・つなぐ前の知らせ・つなぐ・解除）、解除で Google の許可を取り消す、見出しのつなぐボタンを外す、死んだ「表示」「共有」欄を隠す、左の並びを金型 SubMenu へ | なし | 通常（CI 緑→審査役→確認済み→マージ） |
| 便2 | 予定の種類を DB へ（色・共有の初期値）、チーム共有 | あり | ADR-136（バックアップ確認つき） |
| 便3 | 人ごとの初期値（開いたときの形・新しい予定の初期値）、人ごとの色を金型へ、死んだ列の削除 | あり | ADR-136 |

便2・便3 は、便1 の本番確認のあとで、この文書に詳しい設計を足し、もう一度審査してから実装する（§6・§7 は骨組み）。

## 2 便1 の目的と受入条件

| 基準 | 内容 | 検証方法 |
|---|---|---|
| K1 | 設定ページに「Google カレンダー連携」区画があり、管理者だけに見える | 画面試験（管理者=見える／staff.view だけ=見えない／管理者で staff.view なし=Google 区画が出て読み込みの丸が残らず `/calendar/owners` を呼ばない）＋本番で PO 目視 |
| K2 | 未接続で「接続する」を押すと、まず知らせの窓が開き、読む・書く範囲と解除の場所が書いてある。「続ける」で初めて Google へ移る | 画面試験（窓が開くまで `/google-calendar/connect/start` を呼ばない） |
| K3 | 解除で Google 側の許可が取り消され、アプリの設定行が消える | 裏側試験（取り消しの POST → 行の削除の順）＋本番で解除後に Google アカウントの「サードパーティのアクセス」から消えたことを PO 目視（要件 G2） |
| K4 | 解除しても取り込み済みの予定は消えない | 裏側試験（`calendar_events` への DELETE を出さない）＋本番で解除前後の予定件数が同じ（読むだけの鍵で数える） |
| K5 | Google の取り消しが失敗したら設定行を残し、失敗の文を出す（やり直せる） | 裏側試験（500 → 502・行を消さない）＋画面試験（失敗の文） |
| K6 | 既に取り消し済み（`invalid_token`）なら成功として扱う | 裏側試験 |
| K7 | つないだ後・失敗した後は設定ページへ戻り、結果の帯が出る | 裏側試験（戻り先が `/schedule/settings`）＋画面試験（帯） |
| K8 | 予定ページの見出しに「Googleカレンダー連携」ボタンが無い | 画面試験 |
| K9 | 設定ページに、保存しても効かない「表示」スイッチと「共有権限」欄が無い。色の保存は今どおり | 画面試験 |
| K10 | 左の並びが金型 SubMenu で、押すとその区画へ移る | 画面試験＋`ui-allow` 無しで UI 点検が緑 |
| K11 | 新しい文字はすべて `t()`、ja/en 同じキー | i18n 点検 |

## 3 便1 の変更（裏側）

### 3-1 取り消しの関数（`backend/app/services/google_calendar.py` に足す）

根拠（Context7 で確認、developers.google.com/identity/protocols/oauth2/web-server「Revoking a token」）:
- `POST https://oauth2.googleapis.com/revoke`、本文 `token=<token>`、`Content-Type: application/x-www-form-urlencoded`
- 合鍵（refresh token）を取り消すと、それで出した入場券（access token）も取り消される
- 成功は 200。失敗は 400 と誤りの符号

```python
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class GoogleRevokeError(Exception):
    """Google が許可の取り消しを受け付けなかった（通信の失敗を含む）。"""


async def revoke_tenant_token(db, tenant_id: int) -> None:
    """接続している合鍵を Google で取り消す（design §3-1）。行が無ければ何もしない。"""
    row = await db.execute(
        text("SELECT refresh_token_encrypted FROM tenant_google_calendar_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    record = row.first()
    if record is None or not record[0]:
        return
    try:
        token = encryption.decrypt(record[0])
    except Exception as e:  # 鍵が読めないなら、こちらでは二度と使えない。解除は進める
        logger.error("revoke: 合鍵を読めない tenant=%s %s", tenant_id, type(e).__name__)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _REVOKE_URL,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as e:
        raise GoogleRevokeError(f"通信の失敗: {type(e).__name__}") from e
    if resp.status_code == 200:
        return
    if resp.status_code == 400 and _error_code(resp) == "invalid_token":
        return  # 既に取り消されている（利用者が Google 側で外した等）
    raise GoogleRevokeError(f"status={resp.status_code} error={_error_code(resp)}")


def _error_code(resp) -> str:
    try:
        return str(resp.json().get("error", ""))
    except Exception:
        return ""
```

- 合鍵の値はどの記録にも出さない（ログは型名と状態番号だけ）。
- `httpx` は `backend/requirements.txt:18`（0.28.1）。`import httpx` はファイル先頭の取り込み（`:27-38`）に足す。`text` は他の関数（`:303`・`:330`・`:360`）に合わせ、関数の中で `from sqlalchemy import text` とする。

### 3-2 解除の受け口（`backend/app/routers/google_calendar.py:217-239` の `disconnect`）

変更前（要旨）: `DELETE FROM tenant_google_calendar_config` → commit → reset。

変更後:
```python
    """Google Calendar 接続を解除する（admin 専用）。

    順番（design §3-2）: ①通知の窓口を止める ②Google で許可を取り消す ③設定行を消す。
    取り込み済みの予定（calendar_events）は消さない（PO 2026-11-25「2」）。
    """
    from app.services import google_webhook as webhook_svc

    await webhook_svc.stop_webhook(db, tenant_id)
    try:
        await cal_svc.revoke_tenant_token(db, tenant_id)
    except cal_svc.GoogleRevokeError as e:
        logger.warning("Google Calendar disconnect: 取り消し失敗 tenant=%s %s", tenant_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="google_revoke_failed",
        )
    await db.execute(
        text("DELETE FROM tenant_google_calendar_config WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
```
- ①を先にする理由: `stop_webhook` は設定行の合鍵で Google に止める指示を出す（`backend/app/services/google_webhook.py:181`）。行を消した後では止められない。`stop_webhook` は自分で commit する。
- 失敗のときは行を残す（K5）。通知の窓口は既に止まっているが、`/calendar/sync-mode` を開き直すと登録し直せる（今と同じ道）。
- `cal_svc`・`HTTPException`・`status`・`logger` の取り込み名は今のファイルに合わせる。

### 3-3 戻り先（同ファイル `connect_callback`、`frontend_schedule = …` は今 `:106` 付近・`RedirectResponse` は `:112`・`:115`・`:118`・`:154`・`:156` 付近の 5 か所）

`frontend_schedule = f"{_frontend_base_url()}/schedule"` を `f"{_frontend_base_url()}/schedule/settings"` に変える。変数名も `frontend_settings` に変え、5 か所の `RedirectResponse` を揃える。

### 3-4 触らない
- `connection_status`・`connect_start`・`/calendar/sync-mode`・同期の仕事（`backend/app/tasks/google_calendar_sync.py`）・`calendar_events`。

## 4 便1 の変更（画面）

### 4-1 予定ページ（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）
- 見出しのつなぐボタン（今 `:1448-1458`）を消す。`gcalConnecting`・`handleGoogleConnect`（`:960-969`）も、他で使っていなければ消す。
- `?connected=` を読む `useEffect`（`:943-958`）を消す（設定ページへ移す）。
- `gcalStatusQ`（`:832`）は Meet の可否に使うので残す。`banner`（`:842`）も Meet の失敗に使うので残す。
- 歯車（今 `:1517-1526` 付近）の条件を `canManageOwners` から `canManageOwners || isTenantAdmin` に変える（管理者が Google 区画へ行けるように）。

### 4-2 設定ページ（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx`）
1. 権限: `usePermissions()` から `isTenantAdmin` も取る。入れる条件を `hasPermission("staff.view") || isTenantAdmin` にする。持ち主一覧の問い合わせ（`:42-44`）は今どおり `staff.view` のときだけ。
   - 読み込み中の扱い（審査 R1）: `const ownersEnabled = !permsLoading && hasPermission("staff.view")` を作り、問い合わせの `enabled` と `loading = ownersEnabled && !ready && !ownersQ.isError` の両方に使う（今の `:45-51` の `loading` を置き換える）。
   - 画面の本体（`SubMenu`・Google 区画）は `loading` で包まない。持ち主の 2 区画（マイ・他）だけを `loading ? <LoadingBlock /> : …` にする（今の `:121` 付近で本体ごと `<LoadingBlock />` にしている形をやめる）。
   - 左の並びの「マイカレンダー」「他のカレンダー」と、その 2 区画は `ownersEnabled` のときだけ出す（管理者で staff.view が無い人に空の項目を出さない）。
   - Google 区画の状態の問い合わせは `enabled: isTenantAdmin === true` と書く（試験の差し替えで `undefined` になっても取りに行かない）。
2. 左の並び（`:114-131`）を金型 `SubMenu`（`frontend/src/components/SubMenu.tsx`、`variant="flat"`、`onChange` で区画へ移る）に変える。項目: Google 連携（管理者だけ）・マイカレンダー・他のカレンダー（今と同じ条件）。`activeKey` は押した項目。CSS の `.schedule-settings__nav*`（`frontend/src/pages/schedule.css:788-828`）は使われなくなったら消す。
3. Google 区画（管理者だけ、最上段、`id="schedule-settings-google"`）: 金型 `SectionCard`（title=`t("schedule.settingsGoogleTitle")`）。
   - `useApiQuery("/google-calendar/status", { enabled: isTenantAdmin === true })`。
   - 未接続: 説明 `t("schedule.settingsGoogleDesc")` と `Button`（`t("schedule.connect")`）。押すと `ConfirmModal`（title=`t("schedule.connectNoticeTitle")`、message=段落 `t("schedule.connectNoticeBody")` と、その下に箇条書き（`ul`/`li`）で `t("schedule.connectNoticeItemEvents")`・`t("schedule.connectNoticeItemColors")`、最後の段落 `t("schedule.connectNoticeStop")`、confirmLabel=`t("schedule.connectNoticeConfirm")`）。確定で `/google-calendar/connect/start` → `window.location.href = auth_url`。
   - 接続済み: `t("schedule.statusConnected")` と、接続日時（`connected_at` を今の日付の書式の関数で）、`Button variant="danger"`（`t("schedule.disconnect")`）。押すと `ConfirmModal danger`（title=`t("schedule.disconnectConfirm")`、message=`t("schedule.disconnectNotice")`、`confirmLoading`）。確定で `api.delete("/google-calendar/connect")` → 状態を読み直し → 成功の帯 `t("schedule.disconnectSuccess")`。失敗は `t("schedule.disconnectError")`。
4. 結果の帯: `?connected=true|false&error=` を読む処理を予定ページから移す（文の選び方は今と同じ。`scope_missing` なら `connectScopeMissing`）。読み終えたら `setSearchParams({}, { replace: true })`。帯は今の画面の `success-message` / `error-message`（`frontend/src/components.css:421` ほか、既存の共通の決まり）。
5. 死んだ欄を外す（K9）: 自分・他人の両方の行から `Toggle`（表示）と `SelectControl`（共有権限）を消す。保存は `{ color }` だけ送る（`backend/app/routers/calendar.py:79-82` は 3 つとも任意なので通る）。`ToggleMigration.test.tsx:25` の設定ページの行は数が 0 になるので外す。
6. 色の `<input type="color">` は今回は触らない（便3 で金型へ。既存の箇所で、今回足すものではない）。

### 4-3 新しい文字（`ja.json` / `en.json` の `schedule` の中、同じキーを両方）

| キー | ja | en |
|---|---|---|
| settingsGoogleTitle | Google カレンダー連携 | Google Calendar connection |
| settingsGoogleDesc | 会社の Google カレンダーとつなぐと、アプリで作った予定が Google にも入ります。 | Connect your company's Google Calendar so events made in the app also appear in Google. |
| connectNoticeTitle | Google カレンダーとつなぐ前に | Before you connect Google Calendar |
| connectNoticeBody | つなぐと、このアプリは次のことをします。 | Once connected, this app will: |
| connectNoticeItemEvents | あなたのカレンダーの予定を読み、作り、直し、消す（アプリで扱う予定だけ） | Read, create, edit and delete events on your calendar (only the ones the app handles) |
| connectNoticeItemColors | カレンダーの色の設定を読む（変えません） | Read your calendar's color settings (without changing them) |
| connectNoticeStop | つなぐのをやめたいときは、この設定ページの「接続を解除する」で Google の許可も取り消せます。 | To stop, use "Disconnect" on this settings page, which also revokes the Google permission. |
| connectNoticeConfirm | Google の画面へ進む | Continue to Google |
| disconnectNotice | Google 側の許可も取り消します。これまでに入った予定はアプリに残ります。 | This also revokes the permission on Google's side. Events already in the app are kept. |
| disconnectSuccess | 接続を解除しました。Google 側の許可も取り消しました。 | Disconnected. The Google permission was also revoked. |
| disconnectError | 接続を解除できませんでした。少し時間をおいて、もう一度お試しください。 | Could not disconnect. Please wait a moment and try again. |
| settingsConnectedAt | 接続した日時 | Connected on |

使い回す既存キー: `connect`・`disconnect`・`disconnectConfirm`・`statusConnected`・`connectSuccess`・`connectError`・`connectScopeMissing`（`ja.json` の `schedule` に既にある）。使われなくなる `connectBtn`・`connectBtnConnected` は両方の言語から消す。`connectBtnError` は今もどこからも使われていない（審査 L6）ので、同時に両方の言語から消す。

## 5 便1 の試験

| 基準 | 試験 |
|---|---|
| K3・K4 | `backend/tests/test_google_calendar.py` の `TestRouterDisconnect` を書き直す: `stop_webhook` → `revoke_tenant_token` → 行の DELETE の順に呼ばれる。`calendar_events` を含む SQL を出さない |
| K5 | 取り消しが `GoogleRevokeError` → 502・`detail="google_revoke_failed"`・DELETE も commit も呼ばない |
| K3（関数） | `revoke_tenant_token`: 200 → 戻る／400 `invalid_token` → 戻る（K6）／400 他 → 例外／500 → 例外／通信失敗 → 例外／行が無い → POST しない／読めない合鍵 → POST せず戻る。POST の本文が `token=<値>` で宛先が `_REVOKE_URL`。httpx は差し替えて外へ出さない |
| K7 | 受け取り口の戻り先が成功・失敗とも `/schedule/settings?` で始まる（今の callback の試験の場所を書き換える） |
| K1・K2・K5・K7・K9・K10 | 新しい `frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`: 管理者に Google 区画／staff.view だけなら無い／管理者で staff.view なし→Google 区画が出て読み込みの丸が残らず `/calendar/owners` を呼ばない（審査 R1）／未接続で押すと窓→確定まで connect/start を呼ばない→確定で呼ぶ／接続済みで解除→ `api.delete("/google-calendar/connect")`→成功の文／解除失敗→失敗の文／`?connected=true` で成功の帯、`?connected=false&error=scope_missing` で許可一部の文／「表示」スイッチと「共有権限」欄が無い／並びが SubMenu |
| K8 | `SchedulePageImpl.test.tsx` の「connect button」3 本（`describe("SchedulePage Google calendar connect button"`、今 `:128-155` 付近）を、「見出しにつなぐボタンが無い」1 本に置き換える。`?connected=` の試験（S5 の 2 本と G28、今 `:1356-1384` 付近）は設定ページの試験へ移す。G28（帯の閉じるボタン）は Meet の失敗の帯で同じことを確かめる形に変えるか、設定ページへ移す（帯の部品が同じなら設定ページ側で） |
| K11 | i18n の点検（`frontend/CLAUDE.md` の grep） |

## 6 便2（骨組み・詳しい設計は便1 の本番確認後）

- 新しい表 `calendar_categories`（テナントごと）: `key`・`name`（NULL なら今の i18n の名前）・`color_key`（ADR-1081 の 24 色、`backend/app/services/event_colors.py` が正本）・`default_share`（`self`/`all`/`team`）・`default_team_ids` は別の表・`sort_order`・`is_active`。今の 7 種を最初の行として入れる。
- チーム共有: 予定とチームの対応表（1 つの予定に複数チーム可。1 チームだけの使い方はその一部として満たせるため。PO「チームを選ぶ」の範囲内の設計判断）。`calendar_type` に `team` を足す。見える条件は「全員」「本人」「その予定のチームに入っている人」（`teams`・`team_members`、`backend/app/services/tenant.py:530-548`）。
- 種類の固定の CHECK（`tenant.py:1579`）と画面の固定表（`frontend/src/features/schedule/calendars.config.ts:3-62`）を、表 1 つへ寄せる（正本 1 か所）。
- 種類を選ぶと色と共有が初期値で入る（あとで変えられる）。色は `color_key` に入れるので Google への色の送り（ADR-1081）はそのまま効く。
- 受入: 要件 G4・G5・G6（今の見え方の件数が前後で同じ）。

## 7 便3（骨組み）

- 新しい表 `calendar_user_preferences`（人ごと）: 初期の表示・週の始まり・新しい予定の長さ・Meet を自動で付けるか・開いたときに見える人（自分/全員/チーム）。今の固定値（recon §7）がそのまま初期値。
- 人ごとの色を金型の色の選び方へ。
- 使われていない `is_visible`・`share_mode`（`tenant.py:1609-1619`）を消す。
- 受入: 要件 G7。

## 8 代替案

| 案 | 採らない理由 |
|---|---|
| 解除で行だけ消す（今のまま） | Google 側に許可が残り、審査の手順4（解除で許可が外れる）を満たさない |
| 取り消しが失敗しても行を消す | 合鍵がアプリから消え、二度と取り消せなくなる。やり直せる形にする |
| つなぐ・解除を見出しのボタンのまま | 設定を 1 か所に集める PO の方針（要件 G1）に反する |
| GoogleCalendarStatusBar を使う | どこからも使われておらず、状態を自分で問い合わせて親と二重になる。SectionCard＋既存の問い合わせで足りる |

## 9 危うさと手当て

| 危うさ | 手当て |
|---|---|
| 解除を押した後、Google が取り消しを反映するまで少し時間がかかる（公式に記載） | 成功の文は「取り消しました」とし、本番の目視は数分おいて見る |
| 管理者でない社員が歯車を押すと、今は入れない画面 | 条件を staff.view または管理者に揃え、どちらでもなければ今の文を出す |
| 予定ページの帯の試験が減る | 設定ページへ同じ形で移す（§5） |
| 合鍵が読めない・空の行は、取り消さずに行だけ消え、画面は「取り消しました」と出す（審査 L5）。Google 側に許可が残ることがある | 読めない合鍵は二度と使えないための割り切り。本番の目視（K3）で Google の「サードパーティのアクセス」から消えたかを必ず見る。残っていれば PO がそこで手で外す |

## 10 外部事例

- Google カレンダー自身の設定画面（support.google.com/calendar/answer/6084644）は、表示・通知・共有を 1 つの設定ページの左の並びで分けている。今回の「1 ページ・左に区画」の形の参考。日付は未確認。数値の根拠には使わない。
- 取り消しの手順は Google の公式文書（上の §3-1）に従う。

## 11 維持の仕組み

- 解除の順番は裏側の試験で固定（順が崩れると落ちる）。
- 見出しにつなぐボタンが戻らないことは画面の試験で固定。
- 文字は i18n の点検、部品は UI の点検（ADR-144）と色の点検（ADR-067）が CI で毎回走る。

## 12 審査

- 第1回（クラウド Sonnet・architect、2026-11-25）: REVISE。記録は `review-architect-bin1-1.md`（枝 `release/schedule-settings-review1`）。必須の直し R1（管理者で staff.view が無い人が読み込み中のまま止まる）1 件、軽い指摘 L1〜L8。
- 直し: R1 を §4-2 の 1 と §5 の K1 に入れた。L1・L2・L3（行番号）、L4（取り込みの場所）、L5（§9 に 1 行）、L6（`connectBtnError` も消す）、L7（知らせの文を 4 キーに分け箇条書き）、L8（`enabled: isTenantAdmin === true`）も入れた。
- 第2回: 直しの差分だけをクラウドで確かめる（結果は下に足す）。
