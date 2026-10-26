# recon: かぶせて出すパネルの出口封じが、行が消えると効かなくなる（宿題 C8）

> この文書は何か（1行）: 宿題 C8（自動読み直しでフォーカス中の候補が消えるとフォーカスが `<body>` に落ち、
> `Drawer` の出口封じ（フォーカストラップ）を抜ける）の現物調査。**すべて 2026-10-26 時点の現物を開いて確認した事実**。

**日付**: 2026-10-26 ／ **土台**: `release/viewer-focus-trap`（`origin/main` = `840eea949`）
**起票の原文**: `docs/handoff/viewer-filter-subscreen/design.md:318`（便2 の2回目審査 N1・非ブロック）

## 1. 出口封じは「パネル内の先頭か末尾に居るときだけ」働く

`frontend/src/components/Drawer.tsx:101-129`:

- `document` の `keydown` を購読し、`e.key !== "Tab"` なら何もしない。
- `focusable = getFocusableElements(panel)` を取り、`first` / `last` を出す。
- **Shift+Tab**: `document.activeElement === first` のときだけ `preventDefault()` して `last.focus()`。
- **Tab**: `document.activeElement === last` のときだけ `preventDefault()` して `first.focus()`。
- **それ以外は何もしない**。つまり `document.activeElement` が**パネルの外**（`<body>` など）に在るとき、
  どちらの枝にも入らず**ブラウザ既定の Tab 移動がそのまま起きる**＝後ろの画面へ出て行く。

同ファイルのフォーカス関連:
- `:68-77` 開く直前の `document.activeElement` を覚え、閉じたら戻す。
- `:79-86` 開いたらパネル内の最初のフォーカス可能要素へ移す（`open` が変わったときだけ再実行）。
- `:88-99` Esc（`onEscape` があればそちら・無ければ `onClose`）。
- `:144` 付近のコメント「DOM は常にマウント、CSS クラスでアニメーション」＝**閉じていても中身は描かれている**。

## 2. 同じコードが Modal・Sheet にも複製されている（＝同じ穴が3か所）

| 金型 | 出口封じ | フォーカス可能要素の集め方 | 選択子の定義 | 使っている画面ファイル数（`src/**/*.tsx`・test/stories 除く） |
|---|---|---|---|---|
| `Drawer`（右から出るパネル） | `Drawer.tsx:101-129` | `Drawer.tsx:221-229` | `Drawer.tsx:212-219` | **35** |
| `Modal`（真ん中の確認窓） | `Modal.tsx:82-110` | `Modal.tsx:167-175` | `Modal.tsx:158-165` | **43** |
| `Sheet`（下から出るパネル） | `Sheet.tsx:82-110` | `Sheet.tsx:175-183` | `Sheet.tsx:166-173` | **2** |

> 「集め方」の行範囲は `getFocusableElements` と `getFirstFocusable` の**両方**を含む（独立審査で
> 末尾が1行足りない誤記を指摘され訂正。`Drawer` は 221-225 と 227-229）。

3つの `FOCUSABLE_SELECTOR` は**配列の中身も順序も完全に同一**（`a[href]` / `button:not([disabled])` /
`input:not([disabled])` / `select:not([disabled])` / `textarea:not([disabled])` / `[tabindex]:not([tabindex='-1'])`）。
`getFocusableElements` の本体も3つとも同一（`querySelectorAll` ＋ `!el.closest("[aria-hidden='true']")` で絞る）。
出口封じの本体も**変数名（`panel` / `dialog`）と空白以外は同一**。

→ **C8 の穴は `Drawer` だけの問題ではなく、`Modal`・`Sheet` にも同じ形で存在する**。

## 3. 「行が消える」経路（閲覧ページ）

- `frontend/src/pages/viewer/useViewerAutoRefresh.ts:8` `VIEWER_REFRESH_MS = 60_000`（60秒）。
  `:17-23` `setInterval` で `refresh()`。裏のタブでは保留し、表に戻ったとき1回だけ実行（`:24-31`）。
- `frontend/src/pages/viewer/ViewerApp.tsx:91-108` `refresh()` は `fetchInventory(token)` の結果で
  `setScreen((prev) => (prev.name === "inventory" ? { name: "inventory", data } : prev))`
  ＝**`data` を丸ごと差し替える**（`InventoryView` は残るので検索・タブ・ページは保たれる）。
