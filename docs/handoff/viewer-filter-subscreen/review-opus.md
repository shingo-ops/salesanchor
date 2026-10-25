# review-opus: 閲覧ページの絞り込み副画面（便2）の独立審査

> この文書は何か（1行）: 設計を別の Opus に「反証を探す立場」で審査させた結果と、指摘への対応の記録。

**日付**: 2026-10-25
**審査の指示**: 承認ありきにしない／`file:line` を全数で抜き取り検証／`Drawer` と `MultiSelect` の呼び出し元を全数 grep／CI 設定を一次ファイルで読む／推測で書かない
**初回の結論**: **CHANGES-REQUESTED**（引用の誤り5件＋設計の穴9件＋検査の抜け多数）
**改訂後の状態**: 全14項目に対応済み。**審査を書いた時点では区分 A の KGI の PO 承認が未取得**だったが、
**2026-10-25 に PO から「承認」を受領**（§4・design.md ①）。

## 1. 審査が崩せなかった主張（そのまま維持）

| 主張 | 審査の検証 |
|---|---|
| `Drawer` に `onBack` を足しても既存は1pxも変わらない | ヘッダ CSS（`frontend/src/components/Drawer.css:56-64`・`:66-73`）に `nth-child` 等「題がひとつ」前提の指定は**0件**。フォーカストラップ（`frontend/src/components/Drawer.tsx:64-70`）も `aria-labelledby`（`:134`・`:139`）も条件付き描画なら不変。**反証不可** |
| `MultiSelect` の既定 `"popover"` は不動 | 呼び出し元**全8箇所**を列挙。`layout` を渡す本番は `frontend/src/pages/viewer/InventoryView.tsx:145`・`:159` の2件のみ。**反証不可** |
| `ListRow` は使えない／`Sheet` は PO が不採用 | `frontend/src/components/ListRow.tsx:1-12`・`frontend/src/components/Sheet.css:35` で確認 |

## 2. 指摘と対応（全14項目）

| # | 指摘 | 深刻度 | 対応 |
|---|---|---|---|
| 1 | **`ICON.back` / `ICON.arrowRight` / `ICON.chevronDown` は実在しない。`ICON` はアイコンの「大きさ」の定数** | 引用誤り | 自分でも確認（`frontend/src/constants/iconSizes.ts:5`）。recon §4 を全面差し替え。実在名は `NAV_ICONS`（`frontend/src/constants/icons.tsx:209`）・`DashboardIcons`（`:234`）・`SCHEDULE_SETTINGS_ICONS`（`:358`） |
| 2 | **閲覧ページの JS 300KB 上限を見落としている。アイコンは `frontend/src/constants/icons-base.tsx` に足すべき** | 重大 | 自分でも確認（`frontend/scripts/check-viewer-bundle.js:21` の `LIMIT_KB = 300`／`frontend/src/constants/icons-base.tsx:2-3`「定義はここだけ」／`frontend/src/components/Drawer.tsx:19` が `icons-base` から読む）。design §4-3 を新設し、**A22** と ⑪ の関所に `frontend/scripts/check-viewer-bundle.js` を追加 |
| 3 | 「22 ページ」は古い（`frontend/src/components/Sheet.tsx:5` の転記）。**実測 35 ファイル** | 中 | 自分でも `grep -rl` で 35 を確認。design §4-1 を修正し、出典が古い値である旨も明記 |
| 4 | `frontend/src/components/Drawer.tsx:138-166` → **`:138-164`** | 引用誤り | 修正 |
| 5 | recon のアイコン追加手順の出典が `frontend/AGENTS.md:64`（lucide-react と書かれている）で実態と不一致 | 軽 | 出典を `frontend/src/constants/icons-base.tsx:8`・`:27` に付け替え、手順書が実態と合っていない事実も記録 |
| 6 | **検索で `options` を絞ると、選択済みの名前が生の値に化ける**（`frontend/src/components/MultiSelect.tsx:81` の `?? v`） | 高 | `allOptions`（名前を引く全件）を足し、**名前の解決は常に全件から**。**A9** を新設 |
| 7 | `noOptions` を**どの部品が描くか**が決まっていない（`frontend/src/components/MultiSelect.tsx:101` は空の div を描くだけ） | 中〜高 | `emptyLabel` を金型に足す。**A10** を新設 |
| 8 | **フォーカスが `<body>` に落ち、Tab がダイアログ外へ逃げる**（`open` が変わらないので `frontend/src/components/Drawer.tsx:64-70` が再実行されない） | 高 | §4-4 にフォーカスの移し先を明記。**A13・A14** を新設 |
| 9 | 副画面で Esc がドロワーごと閉じる（`frontend/src/components/Drawer.tsx:73-83` は `onClose` 固定） | 中 | `onClose` 側で「`root` 以外なら戻る」に分岐（金型は変えない）。**A12** を新設 |
| 10 | 検索欄の一時状態の寿命が片方しか決まっていない | 中 | 全経路で空に戻すと明記。**A17** を新設 |
| 11 | 「決定する」が実質「戻る」で読み上げと食い違う | 中 | **PO に2択で確認し「決定する」を選択（2026-10-25）**。⑩ に記録 |
| 12 | testId が popover 版と inline 版で共有されている（strict mode violation の既往あり） | 中 | §4-4b で3層に分離 |
| 13 | 閉じるアニメーション中に `root` へ戻すとちらつく（`frontend/src/components/Drawer.tsx:129-131`） | 低 | 閉じ終わってから戻すと明記 |
| 14 | **A6・A9 が常に真。A1・A4 は `scrollIntoView` 流用で常に真になる** | 重大 | A6 に**上限**を追加、A15（旧A9）は「A5 と対で意味を持つ」と明記、測り方の共通の決まり（スクロールせずに測る）を ⑤ の冒頭に追加 |

あわせて、⑥ の触るファイルに `frontend/src/pages/viewer/viewer.css`・`frontend/src/constants/icons-base.tsx`・
Storybook 2本を追加し、**便1 の spec（旧 A4〜A13）と本便の AC の対応表**を §5-1 に載せた。

## 3. 審査が確認した「問題なし」

- `frontend/scripts/check-page-size.js:19` の上限800行に対し `frontend/src/pages/viewer/InventoryView.tsx` は 436 行で余裕。
- `frontend/scripts/check-icon-sync.js` は大きさの一致だけを見るため、**アイコン追加で `frontend/src/constants/iconSizes.ts` の再生成は不要**。
- 提案した4つの文言キーは既存と衝突しない。
- `npm run check:all` に型検査が無いという前便の学びが A23/A24 に正しく反映されている。

## 4. 判定

上記1〜14の対応をもって**設計としては APPROVE 相当**とする。
ただし本記録は設計者（Opus）が自分の設計への指摘に対応したもので、**対応後の再審査は受けていない**。

**区分 A の必須ゲート（審査時は未充足・その後充足）**: `docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:62`（A 区分は PO が判断する）と
`docs/STANDARD-WORKFLOW.md:23`・`:79`（KGI は PO 承認が必須ゲート）により、**② の KGI の PO 承認を得るまで実装に着手しない**と決めた。
形の承認（2026-10-25「右から入れ替わる」）と文言の決定（同「決定する」）は受領済みで、**KGI も同日 PO から「承認」を受領**したため、
このゲートは充足した上で実装に着手している（`docs/handoff/viewer-filter-subscreen/design.md` ① に原文を記録）。
