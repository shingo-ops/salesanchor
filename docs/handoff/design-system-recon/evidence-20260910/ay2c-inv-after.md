# AY-2c 再計測（ay0-input-inventory.cjs、構文エラー0、TSX 277）

| 指標 | before（origin/main 1ce66d21f 相当の snap c6c4fdc51） | after（実装後） |
|---|---|---|
| ページ側の生 text 系 input | 184 | 135 |
| raw input 合計（金型内 1 を含む） | 273 | 224 |
| TextFieldControl 利用 | 177 | 226（+49） |
| TextField 利用 | 220 | 220 |
| `.form-row` 祖先（targets.cjs の連鎖たどり）の生 text 系 input | 49 | 0（残る 5 件は checkbox） |

生出力: ay2c-inv-after.json。`.form-row` 祖先の再列挙: targets.cjs を実装後 worktree に実行し 5 行（全て checkbox）。
