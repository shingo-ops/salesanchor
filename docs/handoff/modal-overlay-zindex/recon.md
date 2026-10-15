<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 2 recon — modal-overlay-zindex（Drawer の中で開いた確認ダイアログが隠れる）

**基準**: origin/main 65ed8cd8b（worktree release-modal-overlay-zindex）  
**日付**: 2026-10-15  
**担当**: 調査・実装 Sonnet、設計 Opus。生出力は /tmp/CC報告ファイル/realtime-stage1/（72-dialog-zindex-recon.txt、72-modal-consumers.txt、73-precheck.txt、73-precheck-wt.txt）

## 0. 既存 ADR の検索

- `git grep -n "z-index\|z-modal\|z-backdrop" docs/adr/` の該当は次の2件。
  - `docs/adr/ADR-067-design-token-enforcement.md`:104,165（z-index の数値ハードコードを禁止し、`npm run check:css-values` で検出する）
  - `docs/adr/ADR-073-design-system-kgi-rubric.md`（デザインシステムの評価基準）
- docs/adr/FEATURE-INDEX.md に Modal の重ね順を決めた行は無い。重ね順の序列を決めた ADR は無い（トークンの値だけが正本）。
- 今回の変更は ADR-067 に沿う（トークン参照のみ。数値の直書きを足さない）。

## 1. 不具合の原因

- `frontend/src/components/Modal.css`:12-17 の `.comp-modal-overlay` は `position: fixed` で、変更前は `z-index: var(--z-backdrop)`（298）だった。
- `frontend/src/components/Modal.css`:32 のダイアログ本体は `var(--z-modal)`（400）。ただし overlay が重ね順の文脈を作るので、400 は overlay の内側でしか効かない。外側から見た Modal の順位は overlay の 298 になる。
- `frontend/src/components/Drawer.css`:33 のパネルは `var(--z-drawer)`（301）。298 < 301 なので、Drawer の中で開いた Modal は Drawer の下に隠れる。
- トークン値: `frontend/src/tokens.css`:121-130（dropdown 50 / backdrop 298 / avatar 300 / drawer 301 / modal 400 / toast 500）。
- Modal は `frontend/src/components/Modal.tsx`:114 で document.body へ portal する。

## 2. 古いコメント・表示値（実際の値と食い違い）

- `frontend/src/components/Drawer.tsx`:12 と `frontend/src/components/Drawer.css`:6 が「(299)」「Modal (400) より下」と書いていた。実際は 301。
- `frontend/src/pages/design-system/DesignSystemPage.tsx`:316 が `--z-drawer` を "299" と表示していた。実際は 301。

## 3. 再点検（worktree 基準 65ed8cd8b）

- 最初の点検は本店 main（650005f29）で行ったが、本店は origin/main より 2388 コミット遅れていた。worktree（65ed8cd8b）で同じ grep を流し直した。結果は 73-precheck-wt.txt。
- 結果が変わった点: `InventoryPicker` と `PurchaseOrdersFormModal` は worktree に存在しない。代わりに body へ portal する部品が増えている。
  - `frontend/src/components/Popover.css`:10,17、`frontend/src/components/Tooltip.css`:8、`frontend/src/components/AsyncCombobox.css`:19 は --z-dropdown(50)。
  - `frontend/src/components/InventorySearchBar.tsx`:372 も 50。Modal 内での使用は grep で検出されなかった。
  - `frontend/src/components/ContextMenu.css`:9 と `frontend/src/components/Sheet.css`:39 は --z-modal(400)。Sheet の overlay（`frontend/src/components/Sheet.css`:23）は --z-backdrop(298)。
  - `frontend/src/components/loading/Toast.tsx` は --z-toast(500)。
- 順序が入れ替わるのは 298 より大きく 400 以下の層（avatar 300、drawer 301、400 同値）だけ。50 の部品は変更前も後も overlay より下で、関係は変わらない。

## 4. Modal の呼び出し元

- 67 ファイル（一覧は 72-modal-consumers.txt）。Modal.css の変更は全てに効く。重ね順が変わるのは Drawer(301)・avatar(300) と同時に開いた場合だけ。
