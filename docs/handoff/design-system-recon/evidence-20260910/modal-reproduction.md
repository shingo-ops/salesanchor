# Modal footer 検証の再現・結果

基準7606ca9a041e315b81040373e8f4ddebbc562133。製品2ファイルはmodal-manifest.jsonに固定。実行環境 Node v24.12.0 / React18.3.1 / Playwright1.60.0 / Vite8.0.16。

原稿は作業tree `/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared` と保存先 `/tmp/frontend-raw-buttons-20260911` の絶対パスに依存する。別環境で再現する場合は原稿のrepo/outとfixture/sample.tsxのimportを該当checkoutへ読み替え、同じ基準と2製品差分を用意する。baseline6部品は戻した状態でありAH16移管を混在させない。

必要な原稿はmodal-artifact-manifest.jsonで全件列挙。特に以下が必要:
- modal-prepare.cjs（before/afterの実3部品とModal、CSS、entry生成）
- modal-fixture/mock-api.ts、mock-firebase.ts、sample.tsx（実翻訳・通信モック・実部品mount）
- modal-browser-v4.mjs（独立reference方式、5件先行・560件）
- modal-focus.mjs（実輪郭448件、Enter/Space6件）
- modal-story.mjs（root作成済みStorybook成果物の実表示）
- modal-summarize.py（比較CSV/summary/hash生成）

既存lockの依存と指定Chromiumを準備した環境で、まずnode modal-prepare.cjs、node modal-browser-v4.mjs --limitedを実行し、成功後にnode modal-browser-v4.mjs、node modal-focus.mjs、node modal-story.mjs、python3 modal-summarize.pyを実行する。各stdout/stderrは別ログへ保存する。製品・正式文書の変更や実API通信は不要。

結果: 全560pair・reference一致560・before比較DOM不変560。縮まず収まる448条件は前後同値、折返し必要112条件を区別。全afterの内容領域/画面内・内部文字・非重複、実状態に応じたdisabled一致と保存中再送0を確認。金額は0 / 123450 / 999999999999に限定。将来Shipping共通Buttonの390px日英2条件、実Story日英明暗4条件も成功。console/pageerror/外部通信0。

品質コマンドはrootが実行し root-quality/results.json で5項目exit0を報告。Generatorはこれを重複実行していない。Generatorはdiffcheckと2製品hash不変を直接検算した。

v1/v2/v3とroot diagnostic失敗は未上書き。v4は比較DOMを変えず独立referenceでのみ必要幅を測る方式。640pxは200%相当の狭幅であり実ブラウザーzoomではない。任意長文字や本番全画面/PO目視の保証は行わない。AH退避7ファイルは未検証草案のまま保持。commit/PR/GO/mergeなし。
