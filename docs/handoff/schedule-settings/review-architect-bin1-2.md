# 審査（architect・第2回）— schedule-settings 便1

- 審査した物: 直しの差分 `git diff ac424e291 594acdb90 -- docs/handoff/schedule-settings/`（`design.md`・`card-bin1.md`）
- 前回: `origin/release/schedule-settings-review1` の `docs/handoff/schedule-settings/review-architect-bin1-1.md`
- 実物の基準: `origin/main` 88c3fccd1
- 方法: 読むだけ。製品のコード・DB・本番・secrets には触れていない。試験は流していない（未確認）

## 判定: APPROVE

1. R1（管理者で staff.view が無い人が読み込み中のまま止まる）の直しは、実物の `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:42-51`・`frontend/src/lib/query/useSeededForm.ts:30` と矛盾せず、止まりを解く形で入っている。
2. L1〜L8 はすべて文書に入っている（下の表）。直しが新しい穴・衝突・金型外の部品を作った所は見つからなかった。
3. 必須の直し（R）は無い。軽い指摘（L）が 3 件あるが、直さなくても作れる・壊れない。

## R1 の確認（実物との突き合わせ）

- `design.md` §4-2 の 1 は `ownersEnabled = !permsLoading && hasPermission("staff.view")` を問い合わせの `enabled` と `loading = ownersEnabled && !ready && !ownersQ.isError` の両方に使う。
  - 実物の今の形は `ScheduleSettingsPage.tsx:42-44`（`enabled: !permsLoading && hasPermission("staff.view")`）と `:51`（`loading = !ready && !ownersQ.isError`）。`ready` は `useSeededForm.ts:30` で `data !== undefined && …`。問い合わせが止まっていると `data` が無く `ready` は false のまま。
  - 直し後は `ownersEnabled` が false のとき `loading` が false になるので、止まらない。`enabled: false` の問い合わせは `isError` にならない（実物 `:56` の `shownError` も出ない）。
- 本体を `loading` で包まない・持ち主の 2 区画だけ `loading ? <LoadingBlock /> : …` にする、は実物 `:110-112`（本体ごと `LoadingBlock`）を置き換える指示として足りる。
- `permsLoading` の間は `:92-94` の早期 return が今のまま効き、`usePermissions` の `loading` は `isPending`（`frontend/src/hooks/usePermissions.ts:27`）なので、権限の応答前に「権限が無い」文が一瞬出る心配は無い。
- `isTenantAdmin` は `frontend/src/hooks/usePermissions.ts:25,50` が返す（`data?.is_tenant_admin === true`）。設計が `usePermissions()` から取る前提は実物と合う。
- `design.md` §5 の K1 の行（管理者で staff.view なし → Google 区画・丸が残らない・`/calendar/owners` を呼ばない）と、`design.md` §2 の K1 の検証欄、`card-bin1.md` 変更5 が揃って R1 を指す。
- `frontend/src/lib/query/batch3bPages.test.tsx:35` の差し替え（`isTenantAdmin` 無し）でも、`isTenantAdmin === true` が false となり状態の問い合わせは動かない。持ち主の一覧は従来どおり出る。

## L1〜L8 が入ったか

| 指摘 | 入った所 | 結果 |
|---|---|---|
| L1 行番号（`:106`・5 か所） | `design.md` §3-3 の見出し | 入った |
| L2 試験の場所（`:128-155`・`:1356-1384`） | `design.md` §5 の K8 | 入った |
| L3 歯車の行番号 | `design.md` §4-1 | 入った |
| L4 取り込みの場所 | `design.md` §3-1 | 入った |
| L5 読めない合鍵の割り切り | `design.md` §9 の表に 1 行 | 入った（本番の目視 K3 で確かめる旨も書いてある） |
| L6 `connectBtnError` | `design.md` §4-3 と `card-bin1.md` 変更6 | 入った。実物でも `frontend/src` の ts・tsx に使用 0 件（`connectBtn` の使用は `SchedulePageImpl.tsx:1456` と `SchedulePageImpl.test.tsx:132,143,152` だけ） |
| L7 知らせの文を分ける | `design.md` §4-3 の表（4 キー）と §4-2 の 3 | 入った。`ConfirmModal` の `message` は `ReactNode`（`frontend/src/components/ConfirmModal.tsx:9`）なので段落＋箇条書きを渡せる |
| L8 `isTenantAdmin === true` | `design.md` §4-2 の 1・3 | 入った |

