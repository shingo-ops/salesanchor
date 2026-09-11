# 共通6部品16ボタンの移管検収

これは何か: ボタンの材料を共通部品へ移した範囲と、操作が変わらないことの確認記録。

親: [設計AH](../../../specs/design-system/design.md#ah-共通6部品の旧ボタン16利用を移管2026-09-11)

基準: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b（先行PR3435マージ済み）。製品は6TSXとSharedButtonMigration.test.tsxの7ファイルだけ。新CIは最後、backend/API/翻訳/共通CSSは変更しない。

## 静的照合

限定読み取り担当が保存原稿を再実行しexit0。Button70→86、先頭btn332→316、専用20→20、リンク8→8。6ファイル全体でimport/tag/class→variant/size以外のAST差分0、退避6製品hash全件一致。rootは6製品差分を直接読み、原稿と結果を確認した。操作試験の実行とは区別する。詳細: [構文と件数](ah-working-verification.json)、[再現原稿](ah-working-check.cjs)、[再実行確認](ah-working-check-reexecution-verification.json)。原稿内の絶対パスは実行環境の記録で、再現時は作業場所/依存/出力先を対応させる。

## 試験原稿の事前レビュー

CSV試験のObject.assign(URL,...)が元URL自体を書き換える不備1件を限定レビューで検出。Generatorへ元オブジェクトを変えない方式と復元確認を指示した。既存PATCHに加え、売上・仕入・発送の新規POST保存も検収対象とする。最終試験結果は未確認。

## 未完

操作unit、実6部品のブラウザー検証、品質検査、製品の最終限定レビュー、PR提出と番号付きGOは未完。PO目視・本番反映は未確認。設計自己審査と実装合格を混同しない。
