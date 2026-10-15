<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 3 design — modal-overlay-zindex（Drawer の中で開いた確認ダイアログが隠れる）

**recon**: `docs/handoff/modal-overlay-zindex/recon.md`  
**ADR**: `docs/adr/ADR-067-design-token-enforcement.md`（z-index はトークン参照のみ）、`docs/adr/ADR-073-design-system-kgi-rubric.md`

## 1. 原因
`.comp-modal-overlay`（`frontend/src/components/Modal.css`:12-17）が --z-backdrop(298) で重ね順の文脈を作り、中のダイアログの 400 が外で効かない。Drawer のパネルは 301（`frontend/src/components/Drawer.css`:33）。298 < 301 で隠れる。

## 2. KGI
要確認ページの商品ドロワーで「このままで良い」を押すと、確認ダイアログがドロワーの手前に出て、ボタンを押せる（PO が画面で○×を判定）。

## 3. 案

| 案 | 内容 | 利点 | 欠点 |
|---|---|---|---|
| A | `.comp-modal-overlay` を --z-modal(400) にする | 1行。Modal 全体で一貫する。トークンのみ | Sheet の overlay(298) など 298 帯の層は Modal より下になる |
| B | Drawer を 301 から 298 未満に下げる | Modal 側は無変更 | avatar(300) との関係（tokens.css:127 のコメント）を壊す。topbar.css:160 等にも波及 |
| C | Drawer 内の確認だけ別の Modal 実装にする | 局所 | 金型の二重化。ADR-144 の方針に反する |

選択: A。理由: 変更が1行で、トークンの序列（Modal 400 > Drawer 301）が意図どおりになる。B は他の層に波及し、C は部品が二重になる。

## 4. 変更内容（触るのはこの4か所だけ）
- `frontend/src/components/Modal.css`:16 `z-index: var(--z-backdrop);` → `var(--z-modal);`（直前に日本語コメント）
- `frontend/src/components/Drawer.tsx`:12、`frontend/src/components/Drawer.css`:6 のコメントを実際の値（301、Modal の overlay は 400 で前面）に直す。
- `frontend/src/pages/design-system/DesignSystemPage.tsx`:316 の表示値 "299" → "301"。
- 触らない: `frontend/src/pages/inbox/InboxPage.css` の 210 への引き下げ、InventorySearchBar 等のコード。数値の直書きは足さない。

## 5. 検証

| 基準 | 検証方法 |
|---|---|
| 型検査とビルドが通る | `npm run build`（結果 73-build.txt、exit=0） |
| z-index の数値直書きが増えない | `node scripts/check-css-hardcoded-values.js`（73-css-check.txt、PASSED） |
| lint が通る | eslint（73-lint.txt、exit=0） |
| 画面で確認ダイアログが Drawer の手前に出る | 要確認ページで商品ドロワーを開き「このままで良い」を押す。.comp-modal-overlay の computed z-index が 400、.comp-drawer-panel が 301（73-visual.txt は未実施。PO の目視で確認） |
| 他の Modal の見え方が変わらない | Drawer と同時に開かない Modal は順序が変わらない（影響範囲の表を参照） |

## 6. 外部事例
不要。理由: 自社トークンの序列を実際の値に揃えるだけの修正で、設計上の新しい選択が無い（stacking context の仕様は CSS の標準）。

## 7. 影響範囲
- Modal の呼び出し元 67 ファイル（72-modal-consumers.txt）。Modal を開く全画面で overlay が 298 から 400 になる。
- 順序が入れ替わる相手は 298 超 400 以下の層だけ: Drawer(301)、avatar(300)、同値 400（ContextMenu・Sheet 本体）。Sheet の overlay(298) は Modal より下になる。400 同士は後から開いた方が前面。
- 50 の部品（Popover / Tooltip / AsyncCombobox / InventorySearchBar）は変更前後とも overlay の下で、順序は不変。
- Toast(500) は Modal より前面のまま。

## 8. 戻し方
Modal.css:16 を `var(--z-backdrop)` に戻す（1行の revert。コメント修正は独立して残してよい）。

## 9. 測り方
PO が要確認ページで商品ドロワー→「このままで良い」を押し、確認ダイアログが見えてボタンが押せるか（○×）。開発者ツールで .comp-modal-overlay の computed z-index が 400 であること。

## 10. 維持の仕組み
- z-index は ADR-067 のチェック（`npm run check:css-values`、pre-commit）で数値直書きが止まる。
- コメントを実際の値に揃えたので、同じ誤解（299）が再発しにくい。
- 重ね順の序列を変えるときは tokens.css の値と DesignSystemPage の表示を同時に直す。

## 11. 残件
- Popover / Tooltip / AsyncCombobox（--z-dropdown=50、body portal）が Modal 内で使われる場合、変更前から overlay の下に隠れる可能性がある。Modal 内の使用有無は未調査・本件対象外（変更前後で順序は不変）。
- 実機の computed z-index 確認（73-visual.txt）は未実施。
