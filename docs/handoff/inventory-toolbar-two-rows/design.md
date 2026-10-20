# 設計: 在庫一覧の上部を2段にする（検索の右に価格・数量、2段目に並び替え・コンディション・提供者）（第1版）

- PO 依頼（2026-10-20）: 「在庫一覧の上部の作りだが検索欄の右側に価格と数量の絞り込み機能、検索欄の下側に2行目として並び替え、コンディション絞り込み、提供者絞り込みをアプリ側にも整理して表示してほしい」
- PO 決定（2026-10-20「1」）: 下の形で、アプリ・閲覧ページ・在庫一覧（GAS）の3つをそろえる。パソコン幅だけ。スマホは今のまま「絞り込み」から開く。
  ```
  1段目: [検索欄] [価格 最低〜最高] [数量 最小〜最大]
  2段目: [並び替え] [コンディション] [提供者]      [24時間以内] [リセット]
  ```
- recon: `docs/handoff/inventory-toolbar-two-rows/recon.md`
- 対象 ADR: ADR-1014（本設計で改訂を足す）、ADR-1019、ADR-093、ADR-144、ADR-067、ADR-027、ADR-137。

## 1. 目的・利用者に見える変化

- 変更前（アプリ）: 上部は1段。価格・数量・状態は「詳細フィルタ」を開き、さらに「フィルタを有効化」を ON にしないと効かない（recon §1）。
- 変更前（閲覧ページ）: 価格・数量・コンディションは「絞り込み」の引き出しを開かないと触れない（recon §2）。
- 変更後（パソコン幅 768px 以上、アプリ・閲覧ページ）:
  - 1段目: 検索欄、その右に価格（最低価格〜最高価格）、数量（最小数量〜最大数量）。
  - 2段目: 並び替え、コンディション、提供者（アプリはその右に「詳細フィルタ」）。右端に「24時間以内」「リセット」。
  - 価格・数量・コンディションは、入れたらすぐ効く（スイッチ不要）。
- 変更後（GAS 在庫一覧、1280px 以上）: 並び替えを1段目の右から2段目の先頭へ移す。GAS のリセット位置には今の「更新」を置く（GAS はデータの取り直しが要るため。リセットは GAS に足さない）。
- スマホ（767px 以下）: 3画面とも今の並びのまま。

## 2. 設計判断

### D1 境目の幅
- アプリ・閲覧ページは 768px 以上で2段（アプリの標準 `useIsMobile`。提供者・行クリックの出し分けと同じ線。recon §1）。
- GAS は今の 1280px 以上の2段 grid を並べ替えるだけ（768〜1279px は今の折り返しのまま）。GAS の境目を変えると 768〜1279px の見え方が全部変わるため、今回は動かさない。
- 768〜1279px のアプリでは、段の中で幅が足りないとき段内で折り返す（はみ出させない）。

### D2 価格・数量・コンディションは「フィルタを有効化」から外す（アプリ）
- ツールバーに出した入力が、スイッチ OFF で効かないのは見た目と動きが食い違うため、この3つは常に効かせる。
- 保存は今のまま同じ項目（`show_conditions`・`qty_min/max`・`price_min/max`）を使う。新しい保存場所は作らない（SSOT）。
- 「フィルタを有効化」は残りの項目（シリーズの表示/非表示・形態・在庫/予約）だけに効く。
- 詳細フィルタの中の状態チェックと範囲入力は消す。スマホでは、ツールバーに無いので、詳細フィルタの先頭（提供者の下・有効化スイッチの上）に同じ部品（コンディション MultiSelect と範囲入力）を出す。提供者と同じ扱い。
- 影響: 本番で「スイッチ OFF なのに状態・範囲が保存されている人」は 0人（recon §7）。開いた瞬間に見え方が変わる人はいない。

### D3 リセットの動き（変えない）
- アプリのリセットは今と同じ（検索語・カテゴリー・並び）。価格・数量・コンディション・提供者・24時間以内は戻さない。
- 閲覧ページに同じ動きのリセットを足す（検索語・並び・ページ）。PO の配置図のリセットを閲覧ページにもそろえるため。

### D4 金型
- `ContentToolbar` に2段目の枠 `bottomLeft`・`bottomRight` を足す（既存金型の拡張。渡さない画面は今と同じ1段）。2段のときだけ、各段の中で折り返しを許す。
- 範囲入力は `ContentToolbar` の部品 `ContentToolbarRange` として同じファイルに置く（数字入力2つ＋「〜」。幅はトークン `--input-width-price` を両方に使う。GAS の範囲入力 112px とほぼ同じ）。直書き幅（6rem/7rem）はなくなる。
- 閲覧ページのパソコン幅は、自前の `viewer-toolbar` をやめて `ContentToolbar` を使う（ADR-1019「同じ金型」）。スマホは今の `viewer-toolbar` のまま。
- 新しいトークンは作らない。
- 手続き: ADR-144 の PO 許可は「金型を新設するとき」の決まりで、既存金型に枠を足す手続きは定めが無い（recon §8）。今回は PO が決めた2段の形をそのまま作るための拡張で、渡さない約60画面は DOM も見た目も変えない。page-header-v2 design §2.5 に「2段目の枠（任意）」と範囲入力の行を追記して規格を1か所に保つ。