## 新しい穴の点検

- i18n キーの衝突: 足す 12 キー（`settingsGoogleTitle`・`settingsGoogleDesc`・`connectNoticeTitle`・`connectNoticeBody`・`connectNoticeItemEvents`・`connectNoticeItemColors`・`connectNoticeStop`・`connectNoticeConfirm`・`disconnectNotice`・`disconnectSuccess`・`disconnectError`・`settingsConnectedAt`）のうち、`frontend/src/locales/ja.json`・`en.json` に既にあるものは grep で 0 件（`connectNotice*`・`settingsGoogle*`・`disconnectNotice`・`disconnectSuccess`・`disconnectError`・`settingsConnectedAt` で確認）。使い回す既存キー `connect`・`disconnect`・`disconnectConfirm`・`statusConnected`・`connectSuccess`・`connectError`・`connectScopeMissing`・`settingsNavigation`・`settingsPermissionRequired` は `schedule` 区画に有る（`frontend/src/locales/ja.json:3403,3479-3484,3587,3629`）。ほかの区画の同名キー（`ja.json:457,1458-1461,1485` など）とは区画が別で衝突しない。
  - 注: 前回の「足す 8 キー」は L7 の分割で 12 キーに増えた。
- 金型外の部品: 設計が使うのは `SubMenu`・`SectionCard`・`ConfirmModal`・`Button` と、既存の帯 `success-message`・`error-message`。`SubMenu` は実物に `variant`・`activeKey`・`onChange`・`items` がある（`frontend/src/components/SubMenu.tsx:27,33,35,36`）。`ConfirmModal` は `danger`・`confirmLoading`・`confirmLabel` を持つ（`:12,16,10`）。新しい部品は足されていない。
- 実物 `ScheduleSettingsPage.tsx:135-181` の `<input type="color">` は残る（設計 §4-2 の 6 のとおり、今回は足さない）。

## 軽い指摘（L）

- L1 `design.md` §4-2 の 3 は `ConfirmModal` の `message` に生の `ul`/`li` を使う。実物の設定ページには `ul` が無い（`ScheduleSettingsPage.tsx` で確認）。`ConfirmModal` の本文は `<div style={{ lineHeight: 1.6 }}>` で、`ul` の既定の余白・点は共通 CSS の `reset` 次第（未確認）。実装役は作った後に目で確かめ、点が出ない場合は既存の箇条書きの書き方（他の画面の `ul` の使い方）に合わせるとよい。生の `ul` が `CC_UI_GOVERNANCE.md` の禁止に当たるかは未確認。当たるなら、1 段落に戻すか、既にある部品に替える。
- L2 `design.md` §4-2 の 1 は「左の並びの 2 項目と 2 区画は `ownersEnabled` のときだけ出す」と書く。実物 `:122` の「他のカレンダー」は `otherOwners.length > 0` の条件付き。`ownersEnabled` かつ従来条件の両方を満たすときに出す、と読めば足りるが、カードの文面に「従来の条件は残す」と一言あるとなお迷わない。
- L3 `design.md` §4-2 の 1 は、管理者で `staff.view` が無く、`ownersEnabled` が false の人の左の並びに「Google 連携」だけが残る。1 項目だけの `SubMenu` は見た目が寂しいが、壊れない。気になるなら PO の判断（今回は直さなくてよい）。

## 見ていないこと

- 試験・型検査・i18n の点検は流していない（作る段階の確かめ）。
- Google の取り消し口の外部仕様は、前回同様に設計の引用を信頼した（未確認）。