- `frontend/src/pages/viewer/InventoryView.tsx:94-101` 候補一覧は **`data` から作る**:
  `providerOptions`（**94-97**）＝ `distinctValues(data.rows, (r) => r.provider).map(...)`／
  `conditionOptions`（**98-101**）も同様（独立審査で行範囲を訂正）。
- 候補1行は `frontend/src/components/MultiSelect.tsx:96-98` の `<label className="comp-multiselect__option ...">` で、
  中にチェック欄（`CheckboxControl`）がある。**フォーカスが当たるのは中のチェック欄**。
- → 60秒の読み直しで提供者が在庫から消えると**その行ごと DOM から外れる**。

## 4. 消えたときにフォーカスを戻す仕掛けは無い

- `frontend/src/pages/viewer/InventoryView.tsx:184-199` のフォーカス移動は**依存配列が `[filterView, drawerOpen]`**（`:199`。
  `:183` は `prevDrawerOpenRef` の宣言。独立審査で訂正）。
  画面の切り替え（root ⇄ 選択画面）でしか動かず、**`data` 差し替えでは動かない**。
- リポジトリ全体で `focusout` / `focusin` / `relatedTarget` は**1件も使われていない**
  （`grep -rn "focusout\|focusin\|relatedTarget" frontend/src` が0件）。フォーカス判定はすべて `document.activeElement`。

## 5. 既存の自動検査（歯止め）

- `frontend/src/components/Drawer.test.tsx`: テスト10件あるが **`focus` という語が1件も出てこない**＝フォーカスの検査は0件
  （内容は `size`・`onBack`・`onEscape`・✕ の4系統）。
- `frontend/src/components/Modal.test.tsx`・`frontend/src/components/Sheet.test.tsx`: **ファイル自体が存在しない**
  （＝この2つの金型には単体テストが1件も無い）。
- 画面検査 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`:
  - **A13**（`:261-284`）Tab / Shift+Tab の端での回り込み。
  - **A14**（`:127-142`）画面遷移時のフォーカス位置。
  - **どちらも「行が消えた場合」は測っていない**。
- 閲覧ページ JS の上限は **300KB**（`frontend/scripts/check-viewer-bundle.js:21`）。便6 時点の実測は 266.7KB
  （`docs/handoff/popover-mold-fix` 便の記録）。

## 6. 作法（この repo の既存ルール）

- 共通の金型は `frontend/src/components/`。**非コンポーネントの共通処理の先例**は
  `frontend/src/components/buttonAppearance.ts`、**DOM に触る再利用処理の置き場**は `frontend/src/hooks/`
  （`useIsMobile.ts`・`useFitTableZoom.ts`・`useExpiryRefresh.ts` などと、その単体テストが同居）。
  `frontend/src/utils/` には現在 `statusPresentation.ts` のみで DOM を触るものは無い。
- ADR-144 §1「`pages/` 配下の UI は原則 `components/` の共通金型を使う」、§4「金型が無い場合は
  実装を止め PO に報告 → 許可を得て `components/` に新設」。
- ADR-067: 色・寸法はトークン（`var()`）参照のみ。**本件は CSS を触らない**ので対象外。

## 7. 閲覧ページ側のハードコード調査（PO 質問への回答根拠）

- `frontend/src/pages/viewer/viewer.css`: `var(--…)` 参照 **38件** / 直値を含む行 **4行**のみ
  （`:129-132` の `left: -9999px; width: 1px; height: 1px;` ＝読み上げ専用の画面外退避）。
- `frontend/src/pages/viewer/*.tsx`（15ファイル）の `style={{` は **全ファイル0件**。
- 便5 の単一選択行 `viewer-choice-row` は**定義も利用も閲覧ページだけ**
  （定義 `viewer.css:66-79` / 利用 `InventoryView.tsx:442,459`）。値はすべてトークン参照だが
  **共通金型としては未登録** → 在庫表へ横展開するには ADR-144 §4 の手続きが必要。**別便で起票（PO 決定）**。

関連: [[salesanchor-viewer-mobile]] / ADR-144 / `docs/handoff/viewer-filter-subscreen/design.md:318`
