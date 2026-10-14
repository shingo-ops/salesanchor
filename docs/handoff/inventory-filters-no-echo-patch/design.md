# design: 同内容 PATCH を出さない

関連: recon.md、docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md

## 変更
- frontend/src/pages/inventory/InventoryPage.tsx に buildFilterPayload を追加（PATCH 本体と同じ規則）
- lastSavedRef を追加。GET 成功時に f から作った文字列を入れ、保存 effect で同じなら PATCH しない。PATCH 成功時に更新、失敗時は更新しない
- GET 失敗時は lastSavedRef が null のまま＝従来どおり既定値を1回保存

## 触らない範囲
load・loadSeqRef・filtersLoaded ゲート、API クライアント、backend、CSS、i18n

## 受入
|基準|検証方法|
|---|---|
|開いただけでは PATCH 0回|frontend/src/pages/inventory/InventoryPage.noechopatch.test.tsx 1件目。デプロイ後は本番 nginx ログで Opus が確認|
|設定を変えたら保存される|同 1件目（変更で1回、戻すと2回目）|
|取得失敗時の挙動が変わらない|同 2件目（PATCH 1回）|
|既存テストが通る|vitest src/pages/inventory と CommerceNavigationButtonMigration.test.tsx|
|ハードコード文言・色の追加なし|lint 0 errors|

## 外部事例
React の「読込直後の初期値を保存し直さない」定石（dirty チェック／最後に保存した値との比較）。React 公式 docs "You Might Not Need an Effect" の入力値同期の考え方に沿う。新規ライブラリなし。

## 維持の仕組み
- 守り手: InventoryPage.noechopatch.test.tsx（CI の frontend vitest）。戻すと 1件目が赤になる（修正前コードで赤を確認済み）。
