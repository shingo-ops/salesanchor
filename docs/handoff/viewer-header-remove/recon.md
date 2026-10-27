# recon: 閲覧ページのヘッダーを丸ごと消す（便4）の現在地

> この文書は何か（1行）: スマホの上部からヘッダー（題・最終更新・言語）を無くし、上部をさらに1行ぶん短くする便の、着手前の一次情報。

**日付**: 2026-10-26
**親（あるべき姿）**: `docs/specs/design-system/visual-language/README.md`
**対象**: 閲覧ページ `frontend/src/pages/viewer/`（**アプリ本体の `frontend/src/pages/inventory/` とは別コード**。正本は ADR-1019）
**前便**: 便5 `docs/handoff/viewer-choice-sheet/design.md`（PR #4759）／便3 `docs/handoff/viewer-top-compact/design.md`（PR #4752・本番反映済み）
**worktree / commit**: `/root/worktrees/salesanchor/release-viewer-header-remove` / `90428a9b4`
**ADR 検索**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（タップ領域44px）／ADR-067（トークン参照のみ）／ADR-027（文言は t() 経由）／ADR-137（スマホ判定 `useIsMobile`）が該当。新規 ADR は不要。

## 1. PO 決定（2026-10-25・選択肢を提示して受領）

> **ヘッダーを丸ごと消す**（「最終更新」も「言語」も絞り込み画面の中へ送る）

提示した3案は「題だけ消す／**丸ごと消す**／残す」。**データの鮮度が一目で分からなくなる弊害は説明済み**で、その上での決定。
2026-10-26 に「1」＝本便を次にやる、との指示を受領。

## 2. ヘッダーの現物（**スマホ・PC で分岐していない**）

`frontend/src/pages/viewer/InventoryView.tsx:408-424`:

| 中身 | 行 | 部品 | 目印 | 文言キー |
|---|---|---|---|---|
| 題「在庫一覧」 | `:409` | 生の `h1`（`viewer-header__title`） | なし | `viewer.title` |
| 最終更新 | `:410-412` | `span`（`viewer-header__updated`） | `viewer-updated` | `viewer.lastUpdated`（値は `formatUpdatedAt(data.updated_at)`・同 `:44-53`） |
| 言語 | `:413-423` | `SelectControl size="sm"` | `viewer-lang` | `viewer.language.label` / `.ja` / `.en`。切替は `changeLang`（同 `:400-403`）＝ cookie 保存＋`i18n.changeLanguage` |

**`isMobile` の分岐の中に入っていない**（`isMobile` が出るのは `:57`・`:427`・`:502`・`:553`・`:558`）。
＝**PC でも同じヘッダーが出る**ので、消すときは**スマホだけ**にする必要がある。

CSS は `frontend/src/pages/viewer/viewer.css:2-22`（`.viewer-header` / `__title` / `__updated`）。
**`frontend/src` と `frontend/tests-e2e` の中で、この3クラスを参照しているのは上記2ファイルだけ**（`grep -rn "viewer-header"`）。

## 3. **見出しを隠す仕組みは閲覧ページに届いていない**（最重要・報告との食い違い）

アプリ本体には `.sr-only`（読み上げだけに見せる）が**ある**（`frontend/src/pages-layout.css:227-238`。`frontend/src/pages/login/LoginPage.tsx:79` が `h1` で使用）。
しかし**閲覧ページのバンドルには入らない**:
- 入口は `frontend/src/pages/viewer/main.tsx:5-7` で `./i18n` → `../../index.css` → `./viewer.css` だけを読む
- `frontend/src/index.css:1-2` が読むのは `./tokens.css` と `./components/field-size.css` のみ＝**`pages-layout.css` は読まれない**

→ ヘッダーを消すと**ページから `h1` が消える**（`h1` はこの1か所だけ）。
**同じ見た目のまま見出しを残すには、閲覧ページ側に隠し用のクラスを1つ置く必要がある**（§設計で扱う）。

## 4. 絞り込みドロワー（移動先）の現物

- ドロワー本体は `frontend/src/pages/viewer/InventoryView.tsx:558` から（`isMobile &&` の中＝**スマホだけ**）
- 最初の画面（`filterView === "root"`）の中身は `.viewer-filter-body`（CSS は `frontend/src/pages/viewer/viewer.css:79-83`）で、
  並びは 24時間以内 → 提供者 → コンディション → 価格の範囲 → 数量の範囲
- **PC のヘッダーだけに `viewer-updated` / `viewer-lang` が残り、スマホはドロワーの中に出す**形にすれば、
  **同じ目印が同時に2つ存在することはない**（ヘッダーは PC だけ・ドロワーはスマホだけ）

## 5. 消すと赤になる既存の検査

| ファイル:行 | 何を見ているか | 影響 |
|---|---|---|
| `frontend/src/pages/viewer/ViewerApp.test.tsx:43`・`:74` | 自動取り直しの前後で `viewer-updated` の時刻が変わる | **jsdom は `window.matchMedia` が無い＝`useIsMobile()` は false**（`frontend/src/hooks/useIsMobile.ts:16-21`）→ PC 経路でヘッダーが出るので**そのまま通る** |
| `frontend/src/pages/viewer/InventoryView.test.tsx:53` | PC で「最終更新」の文字 | 同上（PC 経路）→ そのまま通る |
| `frontend/tests-e2e/visual-language/viewer-*.spec.ts`（3本） | ヘッダー・題・最終更新・言語は**参照していない** | 影響なし（ただし上部の高さ基準 192px は**便4 で更新が必要**） |

**スマホ経路のテスト**（`mobileMatchMedia` を入れる回）で `viewer-updated` を見ているものは**無い**（`grep -n "viewer-updated" frontend/src/pages/viewer/InventoryView.test.tsx` は `:53` のみ）。

## 6. 上部の高さ（便3 以降の実測と計算）

便3 の CI 実測で、スマホの先頭カードの y は **192px 以内**（`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` A1 が毎 PR 固定）。
内訳は ヘッダー68 ＋ 余白12 ＋ 検索欄44 ＋ gap12 ＋ 操作3つ44 ＋ 余白12 ＝ 192。
→ **ヘッダー68 を消すと 124**（＝お手本メルカリの 146 より小さい）。

## 7. PWA の題との二重

`frontend/viewer/index.html:8` の `<title>` は `Sales Anchor Viewer`。
題「在庫一覧」（`viewer.title`）と二重になるため、画面から消しても情報は失われない。
**manifest ファイルは見つからない**（`frontend/viewer/manifest*.json`・`frontend/public/manifest.json` いずれも無し）。

## 8. この端末の制約

実機の ADB は未接続・この端末では Playwright のブラウザが動かない。**寸法の一次情報は CI の Playwright ログだけ**。
本番反映後は、配布 JS の SHA256 を手元ビルドと突き合わせて確認できる（便3・便5 で実施）。