### D5 置き場所
- アプリのツールバーは `frontend/src/pages/inventory/InventoryToolbar.tsx` に切り出す（`frontend/src/pages/inventory/InventoryPage.tsx` は636行で、ページ行数の上限対策のため）。状態は今どおり `InventoryPage` が持ち、props で渡す。

## 3. 変更内容

### 3-1 金型 `frontend/src/components/ContentToolbar.tsx`・`frontend/src/components/ContentToolbar.css`
```tsx
interface ContentToolbarProps {
  left?: React.ReactNode;
  right?: React.ReactNode;
  /** 2段目の左（並び替え・絞り込み）。bottomLeft/bottomRight のどちらかを渡したときだけ2段になる */
  bottomLeft?: React.ReactNode;
  /** 2段目の右（切替・リセット） */
  bottomRight?: React.ReactNode;
}
// 2段: <div class="content-toolbar content-toolbar--two-rows">
//        <div class="content-toolbar__row"> left / right </div>
//        <div class="content-toolbar__row"> bottomLeft / bottomRight </div>
//      </div>
// 1段（従来）: 今の DOM のまま（既存の呼び出し元の見た目を変えない）

export interface ContentToolbarRangeProps {
  minValue: string; maxValue: string;
  onMinChange: (v: string) => void; onMaxChange: (v: string) => void;
  minPlaceholder: string; maxPlaceholder: string;   // 表示文字（t() で渡す）
  minAriaLabel: string; maxAriaLabel: string;
  testIdPrefix: string;                              // `${prefix}-min` / `${prefix}-max`
}
// <div class="content-toolbar__range"> TextFieldControl(type=number,min=0,inputMode=numeric,className="field-h-md content-toolbar__range-input")
//   <span class="content-toolbar__range-sep" aria-hidden="true">〜</span> TextFieldControl </div>
```
CSS（トークンのみ）:
```css
.content-toolbar--two-rows { flex-direction: column; align-items: stretch; gap: var(--space-2); }
.content-toolbar__row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); min-width: 0; }
.content-toolbar--two-rows .content-toolbar__left,
.content-toolbar--two-rows .content-toolbar__right { flex-wrap: wrap; }
.content-toolbar__range { display: flex; align-items: center; gap: var(--space-1); }
.content-toolbar__range-input { width: var(--input-width-price); }
.content-toolbar__range-sep { color: var(--text-muted); }
```
- 「〜」は記号で言語に依存しないため文字のまま置く（GAS・既存パネル :261 と同じ）。i18n 検査で止まる場合は辞書キーにする。
- 単体テスト・stories に2段の例と範囲入力の例を足す。

### 3-2 アプリ `frontend/src/pages/inventory/InventoryToolbar.tsx`（新規）・`frontend/src/pages/inventory/InventoryPage.tsx`・`frontend/src/pages/inventory/InventoryFilterPanel.tsx`
- PC（`!isMobile`）:
  - left: 検索（`inventory-search`・`field-w-md`）、価格の範囲（`inventory-price-min/max`）、数量の範囲（`inventory-qty-min/max`）
  - bottomLeft: 並び替え（`inventory-sort-menu`）、コンディション MultiSelect（`inventory-condition-filter`・選択肢は `conditionFacet`・値は `showConditions`）、提供者（`inventory-supplier-filter`）、詳細フィルタ（`inventory-filter-toggle`）
  - bottomRight: 24時間以内（`inventory-fresh-toggle`）、リセット（`inventory-reset-sort`）
- スマホ: 今の1段の並びのまま（検索・リセット・24時間以内・並び替え・詳細フィルタ）。
- `frontend/src/pages/inventory/InventoryPage.tsx` の取得部（:212・:215-224）: `condition_in`・`qty_*`・`price_*` の `filterEnabled &&` を外す。`unit_in`・`offer_type_in`・`hide_categories` は今のまま `filterEnabled` 付き。
- `frontend/src/pages/inventory/InventoryFilterPanel.tsx`: 状態チェック（:205-220 付近）と範囲入力（:257-272）を消す。スマホだけ先頭（提供者の下）に、コンディション MultiSelect と範囲入力2つを出す（`showSupplierSelect` と同じ条件）。
- 文言（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー）:
  - `inventory.conditionFilter.label` コンディション / Condition
  - `inventory.conditionFilter.clear` 選択をクリア / Clear selection、`.all` すべて / All、`.count` {{count}}件 / {{count}} selected
  - `inventory.range.priceMin` 最低価格 / Min price、`.priceMax` 最高価格 / Max price、`.qtyMin` 最小数量 / Min qty、`.qtyMax` 最大数量 / Max qty
  - 不要になる `inventory.filterPanel.min/max` は他で使っていなければ消す（grep で確認）。

