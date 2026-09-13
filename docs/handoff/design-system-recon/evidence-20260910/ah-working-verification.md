# 復元AH16読み取り検算

before: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b
after: /Users/tanizawashingo/worktrees/salesanchor/release-frontend-shared-button-migration

同条件件数: Button70→86、先頭btn332→316、専用20→20、リンク8→8。

6ファイル全体のASTを、Button import除外・beforeの許可されたtag/class→variant/size変換だけで比較し全件一致。コメントとprinter整形のみ比較対象外。全関数本文/残り属性/childrenにAST差分なし。退避manifestのbase7606ca9aと6製品SHA256に全件一致。

| 対象 | 退避SHA256一致 | 許可差分除くAST一致 |
|---|---|---|
| frontend/src/components/ConfirmModal.tsx | True | True |
| frontend/src/components/CommissionPanel.tsx | True | True |
| frontend/src/components/PriorityScoreOverride.tsx | True | True |
| frontend/src/components/OrderFinancialPanel.tsx | True | True |
| frontend/src/components/PurchaseDetailPanel.tsx | True | True |
| frontend/src/components/ShippingDetailPanel.tsx | True | True |

詳細hash・全対象一覧: working-verification.json。再現: working-check.cjs。製品/文書/台帳変更なし。これは読み取り/静的検算のみ、操作/ブラウザー試験結果は含めない。
