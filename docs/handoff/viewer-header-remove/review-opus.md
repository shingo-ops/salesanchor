# Opus 審査: 閲覧ページのヘッダーを丸ごと消す（便4）

> この文書は何か（1行）: 実装したものが設計どおりか・検査が空振りしないかを、設計担当（Opus）が現物の行番号で確かめ、見つけた点を直した記録。

**日付**: 2026-10-26
**対象**: `release/viewer-header-remove`（base `5f8df4446`＝便5 マージ済みの main）
**設計**: `docs/handoff/viewer-header-remove/design.md`／**recon**: 同 `recon.md`
**判定**: **APPROVE（指摘3件を修正済み）**。手元で測れる検査はすべて緑。寸法・操作の C1〜C8 は CI の Playwright が唯一の一次情報。

## 1. 実装中に止まった質問への回答（私が関所スクリプトを直読みして確定）

実装側が「`check:nav-sync` が赤になる。設計に無いファイルを触ることになるので自分では決めない」と止めた。**正しい止め方**。
関所 `frontend/scripts/check-nav-title-sync.js` を読み、次の事実を確認した:

| 事実 | 根拠 |
|---|---|
| 規則は「`h1`/`h2` の題名は `t("nav.xxx")` か `usePageTitle()`」 | `frontend/scripts/check-nav-title-sync.js:44` |
| **閲覧ページの辞書に `nav` 名前空間が無い**＝規則を満たしようがない | `frontend/src/locales/viewer/ja.json`（トップレベルは `common`/`suppliers`/`viewer` のみ） |
| 既存の PC 側の帯が赤にならないのは**偶然**（除外語に `title` が含まれ、クラス名 `viewer-header__title` が一致するだけ） | 同 `:48` |
| 関所には**ディレクトリ単位の「ナビ外ページ」除外枠**が既にあり `register` 等が入っている | 同 `:35-39`・適用は `:57`（`EXCLUDE_DIRS.has(entry)`） |
| デザインシステムの正本も「ナビ枠外画面」と「視覚表示なしの読み上げ用 sr-only」を題名金型の対象外と明記 | `docs/specs/design-system/component-ssot/page-title/design.md:24` |

→ **`EXCLUDE_DIRS` に `viewer` を1行追加**した（ファイル名単位の `EXCLUDE_FILES` ではなく**ディレクトリ単位**＝同名ファイルの取り違えが起きない）。
**関所の方針を変えたのではなく、既にある区分に当てはめた**。実測: `node scripts/check-nav-title-sync.js` → PASSED。design ⑥・4-2b に記録済み。

## 2. 審査で見つけて直した点

| # | 指摘 | 直し方 |
|---|---|---|
| R1 | 便3・便5 の spec の**テスト名に古い「192px以内」が残っていた**（基準値は 128 に変えたのに名前だけ古い＝読む人を誤らせる） | 両方のテスト名を「上限以内（MAX_TOP_Y。便4で128へ更新）」に変更。`192` の記載は spec から0件になった |
| R2 | SSOT の守り手（`frontend/src/components/srOnlySsot.test.ts`）の判定が `.sr-only:focus` のような**擬似クラスの書き方を取りこぼす**＝二重定義を見逃す穴 | 判定を `[,{:]` に広げた（`.sr-only` の後ろが `:` でも定義として数える） |
| R3 | （1. の関所の件） | 上記のとおり確定・修正 |

## 3. 設計との突合（疑っていた点を現物で潰した）

