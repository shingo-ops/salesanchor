# 独立審査（Opus）: 便12b 打つと出る候補

> この文書は何か（1行）: 便12b の設計と実装を、**現物のソースと実機の実測、自分で動かした検査だけ**を
> 根拠に突き合わせた記録。実装担当の報告は根拠にしない（数値は自分で測り直した）。

**審査日**: 2026-10-28
**対象**: docs/handoff/viewer-search-suggestions/{recon,design}.md ＋ 未コミットの実装一式
**土台**: `release/viewer-search-suggestions`（`origin/main` = ff6787294。審査時点で main は1件も進んでいない＝差0）

## 判定

**APPROVE**。審査の途中で**1点を見つけて直させた**（下記4＝既存検査 B8 の前提崩れ）。
その判断のために**お手本を実機で追加測定**し（recon §1 F8）、設計の「draft が非空なら候補」という
単純な規則がお手本と一致することを一次情報で確かめた。

## 1. 実装が設計どおりか（自分で差分を読んだ）

| design の指示 | 実装 | 判定 |
|---|---|---|
| 候補は純関数（4-1） | `frontend/src/pages/viewer/searchSuggestions.ts:24-49`。React に依存しない・副作用なし | 一致 |
| 判定は既存 `matchesQuery` をそのまま使う（4-1 の2） | 同 `:34`。独自の照合を書いていない＝**押して0件になる候補は作れない** | 一致 |
| 表示名は japanese → english → mark（4-1 の3） | 同 `:12-14`（`||` の順。空文字は空として落ちる） | 一致 |
| 同名はまとめ、件数は数えるが画面に出さない（4-1 の4） | 同 `:32-38` の `Map<string, number>`。返り値は `string[]`＝**件数は型として出られない** | 一致 |
| 並べ替えは先頭一致→件数降順→名前昇順で決定論的（4-1 の5） | 同 `:41-47`。最後が `localeCompare` なので**同値で順が揺れない** | 一致 |
| 最大10件（4-1 の6） | 同 `:48` の `slice(0, limit)`・既定 `limit = 10` | 一致 |
| 空なら履歴・1文字以上なら候補・当たらなければ何も出さない（4-2） | `InventoryView.tsx:884-939` の `draft === "" ? （履歴） : （候補 && 1件以上）` | 一致 |
| 候補を押したら確定と同じ道（4-2） | 同 `:930` が `confirmSearch(term)`＝札・履歴積み・ページ1戻しが**便12a と同じ経路** | 一致 |
| 候補は `useMemo`（4-2） | 同 `:104`。依存は `[allRows, draft]` のみ | 一致 |
| 印は虫眼鏡・履歴は時計で描き分け（4-2） | 同 `:932`（`MagnifyingGlass`）／`:912`（`Clock`）。import は既存の `icons-base`（`:15`）で**追加なし** | 一致 |
| 行の形は履歴と同じ・新しい値を作らない（4-2・⑨） | `viewer.css:207・220-221・237-238・243-244` は既存の `.viewer-recent-*` 規則に**セレクタを並記しただけ**。新トークン0件・直値0件 | 一致 |
| 辞書を増やさない（⑥） | `locales/viewer/{ja,en}.json` は**差分0**（git diff に出ない） | 一致 |
| PC は1px も動かさない（①） | PC の分岐（`:400-411` の `searchField`・`:661` の `isMobile ?`）に差分なし。候補は検索画面（`isMobile` の中）だけ | 一致 |

**金型（`components/`）に触っていない**ことも確認した（`git diff --numstat` に `frontend/src/components/` が1件も出ない）。
ADR-144 の観点では「閲覧ページの中だけで作る」を守っている。

## 2. 既存の検査への波及（自分で grep して全件読んだ）

検索画面に依存するファイルは**6つだけ**（`grep -rln "viewer-recent\|viewer-search-open\|viewer-search-input\|recentSearches" frontend/src frontend/tests-e2e`）。
うち検査は2本（`viewer-search-mercari.spec.ts`・新規 `viewer-search-suggestions.spec.ts`）と単体1本（`recentSearches.test.ts`）。

| 既存の検査 | 何を前提にしているか | 本便の影響 |
|---|---|---|
| mercari B6・B7（`:143-182`） | **札の✕**で開き直した画面に最近使った語 | **緑のまま**（`clearSearchTerm()` は `setDraft("")`） |
| mercari B8（`:183-210`） | **確定後に `viewer-search-open` で開き直す**と最近使った語 | **赤になる**（下記4）→ ✕ の道に替えた |
| mercari「すべて消す」（`:209-227`） | ✕ で開き直して `viewer-recent-clear` | **緑のまま** |
| mercari B9（PC） | PC は検索画面が開かない | **緑のまま**（PC の分岐に差分なし） |
| `recentSearches.test.ts` | 履歴の読み書き | **無影響**（触っていない） |
| `drawer-inert-closed.spec.ts` | 閉じたパネルの枚数（便12a で2→3に直した） | **無影響**（本便は Drawer を1枚も増やしていない） |

