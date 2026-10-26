# recon: 閉じているパネルの中身が Tab で辿れ、読み上げにも乗る（宿題 D5）

> この文書は何か（1行）: 宿題 D5（閉じた `Drawer`／`Sheet` の中身がキーボードの Tab の通り道に残り、
> 画面読み上げにも乗ってしまう）の現物調査。**すべて 2026-10-27 時点の現物を開いて確認した事実**。

**日付**: 2026-10-27 ／ **土台**: `release/drawer-inert-when-closed`（`origin/main` = `fbc8e3086`）
**起票の原文**: `docs/handoff/viewer-choice-sheet/design.md:219`（便5 の ⑫ D5）

## 1. 閉じている状態に効いているのは「横へずらす」だけ

`frontend/src/components/Drawer.css:38-44`:

```css
  /* スライドインアニメーション（user-drawer パターン踏襲） */
  transform: translateX(100%);
  transition: transform var(--transition-slow);
}

.comp-drawer-panel--open {
  transform: translateX(0);
}
```

- **`visibility` / `display` / `inert` / `pointer-events` はどこにも無い**（同ファイル全体を確認）。
- `transition` が効いているのは **`transform` だけ**。`--transition-slow` は
  `frontend/src/tokens.css:148` = `280ms cubic-bezier(0.4, 0, 0.2, 1)`。
- 画面の外へずらしただけなので、**中身は「存在するまま」**＝Tab の順番に残り、読み上げの対象にもなる。
- `frontend/src/components/Drawer.tsx:118` のコメントに「DOM は常にマウント、CSS クラスでアニメーション」と明記されている（独立審査で行番号を訂正）
  （意図した作りで、事故ではない）。

## 2. 背景（オーバーレイ）は閉じているとき DOM に無い

`frontend/src/components/Drawer.tsx:110-116` の `{open && <div className="comp-drawer-overlay" …>}`
＝開いているときだけ描く。**問題はパネル本体だけ**。

## 3. `Sheet` は同じ作り・`Modal` は無関係

| 金型 | 閉じているときの DOM | 閉じている状態の指定 | 使用ファイル数（src/**/*.tsx・test/stories 除く） |
|---|---|---|---|
| `Drawer` | **残る**（`frontend/src/components/Drawer.tsx:105`＝本便の実装後は `:107` は `portalTarget` が無いときだけ null） | `transform: translateX(100%)` のみ（`frontend/src/components/Drawer.css:39`） | **35** |
| `Sheet` | **残る**（`frontend/src/components/Sheet.tsx:86`＝実装後は `:88` も同じ） | `transform: translateY(100%)` のみ（`frontend/src/components/Sheet.css:45`） | **2** |
| `Modal` | **消える**（`frontend/src/components/Modal.tsx:86` `if (!open) return null;`） | — | 43 |

→ **直す対象は `Drawer` と `Sheet` の2つ。`Modal` は何もしなくてよい**。

> **数の訂正**: 下請け調査は `Drawer` を「45ファイル」と報告したが、**実測は35**
> （`grep -rl "<Drawer" --include=*.tsx src/` から test/stories を除いた数。便7 の調査と独立審査も35）。
> この便の設計では**35**を使う。

## 4. 閲覧ページでは「閉じたパネル2枚」が同時に居る

`frontend/src/pages/viewer/InventoryView.tsx:669`（絞り込み）と `:753`（シリーズ／並び替えの選択）が
どちらも `{isMobile && (<Drawer …>)}`。**スマホ幅で画面を開いた直後は両方とも閉じている**。

2枚目の中身は `:758` の `choicePanel === "sort" ? sortChoiceRows : seriesChoiceRows` で、
`choicePanel` が `"none"`（＝閉じている）のときは**シリーズの一覧が描かれている**。
シリーズの行数は `frontend/src/pages/viewer/viewerFilter.ts:213` の `seriesTabs()`（在庫にあるシリーズの種類数）＋「すべて」の1行。
**便5 時点の本番実測は43件**（`docs/handoff/viewer-choice-sheet/design.md` ⑩）。
1行ごとにネイティブのラジオ（`RadioControl`）が1つ＝**フォーカスできる要素が約44個、閉じたまま Tab の通り道に入る**。

1枚目（絞り込み）も閉じたまま中身を描くので、提供者・コンディション・数量・24時間以内などの部品が同様に残る。

## 5. この不具合を測っている自動検査は 0 件

- `frontend/src/hooks/useFocusTrap.test.tsx` の C6 は「**開いていないときは Tab の購読をしない**」を見ているだけで、
  「閉じたパネルの中身が Tab で辿れないこと」は見ていない。
- `frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts`（便7）は**開いているとき**の出口封じだけ。
- `frontend/src/components/Drawer.test.tsx` にフォーカス関連のテストは無い（便7 recon §5 で確認済み）。
- `Modal`・`Sheet` には単体テストのファイル自体が無い（同）。

## 6. 直し方の材料（事実のみ）

- **`inert`（＝その枝をまるごと無効にする印）は DOM の性質として型定義にある**:
  TypeScript 同梱の DOM 型定義（lib.dom.d.ts の 13730 行目） に `inert: boolean`。
  → `ref` 経由で `el.inert = true` と書けば**型の細工は不要**。
  一方 **JSX の属性としては実験的扱い**（React の実験的型定義（@types/react の experimental.d.ts の 130 行目） にのみ存在）なので、
  `<div inert>` と直接書く形は採らない。React は `frontend/package.json:84` で `^18.3.1`。
  下請け調査は「React 18 では使えない」と報告したが、**正確には「JSX 属性としては使えない／DOM の性質としては使える」**。
- `inert` は**リポジトリ内で未使用**（先例なし）。
- `aria-hidden='true'` の中を**フォーカス可能要素から除く**処理は既にある
  （`frontend/src/hooks/useFocusTrap.ts:24`）。ただし閉じたパネル本体に `aria-hidden` は付いていないので効かない。
- **`visibility: hidden` を素で足すと閉じるアニメーションが途中で消える**:
  `transition` は `transform` だけに掛かっており、`visibility` は即座に切り替わる（§1）。
  遅らせるには `visibility 0s linear <280ms>` のような指定が別途必要で、
  **280ms 単体のトークンは存在しない**（`frontend/src/tokens.css:134-148` に `--duration-base: 200ms` などはあるが 280ms は複合値 `--transition-slow` のみ）。

## 7. 作法

- ADR-144 §1「`pages/` 配下の UI は原則 `components/` の共通金型を使う」。本件は金型の内部だけを直す。
- ADR-067: 色・寸法はトークン参照のみ。**新しいトークンを足すなら理由を design に書く**。
- 便7（PR #4800）で `frontend/src/hooks/useFocusTrap.ts` を新設済み＝**かぶせて出すパネル共通のキーボード処理の置き場がすでにある**。

関連: [[salesanchor-viewer-mobile]] / `docs/handoff/viewer-focus-trap/design.md`（便7） / ADR-144
