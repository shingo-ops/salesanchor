<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する） -->
# recon — 要確認の一覧で、件を開かずに各行で直す

**仕事名**: 要確認の一覧の各行で、商品と「このままで良い」を直す
**日付**: 2026-10-13
**基準**: origin/main = 9ecefd3de822ca33014d914a3ceb53ce3dcef647（worktree 作成時。fetch 済み）
**対象ADR**: ADR-144、ADR-027、ADR-067
**担当**: 実装（Sonnet）。設計は Opus

---

## ADR の検索結果

- 検索語 combobox / autocomplete / オートコンプリート を `docs/adr/` と `docs/adr/FEATURE-INDEX.md` で検索した結果、ADR 本文に該当は 0 件。
- `docs/adr/ADR-144-ui-component-governance.md:59-63`「金型がない場合の手順」: 実装を止めて PO に報告 → PO 許可を得て `components/` に新設（`Xxx.tsx` + `Xxx.css`（var() のみ）+ `Xxx.stories.tsx`）→ 金型を使って実装。PO は 2026-10-13 に「y」で許可済み。
- `docs/adr/ADR-144-ui-component-governance.md:37`: 生 `<input type="text">` は禁止。`TextFieldControl` を使う。
- ADR-027（`docs/adr/ADR-027-ui-internationalization.md`）: 全 UI 文字列は `t("key")`。ja と en は同一キー。
- ADR-067（`docs/adr/ADR-067-design-token-enforcement.md`）: 色・余白・重なりは var() のトークン。直値禁止。

## file:line 引用表（基準 SHA の時点）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:152` | 読み直しのたびに `setData(null)` で表が一度消える |
| `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:323` | 本番タブの列定義 `productionColumns` |
| `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:470` | 行クリックで件を開く（`onRowClick={setDrawerItem}`） |
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:4` | 「このままで良い」は v102 の件だけ。`POST /tcg/items/{id}/review-ack` |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:420` | 商品の保存の送る中身（`postCorrection`）。field_name='product_id'、system_value=今の product_uuid |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:415` | 商品の候補は `GET /tcg/products/search?query=` |
| `backend/app/routers/item_corrections.py:128` | `POST /tcg/items/{extraction_item_id}/corrections` |
| `backend/app/routers/item_corrections.py:179` | `POST /tcg/items/{extraction_item_id}/review-ack` |
| `backend/app/routers/tcg_product_master.py:165` | `GET /tcg/products/search` |
| `frontend/src/components/DataTable.css:12-18` | `.comp-table` は `overflow-x: auto`（縦も auto になる） |
| `frontend/src/components/DataTable.tsx:94` | セル内の button / input などでは行クリックを発火しない |
| `frontend/src/components/DataTable.tsx:168` | 表とページ送りを包む枠は `.comp-table` |
| `frontend/src/components/CountryCombobox.tsx:147` | 前例の一覧は position:absolute（枠で切れる作り） |
| `frontend/src/components/Popover.tsx:101` | 位置は開いたときの 1 回だけ。スクロール・リサイズに追従しない |
| `frontend/src/components/Popover.tsx:125` | トリガーのクリックで開閉が切り替わる |
| `frontend/src/tokens.css:121` | `--z-dropdown` |
| `frontend/scripts/check-stories-count.js:32` | `components/` の各 tsx に `.stories.tsx` が必要 |

## 実測（Chromium）

- `.comp-table` と同じ CSS の表の一番下の行に position:absolute の一覧を置くと、枠の外には出ずに枠の中のスクロールになる（clientHeight 144 / scrollHeight 371）。詳細は design.md の §10。
- 実装後の同じ確認（実コンポーネント・実 CSS・一番下の行）は、最終報告の生出力を参照。

## e2e

- `frontend/tests-e2e/` に、要確認の一覧（本番の確認待ちのタブ）を対象にした spec は無い（「ack」「analysis-results」「needsReview」「Keep as is」で検索して 0 件）。更新対象なし。

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | 実際のアプリ画面（ログイン・二段階認証が要る）での見え方 | 未確認。PO の操作で確かめる（design.md 受入条件 6） |
| 2 | 本番に反映されたあとの bundle の鍵 | 未確認（デプロイ後に確かめる） |

**未解決ゼロ確認**: 上の 2 件を除き解消済み