## 3. 空振りでないか（自分で壊して確かめた）

単体は**実際に実装を3通り壊して赤を確認**し、復元後に全緑に戻ること（md5 一致）まで見た。

| 壊し方 | 結果 |
|---|---|
| 先頭一致の優先（`:44`）を外す | **U2 が赤**（1 failed / 6 passed） |
| `matchesQuery` の判定（`:34`）を外して全行を候補にする | **U5 が赤**（1 failed / 6 passed） |
| 10件の上限（`:48`）を外す | **U3 が赤**（1 failed / 6 passed） |
| 復元 | **7 passed** |

- 閲覧ページの単体全体: **Test Files 10 passed / Tests 140 passed**（便12a の 9/133 に対し +1 ファイル +7 件）。
- 画面検査は **B1・B2・B3・B5・B6 が直す前は赤**（候補そのものが存在しなかった／B6 は履歴が出ていた）。
  B4（寸法）だけは「候補が出る」ことに依存するので B1 と同じ test にまとめてある。
- **この端末では Playwright のブラウザが動かない**（`Executable doesn't exist at .../chromium_headless_shell`）。
  画面検査の合否は CI が唯一の一次情報。本数は `--list` で実測した（下記5）。

## 4. 審査で見つけて直させた1点（既存検査 B8 の前提崩れ）

**症状**: 便12b を入れると、既存 mercari B8 が赤になる。
**理由**: `openSearchScreen()` は `setDraft(appliedQuery)`（`InventoryView.tsx:161-165`）なので、
**語を確定したあとに検索欄から開き直すと draft が非空＝候補が出て、最近使った語は出ない**。
B8 はその道順で「最近使った語の行の寸法」を測っていた。

**どちらが正しいかを推測で決めず、お手本を実機で測った**（recon §1 F8・`uiautomator dump` と `dumpsys input_method`）:

- 語を確定した結果画面で検索バーを押す → **入力欄に語が残ったまま候補（`search_hint_item`）が10件**。
  **「検索履歴」の見出し（`section_title`）は出ない**。行は 206px＝68.7dp・文字は左から 192px＝64dp。
- 測定には**履歴にすでにある語（ポケモン）の行を押した**ので、PO の端末の履歴は**1件も増えていない**
  （測定前後の dump が一致）。

**結論**: うちの「draft が非空なら候補」はお手本と一致している＝**実装は正しく、検査の前提が古い**。
よって B8 の道順を**札の✕**（`clearSearchTerm()`＝`setDraft("")`）に替えさせ、**測る値（69px・64px・印1つ）は変えていない**。
あわせて、この挙動を固定する **B6 を新 spec に1本追加**させた（お手本と一致していることの歯止め）。

## 5. 数（自分で測った一次情報）

- `buildSuggestions`（698行・500回の平均・この端末の jsdom）: **当たる語 3.2ms/回・当たらない語 1.3ms/回**。
  design ⑩ の見込み（1ms 前後）より3倍遅いが、1打鍵3ms なので **debounce は入れない**判断を維持（design ⑩ に実測を記載）。
- 画面検査の本数（`npx playwright test --list`）: 新 spec **30 tests**（5本×2幅×3 project）／
  mercari **57 tests**（変更なし）。**3 project に増えるのは社内の既定**（`visual-language/` を3つの project が全部拾う）。
- 型検査（`npx tsc --noEmit -p frontend/tsconfig.json`）: **終了0・出力なし**。
- `npm run check:all`: **終了0**（lint は `✖ 59 problems (0 errors, 59 warnings)`＝便12a と同数で、
  **本便で触った3ファイルだけに `--max-warnings=0` で lint をかけると終了0**＝新規の警告は0件）。
- 閲覧ページ JS（`npx vite build --manifest` ＋ `node scripts/check-viewer-bundle.js`・**同じ作業場所で2回測った差**）:
  本便を外した状態 **265.6KB** → 本便あり **266.4KB**＝**+0.8KB**（上限300KB。`viewer-*.js` が 48.1→48.9KB）。
  外した状態の測り方は「tracked 2ファイルを `git checkout --` で戻し、新規 `searchSuggestions.ts` を一時退避」。
  **戻したあと3ファイルの md5 が退避前と一致**することを確認済み。

## 6. 残した差・申し送り

- **候補が0件のときの見た目**はお手本が未確認なので「何も出さない」にした（文言を作らない）。recon §1 の未確認2件は据え置き。
- **候補は商品名に寄せる**ので、型番や検索ワードだけで当たった行も商品名で並ぶ（design ⑩）。
- **画面検査の持ち時間10分**（余裕45秒）は本便でさらに +30 回ぶん重くなる。別便 H3 の優先度を上げる。
