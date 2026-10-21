# コード審査: 在庫一覧の上部を2段にする

- 審査者: Claude Opus（同一 AI の自己審査。独立した第二者レビューではない）
- 対象: commit ad03ecb26（`git diff 2cacc774a..ad03ecb26 -- frontend/src`、1342行を全行読んだ）
- 実装役の検査結果（実装役の報告・生出力 `/tmp/CC報告ファイル/inventory-toolbar/impl/`）: tsc 合格 / lint エラー0 / check:all 24本 終了コード0 / 関係試験 合格 / build 合格 / 閲覧 JS 250.5KB（上限300KB）

## 判定: APPROVE

## 設計との照合
| 設計 | 実装 | 結果 |
|---|---|---|
| D2 価格・数量・状態は有効化スイッチに関わらず適用。形態・在庫予約・非表示カテゴリーは従来どおり | `InventoryPage.tsx` load(): condition_in・qty・price から `filterEnabled` を外し、unit_in・offer_type_in・hide_categories は残る | ○（K3・K4 試験） |
| D2 保存先は同じ項目 | 状態変数（showConditions・qtyMin 等）と自動保存はそのまま。新しい保存先なし | ○ |
| D4 金型は渡さないとき従来 DOM | `ContentToolbar.tsx`: bottomLeft/bottomRight が両方 undefined なら旧 DOM。試験で innerHTML 完全一致 | ○ |
| D4 範囲入力の幅はトークン | `.content-toolbar__range-input { width: var(--input-width-price) }`。直書き幅 6rem/7rem は削除 | ○ |
| D5 ツールバー切り出し | `InventoryToolbar.tsx` 新設、`InventoryPage.tsx` 636→596行 | ○ |
| 配置（PO 承認の図） | PC 1段目 検索→価格→数量 / 2段目 並び替え→コンディション→提供者→詳細フィルタ、右に 24時間以内→リセット | ○（K1・K2 試験）。詳細フィルタは形態等の残りのため2段目左端に残る |
| スマホは従来どおり | アプリ: 1段・状態/価格/数量は詳細フィルタ内。閲覧: 旧 viewer-toolbar＋引き出し | ○（K6・閲覧スマホ試験） |
| D3 閲覧ページにリセット | 検索語・並び・ページを戻す | ○（K5 試験） |
| i18n | アプリ辞書・閲覧辞書とも ja/en 同一キー。未使用になった `inventory.filterPanel.min/max` は grep で他使用なしを確認して削除 | ○ |

## 設計からの変更（1件・承認）
- 閲覧辞書キー `viewer.resetSort` → `viewer.resetView`。`scripts/check-viewer-bundle.js` が「resetSort」をアプリ辞書混入の目印として検査しているため。文言は設計どおり。design.md §3-3 を更新済み。

## 気づき（直さない・理由つき）
- 「〜」は金型内の記号1文字で、既存パネルと同じ扱い。i18n 検査は通過。
- stories の生 `<input>`/`<select>` は見本用（既存 stories と同じ扱い）。検査通過。
- 閲覧ページの引き出し内 `{isMobile && providerSelect}` は外側も isMobile 条件になったため冗長だが動作は同じ。
- 768〜1279px の見え方は単体試験で判定できない → PO 目視（K1・K2・K5）。
