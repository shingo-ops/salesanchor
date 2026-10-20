# コード審査: 在庫表のタブを表にくっつける（PR #4578）

- 審査対象: HEAD f8103242b43c3892feb8593a3eb3372977b77de6（`git diff origin/main...HEAD`、origin/main 38613d7d7）
- 設計: docs/handoff/inventory-tabs-attach-table/design.md（review-design.md 2回目 APPROVE）
- 審査者: Reviewer（Opus）。コードは直していない
- 生出力: /tmp/CC報告ファイル/tabs-attach-review/（審査者の実行分）、/tmp/CC報告ファイル/tabs-attach-impl/（実装担当の実行分）

## 判定: APPROVE

## 1. 設計 §3 との一致
| 節 | 結果 | 根拠 |
|---|---|---|
| 3-1 Tabs extra/end | 一致 | `frontend/src/components/Tabs.tsx` extra/end 追加。両方無いときは従来の role=tablist の div を返す（className もそこ）。あるときだけ外側 `comp-tabs-bar comp-tabs-bar--{variant}` に className を移し、tablist の中はタブボタンだけ。`frontend/src/components/Tabs.css` の bar 規則は `margin-bottom:-1px`（:86-89）より後、hover 規則より前。値はトークンのみ |
| 3-2 DataTable attachedTop | 一致 | `frontend/src/components/DataTable.tsx:221` `attachedTop && !cardMode` で wrapperCls にだけ付与。CSS は border-top/上角丸を 0 |
| 3-3 Select variant="tab" | 一致 | SelectVariant に "tab"。FormField.css の既存 variant 規則の後に 1〜5 の順で追加。`background` 一括指定なし、border-bottom は focus で触らない。active は value が空でないときだけ |
| 3-4 Storybook | 一致 | Tabs.stories `AttachedToTable`、Select.stories `TabVariant` |
| 3-5 アプリ在庫表 | 一致 | MAIN_TCG_CODES（readonly string[]、as const なし）で直書き4か所を置換。Tabs underline/md、その他選択時は activeKey ""、extra は variant="tab"・size 削除・0件なら出さない、end は注記（testid 同じ、margin-left 削除）。ui-allow コメント削除。DataTable `attachedTop={!isMobile}`。rowdrawer テストは dialog 内だけを見る形に |
| 3-6 閲覧ページ | 一致 | MAIN_SERIES（eslint-disable/enable 付き）・otherSeries（distinctValues=compareText 順）。Tabs を DataTable 直前へ移動、件数なし、その他 select に aria-label/testid、value 空なら何もしない。スマホのセレクト（件数つき）は不変。ja tabAll「すべて」、tabOther ja/en 追加 |
| 3-7 GAS | 本 PR の範囲外 | 別リポジトリ。K7 は反映後に別途確認 |

## 2. 範囲外の変更・影響
- 差分は frontend 17 ファイル＋docs 3 件のみ。migrations / deploy.yml / scripts/ なし。
- Tabs の extra/end を渡すのは InventoryPage と InventoryView のみ（grep）。他の Tabs 利用は何も渡さないので描画は従来どおり。
- `variant="tab"` の既存利用（ReviewSection.tsx:252、InventorySearchBar.tsx:308,318、CompanyDetailPage.tsx）はすべて Button の variant で、Select の新 variant とは別物。tabbar ほか Select の他 variant の規則は未変更。
- attachedTop を渡すのは 2 画面だけで、既定 false。

## 3. ガバナンス
- ADR-067: 追加 CSS に色の直書きなし（diff の grep で #hex/rgb なし）。check:css-colors・stylelint・dark-parity すべて exit 0（tabs-attach-impl/check-all.txt）。
- ADR-027: 新文言は viewer.tabOther（ja/en 同キー）。check:i18n-missing-keys PASSED。シリーズ名の日本語は DB 照合値として eslint-disable 理由つき。
- ADR-144: 追加行に生 `<button>`/`<select>` なし。アプリの自作タブを金型に置換し ui-allow を削除。
- アクセシビリティ: role=tablist はタブボタンだけを包む。その他 select は両画面とも aria-label あり。focus-visible の outline あり。

## 4. テストが K1〜K6 を確かめているか
| 基準 | 確認 |
|---|---|
| K1 | InventoryPage.tabs.test K1（bar の次の兄弟が attached の表、注記が bar 内、tab 4つ）。Storybook 実測 measure-out.txt: タブ行下端と表上端の差 0、選択中タブ下端と内側下端の差 0、その他下端と選択中タブ下端の差 0 |
| K2 | measure-out.txt: 背景 rgba(0,0,0,0)、上左右の枠 透明、背景画像（▽）あり、選択中の文字色 rgb(30,58,138)=accent #1e3a8a。vitest でも tab / tab-active クラス |
| K3 | InventoryView.test K3（タブ名、件数バッジなし、その他 option 名前順、bar の次が DataTable、attachedTop=true） |
| K4 | InventoryView.test K4 ＋ viewerFilter.test otherSeries |
| K5 | InventoryView.test K5（件数つきセレクト、tablist なし、attachedTop=false） |
| K5b | InventoryPage.tabs.test K5b（スマホで tablist あり、attached クラスなし） |
| K6 | タブ切替・その他で work_code が従来どおり（tabs.test K2/K6・K6）。build・lint（0 errors）・check:all・build-storybook 合格。PR CI「Frontend unit tests（内部）」「Frontend lint & custom checks」pass（pr-checks.txt） |

## 5. vitest 全体の失敗が無関係という主張
- 実装担当の全体実行は 33 ファイル失敗（タイムアウト・findBy 1000ms 切れが中心、多くは今回触っていない部品）。
- 審査者の再現:
  - PR 版 rowdrawer 単体: 5/5 合格（vitest-pr-rowdrawer.txt）。
  - origin/main 版で同じ在庫系 4 ファイルを直列実行 3 回: 1 回目・2 回目合格、3 回目 noechopatch 2 件失敗（vitest-main-4files-r2.txt）。PR 版でも settings 1 件失敗（vitest-pr-4files.txt）。失敗はいずれも `findByTestId('inventory-row-r1')` の待ち切れ／5000ms 超えで、main でも出る。
  - 新規 InventoryPage.tabs.test 単体 3 回: 2 回合格、1 回失敗（同じ待ち切れ）。既存在庫テストと同じ書き方に由来する、Mac の負荷に依存する揺れ。
  - PR の CI では Frontend unit tests が pass。
- 結論: 失敗は main でも同じ形で出る負荷依存の揺れで、今回の変更による回帰ではない、という主張は妥当。

## 6. 指摘（差し戻し不要・参考）
- N1: 新規 tabs.test も既存在庫テストと同じく `findByTestId` 既定 1000ms 待ちで、負荷時に揺れる（単体 1/3 失敗を観測）。CI は通っている。揺れ対策は在庫テスト全体の別課題。
- N2: K7（GAS）・K8（本番配信物）は本 PR の審査範囲外。反映後に設計どおり確認すること。
