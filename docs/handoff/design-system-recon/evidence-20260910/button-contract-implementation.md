# Button操作/処理中表示便の検収（2026-09-11）

親: [recon](../recon.md)。製品3ファイルと新規unit2ファイル。Button.css/components.css/配色tokens/利用画面/依存/CIの変更0。設計ADの範囲。

Generatorが実行し、rootはログ/JSON/差分と局所画像を直接確認。rootが全試験を再実行したという意味ではない。

| 検証 | 結果 |
|---|---|
| unit | 18ファイル151試験成功（新規18試験） |
| check:all | exit0、既存lint警告219/エラー0 |
| build / Storybook | いずれもexit0 |
| 実ブラウザー操作 | 6variant×normal/disabled/loading=18条件、通常click/Enter/Spaceを各直後1/2/3回、無効時追加0、ref同一 |
| Spinner表示 | 明暗×（単体3条件+6variant）=18条件、4辺の色・ariaを確認 |
| reduced-motion | 9条件でanimation none/稼働0 |
| 最終ブラウザー診断 | entry URL1、console.error0、pageerror0 |

証拠はbutton-contract-unit.txt、button-contract-checks.txt、button-contract-browser.json、manifest。公開用テキストは末尾空白のみ整形。原出力は/tmp/frontend-button-contract-20260911に保持。

初稿のlight通常trackをrgb228/228/231と誤転記したが、最初の実行前にindex.css:22の#e2e8f0を確認しrgb226/232/240へ訂正。誤値による試験実行/失敗はなし。rootも同じ行を直接照合し訂正根拠を確認。製品色変更ではない。

初回ブラウザーはassertを通過したがcreateRoot重複警告1件を検知。診断では/tmpと/private/tmp由来のentry URL2を観測、watch/HMR update0。実pathの専用fixture rootと出力先分離後はentry URL1/警告0となった。警告抑止/製品修正/合格条件緩和なし。旧診断はbutton-contract-browser-diagnostic.jsonへ保持。

同梱browser.mjs/fixture.tsxは当時の固定作業場所を参照する検証原稿であり新CIではない。一般利用画面の外観/190配色/200%拡大やPOの理解速度は未検証。局所画像はテスト用の英語ラベルで、製品の最終デザイン見本ではない。全体画面統一と最終CIは後続。

PR/リモートCI/マージは未完了。新しい番号付きGOを生成しない。

限定コード第二レビューAPPROVE受領。対象はHEAD86cbb7e8上の製品5ファイルで、reviewerがmanifest5/5のSHA256一致とADへの適合を確認。reviewerの試験確認はログ読み取りであり再実行ではない。rootも同じ5hashを直接確認した。全体設計は同一AI自己審査、限定コードレビューとは別。
