# recon: 確認窓（Modal）と下から出るパネル（Sheet）に単体テストが1件も無い（宿題 E4）

> この文書は何か（1行）: 宿題 E4（`Modal`・`Sheet` の2金型に単体テストが1件も存在しない）の現物調査。
> **すべて 2026-10-27 時点の現物を開いて確認した事実**（設計担当が自分で測った）。

**日付**: 2026-10-27 ／ **土台**: `release/modal-sheet-unit-tests`（`origin/main` = `acc8d11ca`＝便8 #4805 を含む）
**起票の原文**: `docs/handoff/viewer-focus-trap/design.md` ⑫ E4（便7）／`docs/handoff/drawer-inert-when-closed/design.md` ⑫ F4（便8）

## 1. テストファイルの有無（実測）

| ファイル | 状態 |
|---|---|
| `frontend/src/components/Modal.test.tsx` | **存在しない** |
| `frontend/src/components/Sheet.test.tsx` | **存在しない** |
| `frontend/src/components/Drawer.test.tsx` | **存在する（`it(` が10件）** |

`Drawer.test.tsx` の中身（見出しの実測）: `Drawer size`（4件・既定幅480px と wide のトークン）／
`Drawer onBack`（3件）／`Drawer onEscape`（3件）。**フォーカス関連は0件**（便7 recon §5 と一致）。

> 便7（#4800）と便8（#4805）で `frontend/src/hooks/useFocusTrap.test.tsx` が
> `Drawer`・`Modal`・`Sheet` を**共通の仕掛けの側から**28件測るようになった。
> ただしそれは「出口封じ」と「閉じている間の無効化」だけで、**金型そのものの公開された振る舞い**
> （開閉・読み上げ名・大きさ・背景クリック・フッタの有無）は `Modal`・`Sheet` では1件も測っていない。

## 2. `Modal` の公開プロパティと振る舞い（現物）

`frontend/src/components/Modal.tsx`:

| 行 | 事実 |
|---|---|
| `:25-33` | props は `open` / `onClose` / `title`（必須）/ `size?`（`"sm" \| "md" \| "lg" \| "xl"`・既定 `md`）/ `dismissOnOverlay?`（既定 **true**）/ `children` / `footer?` |
| `:50-58` | 開く直前の `document.activeElement` を覚え、閉じたら戻す |
| `:61-68` | 開いたら中の最初のフォーカス可能要素へ移す |
| `:70-80` | Esc で `onClose`（`e.stopPropagation()` 付き） |
| `:84` | 出口封じは共通の `useFocusTrap(open, dialogRef)` |
| `:86` | **`if (!open) return null;`＝閉じると DOM から消える**（`Drawer`・`Sheet` と違う所） |
| `:88-98` | `document.body` へポータル。外側 `.comp-modal-overlay` の `onClick` は `dismissOnOverlay` が true のときだけ `onClose` |
| `:92-99` | 本体は `.comp-modal-dialog comp-modal-dialog--<size>`・`role="dialog"`・`aria-modal="true"`・`aria-labelledby={titleId}`・`onClick` で `stopPropagation`（本体クリックでは閉じない） |
| `:104-113` | 題は `<h2 id={titleId} class="comp-modal-title">`、✕ は `aria-label={t("common.close")}`（**`data-testid` は無い**） |
| `:119-121` | `footer != null` のときだけ `.comp-modal-footer` を描く |

## 3. `Sheet` の公開プロパティと振る舞い（現物）

`frontend/src/components/Sheet.tsx`:

| 行 | 事実 |
|---|---|
| `:30-37` | props は `open` / `onClose` / `title` / `children` / `footer?` のみ（`size` は無い） |
| `:88` | `if (!portalTarget) return null;`＝**描き先が決まる前だけ** null。決まった後は**閉じていても DOM に残る** |
| `:93-99` | オーバーレイは **開いているときだけ**描かれ、`onClick` で `onClose`、`aria-hidden="true"` |
| `:101-109` | 本体は `.comp-sheet-panel`（開いていると `--open` が付く）・`role="dialog"`・`aria-modal="true"`・`aria-labelledby`・`data-testid="sheet-panel"` |
| `:113-125` | 題は `<h2 id={titleId}>`、✕ は `data-testid="sheet-close"`・`aria-label={t("common.close")}` |
| `:131-133` | `footer != null` のときだけ `.comp-sheet-footer` を描く |

## 4. テストの作法（既存の先例）

- 置き場は**金型の隣**（`frontend/src/components/Drawer.test.tsx` の先例）。`npm run test:unit` と
  pre-commit の両方で走る（`vitest.unit.config.ts` の include は `src/**/*.test.{ts,tsx}`）。
- **テスト名は英語**にする（`local/no-japanese-literal` が文字列の日本語を止めるため。
  `frontend/src/hooks/useFocusTrap.test.tsx` も英語名。説明は日本語のコメントで書く）。
- `i18n` を読み込んでから金型を描く（`frontend/src/hooks/useFocusTrap.test.tsx:19` の `import "../i18n";`）。
  ✕ の読み上げ名は辞書の `common.close` 由来なので、辞書を読まないと名前で掴めない。
- `Drawer`／`Sheet` は描き先を後から決める2段構えなので、**`open=false` で描いてから `open=true` へ
  差し替える**（`frontend/src/hooks/useFocusTrap.test.tsx:71-75` の `openMold` と同じ理由）。
  `Modal` は `document.body` 直書きなので最初から `open=true` でよい。

## 5. この便で入れない（触らない）もの

- **製品コードは1行も変えない**（テストだけを足す便）。
- `Drawer.test.tsx` は既存10件のまま触らない。
- `useFocusTrap.test.tsx`（28件）も触らない。

関連: `docs/handoff/drawer-inert-when-closed/design.md`（便8） / `docs/handoff/viewer-focus-trap/design.md`（便7）