| # | 疑い | 結果 |
|---|---|---|
| 1 | `.sr-only` の中身が変わっていないか | `frontend/src/components/sr-only.css` は**10行すべて元のまま**（`git diff` で元の `frontend/src/pages-layout.css` の削除分と一字一句一致）。元の場所には案内コメント1行だけが残る |
| 2 | 定義が1か所になったか | `srOnlySsot.test.ts` が `frontend/src` 配下の全 CSS を読み、定義ファイルが `components/sr-only.css` **ちょうど1つ**であることを固定（実測 pass） |
| 3 | 両方のバンドルに届くか | `frontend/src/index.css:3` に `@import`。アプリ本体の入口も `index.css` を読む（`frontend/src/main.tsx:4`）。閲覧ページも同じ（`frontend/src/pages/viewer/main.tsx:6`）。**閲覧ページ側は C6（h1 の見た目の幅 ≤1px）で効いていることを機械で確かめる** |
| 4 | 帯の中身を書き換えていないか | `{!isMobile && ( … )}` で囲んだだけ。中の3要素は差分0 |
| 5 | 同じ目印が二重にならないか | `viewer-updated`・`viewer-lang` は **PC の帯（`!isMobile`）とスマホのドロワー（`isMobile &&` の中）で排他**。同時に存在しない |
| 6 | 便2・便5 の仕組みを壊していないか | `drawerOpen`・`filterView`・`handleFilterEscape`・`choicePanel`・2つの `Drawer` は差分0 |
| 7 | 検査が空振りしないか | 開く前に `openPanel().count() === 0` を確認／`viewer-updated` は**開いているパネルの中**で測る（閉じていても DOM に居るため）／`scrollIntoView` 不使用／C5 は切替後に**実際に英語になる**ことで判定 |
| 8 | 新しいトークン・ハードコードが無いか | 追加 CSS は `.viewer-filter-meta` の1クラスで**すべて var() 参照**（枠線の 1px のみ・CSS 関所4本と stylelint が pass）。新トークンなし・新金型なし |

## 4. 手元で実際に走らせた検査（数字は実測）

| 検査 | 結果 |
|---|---|
| `npx tsc --noEmit` | 終了 0 |
| `npx vitest run`（`InventoryView.test.tsx`・`srOnlySsot.test.ts`・`ViewerApp.test.tsx`） | **3ファイル40件すべて pass** |
| `npm run check:all`（関所25本＋lint） | 終了 0（lint は 0 errors / 59 warnings＝すべて既存ファイル） |
| `node scripts/check-nav-title-sync.js` | PASSED（除外追加後） |
| `node scripts/check-dark-parity.js` | PASSED（130変数すべて対応） |
| `node scripts/check-css-class-naming.js` | PASSED |
| CSS 関所4本 ＋ `stylelint`（`viewer.css`・`sr-only.css`・`index.css`・`pages-layout.css`） | すべて終了 0 |
| `npx eslint --max-warnings=0`（変更3ファイル） | 終了 0（**警告0**） |
| `npx vite build --manifest` ＋ `node scripts/check-viewer-bundle.js` | **260.5 KB / 上限 300 KB** PASSED（便5 の260.0KB から **+0.5KB**） |
| `npx playwright test --list`（新 spec） | **13 件収集**（6種 × 2幅 ＋ PC 1件）→ CI の3 project で 39 件 |

## 5. 残っている穴（正直に書く）

| # | 穴 | 扱い |
|---|---|---|
| S1 | **寸法・操作（C1〜C8）を手元で測れていない**（この端末は Playwright のブラウザが入らない・実機の ADB 未接続） | **CI の `visual-language` が唯一の一次情報** |
| S2 | **`.sr-only` を使うアプリ本体の2か所（`frontend/src/pages/login/LoginPage.tsx:79`・`frontend/src/pages/inbox/InboxMessageThread.tsx:803`・`:850`）に自動検査が無い** | 定義の中身は一字一句同じで、両バンドルが `index.css` を読むことは確認済み。ただし**実物の確認手段が無い**ため、**PO の目視確認（ログイン画面・受信箱の送信ボタン）を依頼**（PO 了承済み・design ⑩） |
| S3 | 上部の高さは**計算で124px**。基準は 128（余裕4px） | 実測値は CI の C1 が返す。超えたら原因を特定して直す |
| S4 | 便4 で `h1` が**読み上げ専用**になるため、画面上に見える題は無くなる | PWA のタイトルバー「Sales Anchor Viewer」が担う（design ⑩） |

## 6. 判定

**APPROVE**。R1〜R3 を直した上で、設計の意図と実装は一致。手元で測れる関所はすべて緑。
残るのは CI の寸法・操作検査（S1）と PO の目視確認（S2・K1〜K5）で、どちらも赤なら revert 1回で戻せる（design ⑦）。