### 3-3 閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx`（`frontend/src/pages/viewer/viewer.css` はスマホ側で今も使うため変更なし）・`frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json`
- PC: `ContentToolbar` で同じ並び（`viewer-search`、`viewer-price-min/max`、`viewer-qty-min/max` / `viewer-sort-menu`、`viewer-condition-filter`、`viewer-provider-filter` / `viewer-fresh-toggle`、`viewer-reset`）。「絞り込み」ボタンは PC では出さない。
- スマホ: 今のまま（引き出しに提供者・コンディション・範囲）。
- リセット: 検索語・並び（既定）・ページを戻す。
- 文言（閲覧辞書 ja/en）: `viewer.resetView` リセット / Reset（実装時に改名: `resetSort` は閲覧用 JS にアプリ辞書が混ざっていないかを見る目印語で、`frontend/scripts/check-viewer-bundle.js` が止めるため）、`viewer.range.priceMin` 最低価格 / Min price ほか4つ（アプリと同じ文）。
- 閲覧ページの配信物の上限（300KB）を超えないこと（今 248KB）。

### 3-4 GAS 在庫一覧（`index.html` の 1280px 以上の grid だけ）
```css
grid-template-columns: max-content max-content 1fr max-content max-content;
grid-template-areas:
  "search search search price stock"
  "sort   filters .     fresh refresh";
```
- HTML・JS は変えない（並びは CSS の grid-area だけで決まる。`#sortSelect { grid-area: sort; }` 等は既存）。
- 写し: `~/CC報告ファイル-keep/inventory-toolbar-two-rows/gas/`（本番版19・テスト版29 から作る）。反映は PO が `!` で実行。

## 4. 触らない範囲
- サーバー（API・保存の形・DB）。並び替えの選択肢と既定の並び。表の列。行クリック・カード。スマホの並び。GAS の 1280px 未満。GAS の JS。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 アプリ PC 幅で1段目が 検索→価格→数量 の順 | 単体テスト（DOM 順）＋ PO 目視 |
| K2 アプリ PC 幅で2段目が 並び替え→コンディション→提供者（→詳細フィルタ）、右に 24時間以内・リセット | 単体テスト＋ PO 目視 |
| K3 アプリで「フィルタを有効化」OFF のまま価格・数量・コンディションを入れると API に `price_min`・`qty_min`・`condition_in` が付く | 単体テスト（api.get の引数） |
| K4 アプリで形態・在庫/予約・シリーズ除外は有効化 OFF では付かない（今と同じ） | 単体テスト |
| K5 閲覧ページ PC 幅で同じ2段、絞り込みボタンが無い、リセットで検索語と並びが戻る | 単体テスト＋ PO 目視 |
| K6 スマホ幅（767px 以下）は3画面とも今の並び | 単体テスト（matchMedia を偽装）＋ PO 目視 |
| K7 GAS 1280px 以上で 1段目 検索・価格・在庫数、2段目 並び替え・コンディション・提供者・24時間以内・更新 | clasp pull で中身一致＋ PO 目視 |
| K8 直書きの色・幅・日本語が無い | lint・i18n 検査・design-token 検査が緑 |
| K9 本番に反映された | 配信物に `content-toolbar--two-rows` が入っていることを curl で確認 |

## 6. 代替案
- A: 詳細フィルタの値はそのままにして、ツールバーには別の（保存しない）入力を置く → 同じ意味の値が2か所になり SSOT に反する。却下。
- B: スイッチ ON のときだけ効く入力をツールバーに出す → 入れても効かない場面が残り、PO の意図（すぐ絞り込める）に合わない。却下。
- C: 2段の部品を在庫表専用で作る → ADR-1019 で閲覧ページと同じ金型を使う決まり。既存金型の拡張にする。

## 7. リスクと対処
- 本番の保存値で急に絞り込まれる人が出る → 0人（recon §7）。今後も値はツールバーに見え、消せば戻る。
- ContentToolbar の既存約60画面が崩れる → 2段の枠を渡したときだけ別の DOM にし、従来の DOM は1文字も変えない。単体テストで「枠なし＝従来 DOM」を固定する。
- 768〜1279px で窮屈 → 段内で折り返す。PO 目視で確認。
- 戻し方: アプリは PR を revert。GAS はテストを版29、本番を版19 へ redeploy。

## 8. 外部・過去事例の参照と我々への応用
- 不要: 既存の GAS 在庫一覧が同じ2段の形で動いており（recon §3）、それに合わせる変更のため。

## 維持の仕組み
- 守り手: 金型の2段目枠は `frontend/src/components/ContentToolbar.test.tsx`（渡さない画面の DOM を固定）、並びと常時適用は `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx`。GAS の写しは人手で守る（理由: GAS は CI の試験の外。ADR-1014 の方針でアプリと一緒に直す）。
- 正本は `ContentToolbar`（金型）と ADR-1014 改訂。GAS の CSS は写しで、アプリの並びを変えたら一緒に直す（ADR-1014 の既存方針）。
