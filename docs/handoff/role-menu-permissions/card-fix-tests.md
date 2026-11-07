# 実装カード（追加）: 古い画面を前提にした試験 2 本を新しい画面に合わせる

| 項目 | 内容 |
|------|------|
| 枝 | release/role-menu-permissions（この枝の先頭に足す。新しい枝は作らない） |
| 起点の commit | d2f3a62a189b16526ed549e8d9319d6befd39a60 |
| 理由 | CI「Frontend unit tests（内部）」が 2 件落ちた（2358 件通過・2 件失敗、run 42370309909）。どちらも役割の画面のチェック欄（`role="checkbox"`）と許可の説明文を探しているが、新しい画面は 3 択の切替（`role="radiogroup"` の中の `role="radio"`）で、行の名前はメニュー名になった |
| 区分 | A の続き（試験だけ。製品コードは変えない） |

## 1. 直すファイル（この 2 つだけ）

- `frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx` の試験「role permission cancel restores the server baseline and writes zero」（34〜38 行）
- `frontend/src/lib/query/batch3ePages.test.tsx` の `permissionBox`（140〜141 行）と試験「keeps the role permission boxes disabled until that role's permissions are read」（143〜156 行）

触らない: 製品コード（`frontend/src/pages/roles/` と `frontend/src/components/` の .tsx・.ts・.css）・locale・他の試験。試験の準備部分（許可は `customers.view` 1 件だけ）も変えない。

## 2. 新しい画面での見え方（Opus が実物で確かめた事実）

- 許可が `customers.view` 1 件だけのとき、その鍵は行 `crm` に入る（`frontend/src/constants/menuPermissions.ts` の `ROLE_ROWS`。行の鍵は存在する許可だけに絞られる: `frontend/src/pages/roles/rolePermissionRows.ts:63`）。
- 行の名前は `t(rowMenuLabelKey("leads"))`（`frontend/src/pages/roles/RolesPage.tsx:212-213`）。切替は `role="radiogroup"` で、`aria-label` は行の名前（`frontend/src/pages/roles/RolesPage.tsx:422-428`）。
- 切替の中の 3 つは `role="radio"`。`aria-label` は `t("roles.stateOff")`・`t("roles.stateView")`・`t("roles.stateEdit")`。選ばれているものは `aria-checked="true"`（`frontend/src/components/SegmentedToggle.tsx:44-65`）。
- 鍵が見る許可 1 件だけなので、状態は「表示のみ」。「編集可」はいつも押せない（`canSetEdit` が偽）。鍵が 1 件なので「個別」ボタンは出ない（`frontend/src/pages/roles/RolesPage.tsx:391`）。
- 読み込みが終わるまでは 3 つとも押せない（`canTogglePerms = canEditPerms && permsReady`、`frontend/src/pages/roles/RolesPage.tsx:169`）。

## 3. 書き換え方（試験の意味は変えない）

- 行の名前は文字を直書きしない。`rowMenuLabelKey` を `frontend/src/constants/menuPermissions.ts` から import し、各試験の翻訳関数（`tr` または同じファイルにあるもの）で引く。名前が取れなければ止まって報告する。

（１）PurchaseAdminEditorButtonMigration の試験
- 行の切替を `findByRole('radiogroup', { name: <行の名前> })` で取る。その中の radio を `within(...)` で名前から取る。
- 初め: 「表示のみ」が `aria-checked="true"`。取消ボタンは押せない。
- 「非表示」を押す: 「非表示」が `aria-checked="true"`、「表示のみ」が false。取消ボタンが押せる。
- 取消を押す: 「表示のみ」が true に戻る。取消ボタンは押せない。`mock.put` は呼ばれない。

（２）batch3ePages の試験
- `permissionBox` を、行の切替の中の「非表示」の radio を返す形にする。
- 待つ目印は `findByRole('radiogroup', { name: <行の名前> })`。
- 読み込み前: 「非表示」の radio が `disabled`。
- `release([permission])` のあと: 「非表示」が押せる。「表示のみ」が `aria-checked="true"`。
- 試験の名前（it の文）は変えない。

## 4. 確かめ（全部の生出力をファイルに残し、終了コードを報告する）

- 直した 2 ファイルを `npx vitest run <2つのパス>` で流し、全部通る。
- `npx vitest run src/pages/roles src/constants src/components/SegmentedToggle.test.tsx src/components/DesktopShell.test.tsx src/components/MobileShell.test.tsx` も通る。
- frontend の全部の単体試験（`npm run test` で CI と同じもの）を 1 回流し、失敗が 0 件。失敗が残ったら、その試験名と最初のエラー行を報告して止まる（直さない）。
- `npx tsc --noEmit` exit 0。変えたファイルに `eslint --max-warnings=0` exit 0。

## 5. 止まる条件

- 2 章の事実と実物が違う（名前が取れない・radio が無い）。
- 製品コードを変えないと通らない。
- 2 本以外の試験が落ちる。

## 6. 記録

- commit は 1 つ。題「test(roles): update two legacy RolesPage tests to the 3-way toggle」。最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/role-menu-permissions`（force は使わない）。
- 最後に DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容> のどれか 1 行。
