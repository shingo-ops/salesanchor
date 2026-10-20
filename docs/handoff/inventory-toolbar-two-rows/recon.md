# recon: 在庫一覧の上部（検索・絞り込み・並び替え）を2段に並べ直す

- 基準: origin/main 2cacc774a（worktree `release/inventory-toolbar-two-rows`）。行番号はこの時点の実ファイル。
- 調査の生出力: リポジトリ外の記録置き場（CC報告ファイル-keep の inventory-toolbar-two-rows/recon フォルダ。recon-raw・recon2-raw・recon3-raw の3つ。Sonnet・読み取りのみ）。
- 対象 ADR（`git grep -i` と FEATURE-INDEX で確認）: ADR-1014（在庫表の見え方）、ADR-1019（閲覧ページは在庫表と同じ金型で作る・`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:26`）、ADR-093（詳細フィルタ・表示条件）、ADR-144（金型の先確認）、ADR-067（トークン）、ADR-027（i18n）、ADR-137（PC/スマホの分け方）。

## 1. アプリの在庫表 `/inventory`

- 上部は金型 `ContentToolbar` の left だけを使い、1段で横に並ぶ（`frontend/src/pages/inventory/InventoryPage.tsx:438-512`）。並び: 検索（`inventory-search` :445）→ リセット → 24時間以内 → 並び替え（SelectControl）→ 提供者（MultiSelect・スマホでは出さない）→ 詳細フィルタ（`inventory-filter-toggle` :507）。
- 価格・数量・状態（コンディション）は、詳細フィルタの中の「表示条件」の枠にある（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:196-272`）。状態はチェックボックス（:212）、範囲は TextFieldControl に直書き幅 `style={{ width: "6rem" / "7rem" }}`（:259-272）。
- 価格・数量・状態は「フィルタを有効化」（`filterEnabled`・:132）が ON のときだけ API に渡る（`frontend/src/pages/inventory/InventoryPage.tsx:212`・`:215-224`）。OFF だと入れても効かない。
- 保存: 詳細フィルタの値は `PATCH /me/inventory-filters` で250ms後に自動保存（`frontend/src/pages/inventory/InventoryPage.tsx:345`）。保存項目は `backend/app/routers/me_inventory_filters.py:29-51`（enabled・show_conditions・qty_min/max・price_min/max ほか）。検索・並び・提供者・24時間以内は保存しない（`frontend/src/pages/inventory/InventoryPage.tsx:137-160` のコメント）。
- リセット（`frontend/src/pages/inventory/InventoryPage.tsx:356-363`）は検索語・カテゴリー・並び（発売日の新しい順）・ページだけを戻す。詳細フィルタは「意図的な設定なので保持」とコメントにある。
- ファイル行数: `frontend/src/pages/inventory/InventoryPage.tsx` 636行。`frontend/src/pages/inventory/InventoryFilterPanel.tsx` は「ページ行数上限対策」で切り出した（同ファイル冒頭コメント）。
- PC/スマホの境目: `useIsMobile` = 幅767px以下（`frontend/src/hooks/useIsMobile.ts`・`frontend/src/constants/breakpoints.ts` MOBILE_MAX 767）。768px以上で 1280px 未満を分ける JS は無い（recon2 §G）。

## 2. 閲覧ページ `/viewer/`

- 上部は自前の `div.viewer-toolbar`（`frontend/src/pages/viewer/InventoryView.tsx:178`・`viewer.css` の `.viewer-toolbar` は flex で折り返す）。並び: 検索 → 24時間以内 → 並び替え → 提供者（PCのみ）→ 絞り込み（`viewer-filter-toggle` :222・PCでも出る）。
- 価格・数量・コンディションは引き出し（Drawer）の中（`frontend/src/pages/viewer/InventoryView.tsx:252-312`）。PC でも引き出しを開かないと触れない。
- 絞り込みはすべて手元の行で行う（`frontend/src/pages/viewer/viewerFilter.ts` の `filterRows`）。サーバーに保存しない。リセットボタンは無い。
- 文言は閲覧専用の辞書 `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json`（アプリの辞書は読まない）。リセット用のキーは無い（`viewer.reset.*` はパスワード再発行用で別物）。

## 3. スプレッドシートの在庫一覧（GAS）

- 写し: `~/CC報告ファイル-keep/inventory-name-hover-card/gas/prod_stage/index.html`（本番版19と同じ中身。test 版29 の stage と index.html は一致）。
- 1280px以上は2段の grid（`index.html:334-367`）: 1段目 [検索][価格][在庫数][並び替え][更新]、2段目 [コンディション][提供者][24時間以内]。768〜1279px は折り返し、767px以下は引き出し。
- 「更新」（`index.html:905`）はデータを取り直す。PC にリセットは無い（引き出しの「クリア」はスマホだけ）。

## 4. 金型・トークン

- `ContentToolbar`（`frontend/src/components/ContentToolbar.tsx`）は left/right の2枠だけ。CSS は `flex-wrap: nowrap`（2段にしない、とコメントあり）。
- 範囲入力（数字2つを「〜」でつなぐ）の金型は無い。前例は `frontend/src/pages/inventory/InventoryFilterPanel.tsx:257-272` と `frontend/src/pages/viewer/InventoryView.tsx:265-310` の2か所だけ。
- 幅トークン: `--input-width-price: 120px`（`frontend/src/tokens.css:418`）、`--input-width-qty: 70px`（:413）。
- MultiSelect はボタンに「{label}: すべて」と出る。

## 5. 試験（ツールバーを触るもの）

- `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx`（並び替え・リセット）、`frontend/src/pages/inventory/InventoryPage.settings.test.tsx`（24時間以内）、`frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx`（提供者・検索）、`frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx`（詳細フィルタのボタン）、`frontend/src/pages/viewer/InventoryView.test.tsx`（並び替え・24時間以内）。
- 詳細フィルタの中身（`inventory-cond-*`・`inventory-qty-min` 等）を見る試験は無い（recon2 §E）。

## 6. API

- `/inventory` は `condition_in`・`supplier_ids`・`price_min/max`・`qty_min/max`・`sort/order` を既に受ける（`backend/app/routers/inventory_offers.py`）。サーバー側の変更は要らない。

## 7. 本番の保存値（影響の大きさ）

- reader 鍵で SELECT 1回（ADR-1024。読んだのは `ai_ro.public__user_inventory_filters`。SQL と結果は同じ記録置き場の q.sql・q.out）。
  - 保存している人 3 / 有効化 ON 1 / 有効化 OFF 2
  - 有効化 OFF で状態か範囲が保存されている人: **0**（状態だけ 0、範囲だけ 0）
  - → 価格・数量・状態を有効化スイッチから外しても、開いた瞬間に急に絞り込まれる人はいない。

## 8. 金型の手続き（記録置き場の recon3-raw §2・§3）

- `ContentToolbar` の呼び出し元は約60ファイル。stories は `frontend/src/components/ContentToolbar.stories.tsx`。単体テストは無い。
- 規格は `docs/specs/design-system/component-ssot/page-header-v2/design.md` §2.5 だけ。操作台を2行にする規定は無い（「2段」はボタン置き場のルール名だけ）。
- `docs/CC_UI_GOVERNANCE.md`・ADR-144 §4 は「金型が無いとき新設は PO 許可」を定める。既存金型に枠を足す手続きの記述は無い。
